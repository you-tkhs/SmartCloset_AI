"""design.md 6.2節・7.3節(17段階)・7.5節(補償処理)・7.7節(Idempotency-Key): POST /api/upload。"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Request, Response, UploadFile
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.schemas.item import UploadAcceptedResponse
from app.services import storage_service
from app.services.image_validation_service import InvalidImageError, UnsupportedMediaTypeError, validate_and_normalize
from app.services.pipeline_service import run_pipeline_for_item
from app.services.storage_service import FileTooLargeError, InsufficientStorageError, StorageError

logger = logging.getLogger(__name__)

router = APIRouter()

_FORMAT_TO_EXT = {"jpeg": "jpg", "png": "png"}


def _error(status_code: int, error_code: str, detail: str, retryable: bool) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "error_code": error_code, "retryable": retryable},
    )


def _existing_item_response(response: Response, item: ClothingItem) -> UploadAcceptedResponse:
    """design.md 7.7節: 既存Idempotency-Keyヒット時の応答(processing以外は200)。"""
    if item.status != "processing":
        response.status_code = 200
    return UploadAcceptedResponse(item_id=item.id, status=item.status, failure_reason=item.failure_reason)


@router.post("/api/upload", response_model=UploadAcceptedResponse, status_code=202)
async def upload_item(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    # 手順1: Idempotency-Keyの存在(Header必須指定で保証済み)・UUID形式検証
    try:
        uuid.UUID(idempotency_key)
    except ValueError as e:
        raise _error(422, "validation_error", "Idempotency-Keyの形式が不正です。", False) from e

    # 手順2: Content-Length事前確認(実受信サイズを最終基準とする点はsave_upload_to_tmp側で担保)
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = None
        if declared_size is not None and declared_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise _error(413, "file_too_large", "10MB以下の画像をご利用ください。", False)

    tmp_path: Path | None = None
    try:
        # 手順3〜4: チャンク単位のtmp保存。空き容量事前確認はsave_upload_to_tmp内で実施
        try:
            upload_result = await storage_service.save_upload_to_tmp(file)
        except FileTooLargeError as e:
            raise _error(413, "file_too_large", "10MB以下の画像をご利用ください。", False) from e
        except InsufficientStorageError as e:
            raise _error(
                503,
                "insufficient_storage",
                "サーバーの空き容量が不足しています。しばらく待ってから再度お試しください。",
                True,
            ) from e
        except StorageError as e:
            raise _error(500, "storage_error", "画像の保存に失敗しました。再度お試しください。", True) from e

        tmp_path = upload_result.tmp_path

        # 7.7節: 既存Idempotency-Keyとの照合(tmp受信・SHA-256確定後に判定する)
        existing_item = db.query(ClothingItem).filter(ClothingItem.idempotency_key == idempotency_key).first()
        if existing_item is not None:
            if existing_item.upload_sha256 != upload_result.sha256:
                raise _error(
                    409,
                    "idempotency_key_conflict",
                    "同一のIdempotency-Keyで異なる画像が送信されました。",
                    False,
                )
            return _existing_item_response(response, existing_item)

        # 手順5〜10: 実データ検証・正規化
        try:
            normalized = validate_and_normalize(tmp_path, file.content_type, file.filename)
        except UnsupportedMediaTypeError as e:
            raise _error(415, "unsupported_media_type", "JPEG/PNG形式のみ対応しています。", False) from e
        except InvalidImageError as e:
            raise _error(400, "invalid_image", "画像を読み込めませんでした。別のファイルをお試しください。", False) from e

        # 手順11: item_id生成
        item_id = str(uuid.uuid4())
        ext = _FORMAT_TO_EXT[normalized.format]

        # 手順12: DBへ仮登録(画像パスはまだNULL)
        item = ClothingItem(
            id=item_id,
            status="processing",
            idempotency_key=idempotency_key,
            upload_sha256=upload_result.sha256,
            original_filename=file.filename,
        )
        db.add(item)
        try:
            db.commit()
        except IntegrityError as e:
            # 7.7節: 同時リクエストの競合(UNIQUE制約違反)→既存レコード応答へフォールバック
            db.rollback()
            existing_item = db.query(ClothingItem).filter(ClothingItem.idempotency_key == idempotency_key).first()
            if existing_item is not None:
                return _existing_item_response(response, existing_item)
            logger.error("item %s: provisional db registration failed", item_id)
            raise _error(
                503,
                "database_error",
                "サーバーが混み合っています。しばらく待ってから再度お試しください。",
                True,
            ) from e
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("item %s: provisional db registration failed", item_id)
            raise _error(
                503,
                "database_error",
                "サーバーが混み合っています。しばらく待ってから再度お試しください。",
                True,
            ) from e

        # 手順13: 原画像を正式保存
        try:
            original_saved_path = storage_service.save_original(item_id, normalized.image, ext)
        except OSError as e:
            db.delete(item)
            db.commit()
            storage_service.delete_item_files(item_id)
            logger.error("item %s: original image save failed", item_id)
            raise _error(500, "storage_error", "画像の保存に失敗しました。再度お試しください。", True) from e

        # 手順14: 原画像パスをDBへ反映してコミット
        item.original_image_path = str(original_saved_path)
        try:
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            db.delete(item)
            db.commit()
            storage_service.delete_item_files(item_id)
            logger.error("item %s: original image path commit failed", item_id)
            raise _error(
                503,
                "database_error",
                "サーバーが混み合っています。しばらく待ってから再度お試しください。",
                True,
            ) from e

        # 手順15: BackgroundTasksへitem_id(文字列)のみを登録する唯一の箇所。
        # Celery移行時はここを run_pipeline_for_item.delay(item_id) に置き換える。
        try:
            background_tasks.add_task(run_pipeline_for_item, item_id)
        except Exception as e:
            db.delete(item)
            db.commit()
            storage_service.delete_item_files(item_id)
            logger.error("item %s: background task registration failed", item_id)
            raise _error(500, "internal_error", "サーバーエラーが発生しました。再度お試しください。", True) from e

        # 手順16: 202 Accepted(ここまで全成功時のみ)
        return UploadAcceptedResponse(item_id=item_id, status="processing")
    finally:
        # 手順17: tmpは成功・失敗にかかわらず必ず削除
        if tmp_path is not None:
            storage_service.delete_tmp(tmp_path)
