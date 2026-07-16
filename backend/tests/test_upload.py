import asyncio
import errno
import io
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

import app.database as database_module
import app.main as main_module
import app.routers.upload as upload_module
from app.config import settings
from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.services import pipeline_service, storage_service
from app.services.image_validation_service import (
    InvalidImageError,
    UnsupportedMediaTypeError,
    validate_and_normalize,
)
from app.services.yolo_service import SegmentResult

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class _FakeUploadFile:
    """テスト用の疑似UploadFile。実受信バイト数のみを基準に読み込む。"""

    def __init__(self, data: bytes, declared_size: int | None = None):
        self._buf = io.BytesIO(data)
        self.size = declared_size

    async def read(self, n: int) -> bytes:
        return self._buf.read(n)


def test_validation_accepts_tops_jpg():
    result = validate_and_normalize(FIXTURES_DIR / "tops.jpg", "image/jpeg", "tops.jpg")

    assert result.format == "jpeg"
    assert result.image.mode == "RGB"
    assert result.width > 0
    assert result.height > 0


def test_validation_accepts_shoes_jpg():
    result = validate_and_normalize(FIXTURES_DIR / "shoes.jpg", "image/jpeg", "shoes.jpg")

    assert result.format == "jpeg"
    assert result.image.mode == "RGB"


def test_validation_rejects_disallowed_extension():
    with pytest.raises(UnsupportedMediaTypeError):
        validate_and_normalize(FIXTURES_DIR / "tops.jpg", "image/jpeg", "photo.gif")


def test_validation_rejects_mime_type_mismatch():
    with pytest.raises(UnsupportedMediaTypeError):
        validate_and_normalize(FIXTURES_DIR / "tops.jpg", "text/plain", "tops.jpg")


def test_validation_rejects_fake_jpg_by_signature():
    with pytest.raises(UnsupportedMediaTypeError):
        validate_and_normalize(FIXTURES_DIR / "fake.jpg", "image/jpeg", "fake.jpg")


def test_validation_rejects_broken_png():
    with pytest.raises(InvalidImageError):
        validate_and_normalize(FIXTURES_DIR / "broken.png", "image/png", "broken.png")


def test_validation_rejects_huge_pixels_png():
    with pytest.raises(InvalidImageError):
        validate_and_normalize(FIXTURES_DIR / "huge_pixels.png", "image/png", "huge_pixels.png")


def test_validation_rejects_pixels_in_bomb_warning_band(tmp_path):
    # settings.MAX_IMAGE_PIXELS(4,000万px)の1〜2倍の範囲はPillowが
    # DecompressionBombWarning(エラー化済み)を出す帯域。DecompressionBombError
    # (2倍超)とは別の例外型のため、except節に含めていないと素通りしてしまう。
    src = tmp_path / "bomb_warning_band.png"
    img = Image.new("RGB", (7000, 7000), color=(100, 100, 100))  # 49,000,000px
    img.save(src, format="PNG")

    with pytest.raises(InvalidImageError):
        validate_and_normalize(src, "image/png", "bomb_warning_band.png")


def test_validation_error_message_excludes_absolute_path():
    with pytest.raises(InvalidImageError) as exc_info:
        validate_and_normalize(FIXTURES_DIR / "broken.png", "image/png", "broken.png")

    assert str(FIXTURES_DIR) not in str(exc_info.value)


