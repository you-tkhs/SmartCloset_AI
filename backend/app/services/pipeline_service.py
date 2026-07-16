"""design.md 8.4節・8.5節: pipeline_service.run_pipeline_for_item()。

BackgroundTasksから呼ばれるAIパイプライン本体。引数はitem_id(str)のみで、
Session/UploadFile/モデルオブジェクトは受け取らない(design.md 2.4節)。
例外はすべて内部で処理し、送出しない。
"""

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.database import create_session
from app.models.clothing_item import ClothingItem
from app.services import storage_service
from app.services.llm_service import LlmServiceError, extract_metadata
from app.services.yolo_service import segment_item

logger = logging.getLogger(__name__)

# design.md 8.5節: YOLO推論の並行実行を避けるため同時実行数を1に制限する。
# 管理場所はこのモジュールに固定(Celery移行時にここを廃止する)。
_ai_semaphore = threading.BoundedSemaphore(settings.AI_MAX_CONCURRENCY)


def mark_item_failed(db: Session, item: ClothingItem, reason: str) -> None:
    item.status = "failed"
    item.failure_reason = reason
    db.commit()
    storage_service.delete_generated_files(item.id)
    logger.error("item %s: failed (failure_reason=%s)", item.id, reason)


def _stale_threshold() -> datetime:
    # updated_at はSQLiteから素朴なUTC(tzinfoなし)で戻るため、比較側も同じ形に揃える。
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=settings.PROCESSING_STALE_MINUTES)


def _recover_stale_item(db: Session, item: ClothingItem) -> None:
    elapsed = datetime.now(timezone.utc).replace(tzinfo=None) - item.updated_at
    item.status = "failed"
    item.failure_reason = "processing_interrupted"
    db.commit()
    storage_service.delete_generated_files(item.id)
    logger.warning("item %s: processing interrupted (elapsed=%.1fs)", item.id, elapsed.total_seconds())


def recover_item_if_stale(db: Session, item: ClothingItem) -> bool:
    """design.md 8.6節(b): lazy検出。stale状態のprocessingを復旧した場合Trueを返す。"""
    if item.status != "processing" or item.updated_at >= _stale_threshold():
        return False
    _recover_stale_item(db, item)
    return True


def recover_stale_processing(db: Session) -> None:
    """design.md 8.6節(a): 起動時に閾値超過のprocessingを一括failed(processing_interrupted)化する。"""
    stale_items = (
        db.query(ClothingItem)
        .filter(ClothingItem.status == "processing", ClothingItem.updated_at < _stale_threshold())
        .all()
    )
    for item in stale_items:
        _recover_stale_item(db, item)


def _resize_for_inference(original_path: Path, work_path: Path, long_side: int) -> Path:
    """原画像の長辺がlong_sideを超える場合のみ、推論用の縮小コピーを作成する。原画像は変更しない。"""
    with Image.open(original_path) as img:
        width, height = img.size
        if max(width, height) <= long_side:
            return original_path
        scale = long_side / max(width, height)
        new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        resized = img.resize(new_size, Image.LANCZOS)
        resized.save(work_path)
    return work_path


def run_pipeline_for_item(item_id: str) -> None:
    """BackgroundTasksから呼ばれるAIパイプライン本体。同期関数(def)。引数はitem_id(str)のみ。"""
    wait_start = time.monotonic()
    logger.info("item %s: waiting for AI semaphore", item_id)
    with _ai_semaphore:
        wait_seconds = time.monotonic() - wait_start
        logger.info("item %s: acquired AI semaphore after %.3fs", item_id, wait_seconds)
        _run_pipeline_locked(item_id)
        logger.info("item %s: released AI semaphore", item_id)


def _run_pipeline_locked(item_id: str) -> None:
    db = create_session()
    item: ClothingItem | None = None
    work_path: Path | None = None

    try:
        item = db.get(ClothingItem, item_id)
        if item is None or item.status != "processing":
            logger.warning("item %s: not found or not in processing status, skipping", item_id)
            return

        # 遅延import: main.py(app定義)とpipeline_serviceの循環importを避けるため
        # モジュールレベルではなく関数内でimportする。
        from app.main import app as fastapi_app

        model = fastapi_app.state.yolo_model
        client = fastapi_app.state.openai_client

        original_path = Path(item.original_image_path)

        step_start = time.monotonic()
        target_path = original_path
        with Image.open(original_path) as img:
            needs_resize = max(img.size) > settings.MAX_IMAGE_LONG_SIDE
        if needs_resize:
            work_path = storage_service.work_path(item_id)
            target_path = _resize_for_inference(original_path, work_path, settings.MAX_IMAGE_LONG_SIDE)
        logger.info("item %s: resize step took %.3fs", item_id, time.monotonic() - step_start)

        step_start = time.monotonic()
        result = segment_item(model, target_path, settings.CONF_THRES)
        logger.info(
            "item %s: yolo step took %.3fs (status=%s)", item_id, time.monotonic() - step_start, result.status
        )

        if result.status != "success":
            mark_item_failed(db, item, result.status)
            return

        step_start = time.monotonic()
        storage_service.save_pipeline_outputs(item_id, result.rgba, result.mask, result.yolo_result)
        logger.info("item %s: save outputs step took %.3fs", item_id, time.monotonic() - step_start)

        step_start = time.monotonic()
        try:
            metadata = extract_metadata(client, storage_service.transparent_path(item_id))
        except LlmServiceError:
            mark_item_failed(db, item, "llm_error")
            return
        logger.info("item %s: llm step took %.3fs", item_id, time.monotonic() - step_start)

        step_start = time.monotonic()
        item.category = metadata["category"]
        item.color_primary = metadata["color_primary"]
        item.color_secondary = metadata["color_secondary"]
        item.pattern = metadata["pattern"]
        item.material = metadata["material"]
        item.silhouette = metadata["silhouette"]
        item.yolo_pred_class = result.info["pred_class"]
        item.yolo_confidence = result.info["confidence"]
        item.num_instances = result.info["num_instances"]
        item.transparent_image_path = str(storage_service.transparent_path(item_id))
        item.mask_image_path = str(storage_service.mask_path(item_id))
        item.annotated_image_path = str(storage_service.annotated_path(item_id))
        item.status = "completed"
        db.commit()
        logger.info("item %s: db update step took %.3fs", item_id, time.monotonic() - step_start)
    except Exception:
        logger.exception("item %s: unexpected error in pipeline", item_id)
        db.rollback()
        if item is not None:
            mark_item_failed(db, item, "internal_error")
    finally:
        if work_path is not None:
            storage_service.delete_tmp(work_path)
        db.close()
