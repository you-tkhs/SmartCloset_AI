import json
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import numpy as np
import pytest
from openai import APIConnectionError
from PIL import Image
from sqlalchemy.orm import sessionmaker
from ultralytics import YOLO

import app.database as database_module
import app.main as main_module
from app.config import settings
from app.models.clothing_item import ClothingItem
from app.services import llm_service, pipeline_service, storage_service
from app.services.llm_service import LlmServiceError, extract_metadata
from app.services.pipeline_service import run_pipeline_for_item
from app.services.yolo_service import SegmentResult, segment_item

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fake_openai_response(content: str):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


def _valid_metadata_json() -> str:
    return json.dumps(
        {
            "category": "tops",
            "color_primary": "白",
            "color_secondary": None,
            "pattern": "無地",
            "material": "コットン",
            "silhouette": "ゆったりしたシルエット",
        }
    )


@pytest.fixture(scope="module")
def yolo_model():
    return YOLO(settings.MODEL_PATH)


def test_storage_init_creates_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path / "data"))

    storage_service.init_storage()

    for name in ("tmp", "originals", "transparent", "masks", "annotated"):
        assert (tmp_path / "storage" / name).is_dir()
    assert (tmp_path / "data").is_dir()


def test_storage_delete_item_files_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    storage_service.init_storage()

    storage_service.delete_item_files("nonexistent-id")