def test_validation_unidentifiable_image_error_excludes_absolute_path(tmp_path):
    # PNGシグネチャは正しいが本体が壊れている場合、Pillowの
    # UnidentifiedImageErrorはメッセージにtmpの絶対パスを含める。
    # InvalidImageErrorに素通しすると絶対パスが漏れるため、固定メッセージにしていることを確認する。
    src = tmp_path / "unidentifiable.png"
    src.write_bytes(b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a" + b"\x00" * 2000)

    with pytest.raises(InvalidImageError) as exc_info:
        validate_and_normalize(src, "image/png", "unidentifiable.png")

    assert str(tmp_path) not in str(exc_info.value)


def test_validation_applies_exif_orientation(tmp_path):
    src = tmp_path / "exif_oriented.jpg"
    img = Image.new("RGB", (100, 50), (200, 50, 50))
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation: rotate 270 CW
    img.save(src, format="JPEG", exif=exif)

    result = validate_and_normalize(src, "image/jpeg", "exif_oriented.jpg")

    assert (result.width, result.height) == (50, 100)


def test_validation_converts_cmyk_jpeg_to_rgb(tmp_path):
    src = tmp_path / "cmyk.jpg"
    img = Image.new("CMYK", (60, 40))
    img.save(src, format="JPEG")

    result = validate_and_normalize(src, "image/jpeg", "cmyk.jpg")

    assert result.format == "jpeg"
    assert result.image.mode == "RGB"


@pytest.fixture
def storage_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(settings, "MIN_FREE_STORAGE_MB", 1)
    storage_service.init_storage()
    return tmp_path / "storage" / "tmp"


def _tmp_files(tmp_dir: Path) -> list[Path]:
    return list(tmp_dir.glob("*.upload"))


def test_chunk_upload_rejects_oversized_file_and_leaves_no_tmp(storage_env):
    data = b"x" * (2 * 1024 * 1024)  # MAX_UPLOAD_SIZE_MB=1MBを超過
    file = _FakeUploadFile(data)

    with pytest.raises(storage_service.FileTooLargeError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_uses_actual_received_size_over_declared_size(storage_env):
    # Content-Length偽装を模した状況: 申告サイズ(declared_size)は小さいが、
    # 実際に読み込まれるバイト数は上限を超える。実受信サイズを最終基準とする。
    data = b"x" * (2 * 1024 * 1024)
    file = _FakeUploadFile(data, declared_size=100)

    with pytest.raises(storage_service.FileTooLargeError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_rejects_when_free_space_insufficient(storage_env, monkeypatch):
    monkeypatch.setattr(storage_service, "check_free_space", lambda: 0.1)
    file = _FakeUploadFile(b"small file content")

    with pytest.raises(storage_service.InsufficientStorageError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_storage_error_on_write_failure_leaves_no_tmp(storage_env, monkeypatch):
    def _raise_write_error(f, chunk: bytes) -> None:
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(storage_service, "_write_chunk", _raise_write_error)
    file = _FakeUploadFile(b"small file content")

    with pytest.raises(storage_service.StorageError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_insufficient_storage_on_enospc_write_failure(storage_env, monkeypatch):
    def _raise_enospc(f, chunk: bytes) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(storage_service, "_write_chunk", _raise_enospc)
    file = _FakeUploadFile(b"small file content")

    with pytest.raises(storage_service.InsufficientStorageError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_succeeds_and_computes_sha256(storage_env):
    data = b"hello smartcloset"
    file = _FakeUploadFile(data)

    result = asyncio.run(storage_service.save_upload_to_tmp(file))

    assert result.size == len(data)
    assert len(result.sha256) == 64
    assert result.tmp_path.read_bytes() == data
    assert _tmp_files(storage_env) == [result.tmp_path]


def test_no_bulk_file_read_in_storage_service():
    source = Path(storage_service.__file__).read_text()
    assert ".read()" not in source


def _fake_success_segment_result() -> SegmentResult:
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)
    rgba[:, :, 3] = 255
    mask = np.full((10, 10), 255, dtype=np.uint8)
    yolo_result = MagicMock()
    yolo_result.plot.return_value = np.zeros((10, 10, 3), dtype=np.uint8)
    info = {
        "pred_class": "tops",
        "confidence": 0.9,
        "num_instances": 1,
        "all_pred_classes": ["tops"],
        "all_confidences": [0.9],
    }
    return SegmentResult(rgba=rgba, mask=mask, yolo_result=yolo_result, info=info, status="success")


def _valid_metadata_dict() -> dict:
    return {
        "category": "tops",
        "color_primary": "白",
        "color_secondary": None,
        "pattern": "無地",
        "material": "コットン",
        "silhouette": "ゆったりしたシルエット",
    }


def _override_get_db_failing_commit(fail_on_call: int):
    """指定回数目のcommit()だけ失敗させるDependsのオーバーライドを作る。"""
    call_state = {"count": 0}

    def _override():
        db = database_module.SessionLocal()
        real_commit = db.commit

        def _commit():
            call_state["count"] += 1
            if call_state["count"] == fail_on_call:
                raise SQLAlchemyError("simulated commit failure")
            real_commit()

        db.commit = _commit
        try:
            yield db
        finally:
            db.close()

    return _override


def _fake_no_mask_segment_result() -> SegmentResult:
    return SegmentResult(rgba=None, mask=None, yolo_result=None, info=None, status="no_mask")


def _upload_tops_jpg(client, idempotency_key: str | None):
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key is not None else {}
    with open(FIXTURES_DIR / "tops.jpg", "rb") as f:
        return client.post("/api/upload", files={"file": ("tops.jpg", f, "image/jpeg")}, headers=headers)


def _upload_shoes_jpg(client, idempotency_key: str | None):
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key is not None else {}
    with open(FIXTURES_DIR / "shoes.jpg", "rb") as f:
        return client.post("/api/upload", files={"file": ("shoes.jpg", f, "image/jpeg")}, headers=headers)


def test_upload_happy_path_returns_202_then_completes(client, monkeypatch):
    monkeypatch.setattr(pipeline_service, "segment_item", lambda model, path, conf: _fake_success_segment_result())
    monkeypatch.setattr(pipeline_service, "extract_metadata", lambda openai_client, path: _valid_metadata_dict())

    response = _upload_tops_jpg(client, str(uuid.uuid4()))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    item_id = body["item_id"]

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()

    assert item is not None
    assert item.status == "completed"
    assert item.category == "tops"
    assert item.original_image_path is not None
    assert Path(item.original_image_path).exists()
    assert list((Path(settings.STORAGE_DIR) / "tmp").glob("*")) == []


def test_upload_provisional_registration_failure_returns_503(client, monkeypatch):
    monkeypatch.setitem(
        main_module.app.dependency_overrides, get_db, _override_get_db_failing_commit(fail_on_call=1)
    )

    response = _upload_tops_jpg(client, str(uuid.uuid4()))

    assert response.status_code == 503
    assert response.json()["error_code"] == "database_error"

    db = database_module.SessionLocal()
    count = db.query(ClothingItem).count()
    db.close()
    assert count == 0

    storage_dir = Path(settings.STORAGE_DIR)
    assert list((storage_dir / "tmp").glob("*")) == []
    assert list((storage_dir / "originals").glob("*")) == []


def test_upload_original_save_failure_returns_500(client, monkeypatch):
    def _raise_oserror(item_id, image, ext):
        raise OSError("disk write failed")

    monkeypatch.setattr(storage_service, "save_original", _raise_oserror)

    response = _upload_tops_jpg(client, str(uuid.uuid4()))

    assert response.status_code == 500
    assert response.json()["error_code"] == "storage_error"

    db = database_module.SessionLocal()
    count = db.query(ClothingItem).count()
    db.close()
    assert count == 0

    storage_dir = Path(settings.STORAGE_DIR)
    assert list((storage_dir / "tmp").glob("*")) == []
    assert list((storage_dir / "originals").glob("*")) == []


def test_upload_path_commit_failure_returns_503(client, monkeypatch):
    monkeypatch.setitem(
        main_module.app.dependency_overrides, get_db, _override_get_db_failing_commit(fail_on_call=2)
    )

    response = _upload_tops_jpg(client, str(uuid.uuid4()))

    assert response.status_code == 503
    assert response.json()["error_code"] == "database_error"

    db = database_module.SessionLocal()
    count = db.query(ClothingItem).count()
    db.close()
    assert count == 0

    storage_dir = Path(settings.STORAGE_DIR)
    assert list((storage_dir / "tmp").glob("*")) == []
    assert list((storage_dir / "originals").glob("*")) == []


def test_upload_missing_idempotency_key_returns_422(client):
    response = _upload_tops_jpg(client, idempotency_key=None)

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


def test_upload_malformed_idempotency_key_returns_422(client):
    response = _upload_tops_jpg(client, idempotency_key="not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


def test_upload_idempotency_key_resend_while_processing_returns_202_without_new_record(client, monkeypatch):
    monkeypatch.setattr(upload_module, "run_pipeline_for_item", lambda item_id: None)
    key = str(uuid.uuid4())

    first = _upload_tops_jpg(client, key)
    assert first.status_code == 202
    item_id = first.json()["item_id"]

    second = _upload_tops_jpg(client, key)

    assert second.status_code == 202
    body = second.json()
    assert body["item_id"] == item_id
    assert body["status"] == "processing"

    db = database_module.SessionLocal()
    count = db.query(ClothingItem).count()
    db.close()
    assert count == 1


def test_upload_idempotency_key_resend_while_completed_returns_200(client, monkeypatch):
    monkeypatch.setattr(pipeline_service, "segment_item", lambda model, path, conf: _fake_success_segment_result())
    monkeypatch.setattr(pipeline_service, "extract_metadata", lambda openai_client, path: _valid_metadata_dict())
    key = str(uuid.uuid4())

    first = _upload_tops_jpg(client, key)
    item_id = first.json()["item_id"]

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()
    assert item.status == "completed"

    second = _upload_tops_jpg(client, key)

    assert second.status_code == 200
    body = second.json()
    assert body["item_id"] == item_id
    assert body["status"] == "completed"

    db = database_module.SessionLocal()
    count = db.query(ClothingItem).count()
    db.close()
    assert count == 1


def test_upload_idempotency_key_resend_while_failed_returns_200_with_failure_reason(client, monkeypatch):
    monkeypatch.setattr(pipeline_service, "segment_item", lambda model, path, conf: _fake_no_mask_segment_result())
    key = str(uuid.uuid4())

    first = _upload_tops_jpg(client, key)
    item_id = first.json()["item_id"]

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()
    assert item.status == "failed"

    second = _upload_tops_jpg(client, key)

    assert second.status_code == 200
    body = second.json()
    assert body["item_id"] == item_id
    assert body["status"] == "failed"
    assert body["failure_reason"] == "no_mask"

    db = database_module.SessionLocal()
    count = db.query(ClothingItem).count()
    db.close()
    assert count == 1


def test_upload_idempotency_key_conflict_with_different_image_returns_409(client, monkeypatch):
    monkeypatch.setattr(upload_module, "run_pipeline_for_item", lambda item_id: None)
    key = str(uuid.uuid4())

    first = _upload_tops_jpg(client, key)
    assert first.status_code == 202

    second = _upload_shoes_jpg(client, key)

    assert second.status_code == 409
    assert second.json()["error_code"] == "idempotency_key_conflict"

    db = database_module.SessionLocal()
    count = db.query(ClothingItem).count()
    db.close()
    assert count == 1


def _make_processing_item(item_id: str, minutes_old: int) -> tuple[Path, Path, Path]:
    """design.md 8.6節検証用: 生成物込みのprocessingレコードをupdated_atを指定して直接作成する。"""
    original = storage_service.original_path(item_id, "jpg")
    original.write_bytes(b"fake original")
    transparent = storage_service.transparent_path(item_id)
    transparent.write_bytes(b"fake transparent")
    mask = storage_service.mask_path(item_id)
    mask.write_bytes(b"fake mask")

    updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=minutes_old)
    db = database_module.SessionLocal()
    item = ClothingItem(
        id=item_id,
        status="processing",
        idempotency_key=str(uuid.uuid4()),
        upload_sha256="a" * 64,
        original_image_path=str(original),
        transparent_image_path=str(transparent),
        mask_image_path=str(mask),
        updated_at=updated_at,
    )
    db.add(item)
    db.commit()
    db.close()
    return original, transparent, mask


def test_recover_stale_processing_marks_old_processing_as_failed_interrupted(client):
    item_id = str(uuid.uuid4())
    original, transparent, mask = _make_processing_item(item_id, settings.PROCESSING_STALE_MINUTES + 1)

    db = database_module.SessionLocal()
    pipeline_service.recover_stale_processing(db)
    db.close()

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()

    assert item.status == "failed"
    assert item.failure_reason == "processing_interrupted"
    assert original.exists()
    assert not transparent.exists()
    assert not mask.exists()


def test_status_api_lazy_detects_stale_processing_as_failed_interrupted(client):
    item_id = str(uuid.uuid4())
    original, transparent, mask = _make_processing_item(item_id, settings.PROCESSING_STALE_MINUTES + 1)

    response = client.get(f"/api/items/{item_id}/status")

    assert response.status_code == 200
    body = response.json()
    assert body["item_id"] == item_id
    assert body["status"] == "failed"
    assert body["failure_reason"] == "processing_interrupted"

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()
    assert item.status == "failed"
    assert original.exists()
    assert not transparent.exists()
    assert not mask.exists()


def test_recover_stale_processing_leaves_recent_processing_untouched(client):
    item_id = str(uuid.uuid4())
    _make_processing_item(item_id, settings.PROCESSING_STALE_MINUTES - 1)

    db = database_module.SessionLocal()
    pipeline_service.recover_stale_processing(db)
    db.close()

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()
    assert item.status == "processing"


def test_recover_stale_processing_does_not_overwrite_internal_error_failures(client, monkeypatch):
    def _raise(model, path, conf):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_service, "segment_item", _raise)

    response = _upload_tops_jpg(client, str(uuid.uuid4()))
    item_id = response.json()["item_id"]

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()
    assert item.status == "failed"
    assert item.failure_reason == "internal_error"

    db = database_module.SessionLocal()
    pipeline_service.recover_stale_processing(db)
    db.close()

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()
    assert item.status == "failed"
    assert item.failure_reason == "internal_error"


def test_status_api_returns_404_for_missing_item(client):
    response = client.get(f"/api/items/{uuid.uuid4()}/status")

    assert response.status_code == 404
    assert response.json()["error_code"] == "item_not_found"


@pytest.fixture
def yolo_client(tmp_path, monkeypatch):
    """T1-10: 実YOLO重みを読み込む統合テスト用のTestClient。LLMはテスト側でモックする。"""
    storage_dir = tmp_path / "storage"
    data_dir = tmp_path / "data"
    db_path = data_dir / "smartcloset.db"

    monkeypatch.setattr(settings, "STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)

    test_engine = database_module.build_engine(settings.DATABASE_URL)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(database_module, "engine", test_engine)
    monkeypatch.setattr(database_module, "SessionLocal", test_session_local)

    with TestClient(main_module.app) as test_client:
        yield test_client


@pytest.mark.yolo
def test_upload_e2e_with_real_yolo_completes_with_six_attributes_and_transparent_png(yolo_client, monkeypatch):
    metadata = _valid_metadata_dict()
    monkeypatch.setattr(pipeline_service, "extract_metadata", lambda openai_client, path: metadata)

    response = _upload_tops_jpg(yolo_client, str(uuid.uuid4()))
    assert response.status_code == 202
    item_id = response.json()["item_id"]

    status_response = yolo_client.get(f"/api/items/{item_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()

    assert item.status == "completed"
    assert item.category == metadata["category"]
    assert item.color_primary == metadata["color_primary"]
    assert item.color_secondary == metadata["color_secondary"]
    assert item.pattern == metadata["pattern"]
    assert item.material == metadata["material"]
    assert item.silhouette == metadata["silhouette"]
    assert item.yolo_pred_class is not None
    assert item.num_instances >= 1
    assert item.transparent_image_path is not None
    assert Path(item.transparent_image_path).exists()
