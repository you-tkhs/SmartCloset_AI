from pathlib import Path

import pytest
from ultralytics import YOLO

from app.config import settings
from app.services import storage_service
from app.services.yolo_service import segment_item

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