def test_storage_delete_item_files_removes_all_kinds(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    storage_service.init_storage()
    item_id = "item-1"

    storage_service.original_path(item_id, "jpg").write_bytes(b"x")
    storage_service.transparent_path(item_id).write_bytes(b"x")
    storage_service.mask_path(item_id).write_bytes(b"x")
    storage_service.annotated_path(item_id).write_bytes(b"x")
    storage_service.work_path(item_id).write_bytes(b"x")

    storage_service.delete_item_files(item_id)

    assert not storage_service.original_path(item_id, "jpg").exists()
    assert not storage_service.transparent_path(item_id).exists()
    assert not storage_service.mask_path(item_id).exists()
    assert not storage_service.annotated_path(item_id).exists()
    assert not storage_service.work_path(item_id).exists()


def test_storage_delete_generated_files_keeps_original(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    storage_service.init_storage()
    item_id = "item-2"

    storage_service.original_path(item_id, "png").write_bytes(b"x")
    storage_service.transparent_path(item_id).write_bytes(b"x")

    storage_service.delete_generated_files(item_id)

    assert storage_service.original_path(item_id, "png").exists()
    assert not storage_service.transparent_path(item_id).exists()


def test_storage_delete_tmp_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    storage_service.init_storage()

    tmp_file = Path(settings.STORAGE_DIR) / "tmp" / "abc.upload"
    tmp_file.write_bytes(b"x")

    storage_service.delete_tmp(tmp_file)
    assert not tmp_file.exists()

    storage_service.delete_tmp(tmp_file)


def test_storage_check_free_space_returns_positive(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    storage_service.init_storage()

    assert storage_service.check_free_space() > 0


def test_storage_to_public_url_originals():
    assert storage_service.to_public_url("storage/originals/abc_original.jpg") == "/images/originals/abc_original.jpg"


def test_storage_to_public_url_transparent():
    assert (
        storage_service.to_public_url("storage/transparent/abc_transparent.png")
        == "/images/transparent/abc_transparent.png"
    )


def test_storage_to_public_url_non_public_returns_none():
    assert storage_service.to_public_url("storage/masks/abc_mask.png") is None


@pytest.mark.yolo
def test_segment_item_tops_jpg_success(yolo_model):
    result = segment_item(yolo_model, FIXTURES_DIR / "tops.jpg", settings.CONF_THRES)

    assert result.status == "success"
    assert result.rgba is not None
    assert result.mask is not None
    assert result.info is not None
    assert "pred_class" in result.info
    assert "confidence" in result.info
    assert "num_instances" in result.info
    assert "all_pred_classes" in result.info
    assert "all_confidences" in result.info


@pytest.mark.yolo
def test_segment_item_shoes_jpg_has_at_least_one_instance(yolo_model):
    result = segment_item(yolo_model, FIXTURES_DIR / "shoes.jpg", settings.CONF_THRES)

    assert result.status == "success"
    assert result.info["num_instances"] >= 1


@pytest.mark.yolo
def test_segment_item_no_clothing_jpg_no_mask(yolo_model):
    result = segment_item(yolo_model, FIXTURES_DIR / "no_clothing.jpg", settings.CONF_THRES)

    assert result.status == "no_mask"
    assert result.rgba is None
    assert result.mask is None
    assert result.info is None


@pytest.mark.yolo
def test_segment_item_missing_path_image_read_error(yolo_model):
    result = segment_item(yolo_model, FIXTURES_DIR / "does_not_exist.jpg", settings.CONF_THRES)

    assert result.status == "image_read_error"
    assert result.rgba is None
    assert result.mask is None
    assert result.yolo_result is None
    assert result.info is None


def test_llm_extract_metadata_success(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_service.time, "sleep", lambda seconds: None)
    image_path = tmp_path / "img.png"
    image_path.write_bytes(b"fake-image-bytes")

    client = MagicMock()
    client.chat.completions.create.return_value = _fake_openai_response(_valid_metadata_json())

    result = extract_metadata(client, image_path)

    assert result["category"] == "tops"
    assert result["color_secondary"] is None
    assert client.chat.completions.create.call_count == 1


def test_llm_extract_metadata_retries_then_raises_on_api_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_service.time, "sleep", lambda seconds: None)
    image_path = tmp_path / "img.png"
    image_path.write_bytes(b"fake-image-bytes")

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    client = MagicMock()
    client.chat.completions.create.side_effect = APIConnectionError(request=request)

    with pytest.raises(LlmServiceError):
        extract_metadata(client, image_path)

    assert client.chat.completions.create.call_count == settings.OPENAI_MAX_RETRIES + 1


def test_llm_extract_metadata_recovers_from_code_fenced_json(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_service.time, "sleep", lambda seconds: None)
    image_path = tmp_path / "img.png"
    image_path.write_bytes(b"fake-image-bytes")

    fenced = f"```json\n{_valid_metadata_json()}\n```"
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_openai_response(fenced)

    result = extract_metadata(client, image_path)

    assert result["category"] == "tops"
    assert client.chat.completions.create.call_count == 1


def test_llm_extract_metadata_unrecoverable_json_retries_then_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_service.time, "sleep", lambda seconds: None)
    image_path = tmp_path / "img.png"
    image_path.write_bytes(b"fake-image-bytes")

    client = MagicMock()
    client.chat.completions.create.return_value = _fake_openai_response("not valid json at all")

    with pytest.raises(LlmServiceError):
        extract_metadata(client, image_path)

    assert client.chat.completions.create.call_count == settings.OPENAI_MAX_RETRIES + 1


@pytest.fixture
def pipeline_env(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    data_dir = tmp_path / "data"
    db_path = data_dir / "test.db"

    monkeypatch.setattr(settings, "STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")

    test_engine = database_module.build_engine(settings.DATABASE_URL)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(database_module, "engine", test_engine)
    monkeypatch.setattr(database_module, "SessionLocal", test_session_local)

    storage_service.init_storage()
    database_module.Base.metadata.create_all(bind=test_engine)

    monkeypatch.setattr(main_module.app.state, "yolo_model", MagicMock(), raising=False)
    monkeypatch.setattr(main_module.app.state, "openai_client", MagicMock(), raising=False)

    return storage_dir


def _create_processing_item(item_id: str, original_path: Path) -> None:
    db = database_module.SessionLocal()
    item = ClothingItem(
        id=item_id,
        status="processing",
        idempotency_key=str(uuid.uuid4()),
        upload_sha256="0" * 64,
        original_image_path=str(original_path),
    )
    db.add(item)
    db.commit()
    db.close()


def _make_original_image(path: Path, size=(64, 64)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(120, 60, 30)).save(path, format="JPEG")
    return path


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


def test_pipeline_no_mask_marks_failed_and_does_not_retry_yolo(pipeline_env, monkeypatch):
    item_id = str(uuid.uuid4())
    original_path = _make_original_image(pipeline_env.parent / "src" / f"{item_id}.jpg")
    _create_processing_item(item_id, original_path)

    segment_calls = []

    def _fake_segment(model, path, conf):
        segment_calls.append(path)
        return SegmentResult(rgba=None, mask=None, yolo_result=MagicMock(), info=None, status="no_mask")

    monkeypatch.setattr(pipeline_service, "segment_item", _fake_segment)

    run_pipeline_for_item(item_id)

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()

    assert item.status == "failed"
    assert item.failure_reason == "no_mask"
    assert len(segment_calls) == 1


def test_pipeline_llm_failure_marks_failed_and_cleans_generated_files(pipeline_env, monkeypatch):
    item_id = str(uuid.uuid4())
    original_path = _make_original_image(pipeline_env.parent / "src" / f"{item_id}.jpg")
    _create_processing_item(item_id, original_path)

    monkeypatch.setattr(pipeline_service, "segment_item", lambda model, path, conf: _fake_success_segment_result())

    def _fake_extract_metadata(client, image_path):
        raise LlmServiceError("boom")

    monkeypatch.setattr(pipeline_service, "extract_metadata", _fake_extract_metadata)

    run_pipeline_for_item(item_id)

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()

    assert item.status == "failed"
    assert item.failure_reason == "llm_error"
    assert original_path.exists()
    assert not storage_service.transparent_path(item_id).exists()
    assert not storage_service.mask_path(item_id).exists()
    assert not storage_service.annotated_path(item_id).exists()


def test_pipeline_unexpected_exception_marks_failed_internal_error(pipeline_env, monkeypatch):
    item_id = str(uuid.uuid4())
    original_path = _make_original_image(pipeline_env.parent / "src" / f"{item_id}.jpg")
    _create_processing_item(item_id, original_path)

    def _raise(model, path, conf):
        raise RuntimeError("unexpected failure injected by test")

    monkeypatch.setattr(pipeline_service, "segment_item", _raise)

    run_pipeline_for_item(item_id)

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()

    assert item.status == "failed"
    assert item.failure_reason == "internal_error"


def test_pipeline_serializes_concurrent_executions(pipeline_env, monkeypatch):
    item_id_1 = str(uuid.uuid4())
    item_id_2 = str(uuid.uuid4())
    _create_processing_item(item_id_1, _make_original_image(pipeline_env.parent / "src" / f"{item_id_1}.jpg"))
    _create_processing_item(item_id_2, _make_original_image(pipeline_env.parent / "src" / f"{item_id_2}.jpg"))

    intervals = []
    intervals_lock = threading.Lock()

    def _slow_segment(model, path, conf):
        start = time.monotonic()
        time.sleep(0.2)
        end = time.monotonic()
        with intervals_lock:
            intervals.append((start, end))
        return _fake_success_segment_result()

    monkeypatch.setattr(pipeline_service, "segment_item", _slow_segment)
    monkeypatch.setattr(pipeline_service, "extract_metadata", lambda client, path: _valid_metadata_dict())

    t1 = threading.Thread(target=run_pipeline_for_item, args=(item_id_1,))
    t2 = threading.Thread(target=run_pipeline_for_item, args=(item_id_2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(intervals) == 2
    (start_a, end_a), (start_b, end_b) = intervals
    assert end_a <= start_b or end_b <= start_a


def test_pipeline_creates_and_closes_session_per_task(pipeline_env, monkeypatch):
    item_id = str(uuid.uuid4())
    original_path = _make_original_image(pipeline_env.parent / "src" / f"{item_id}.jpg")
    _create_processing_item(item_id, original_path)

    real_create_session = pipeline_service.create_session
    created_sessions = []

    def _spy_create_session():
        real_db = real_create_session()
        spy = MagicMock(wraps=real_db)
        created_sessions.append(spy)
        return spy

    monkeypatch.setattr(pipeline_service, "create_session", _spy_create_session)
    monkeypatch.setattr(pipeline_service, "segment_item", lambda model, path, conf: _fake_success_segment_result())
    monkeypatch.setattr(pipeline_service, "extract_metadata", lambda client, path: _valid_metadata_dict())

    run_pipeline_for_item(item_id)

    assert len(created_sessions) == 1
    created_sessions[0].close.assert_called_once()

    db = database_module.SessionLocal()
    item = db.get(ClothingItem, item_id)
    db.close()
    assert item.status == "completed"
