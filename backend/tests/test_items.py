"""design.md 6.4〜6.7節: GET /api/items(一覧・フィルタ・ページング)、GET /api/items/{id}、PATCH /api/items/{id}、DELETE /api/items/{id}。"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

import app.database as database_module
import app.main as main_module
from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.services import storage_service


def _create_item(**overrides):
    item_id = overrides.pop("id", str(uuid.uuid4()))
    defaults = {
        "id": item_id,
        "status": "completed",
        "idempotency_key": str(uuid.uuid4()),
        "upload_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
        "original_image_path": f"/data/storage/originals/{item_id}_original.jpg",
        "transparent_image_path": f"/data/storage/transparent/{item_id}_transparent.png",
        "is_user_corrected": False,
    }
    defaults.update(overrides)

    db = database_module.SessionLocal()
    item = ClothingItem(**defaults)
    db.add(item)
    db.commit()
    db.close()
    return item_id


def test_list_returns_empty_when_no_items(client):
    resp = client.get("/api/items")

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_list_returns_item_response_fields_with_urls(client):
    item_id = _create_item(
        category="tops",
        color_primary="白",
        color_secondary="紺",
        pattern="無地",
        material="コットン",
        silhouette="レギュラーフィット",
        yolo_pred_class="tops",
        yolo_confidence=0.91,
        num_instances=1,
    )

    resp = client.get("/api/items")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == item_id
    assert item["status"] == "completed"
    assert item["category"] == "tops"
    assert item["color_primary"] == "白"
    assert item["color_secondary"] == "紺"
    assert item["original_image_url"] == f"/images/originals/{item_id}_original.jpg"
    assert item["transparent_image_url"] == f"/images/transparent/{item_id}_transparent.png"
    assert "original_image_path" not in item
    assert "transparent_image_path" not in item


def test_list_sort_created_at_desc_is_default(client):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    older_id = _create_item(created_at=now - timedelta(minutes=10))
    newer_id = _create_item(created_at=now)

    resp = client.get("/api/items")

    ids = [item["id"] for item in resp.json()["items"]]
    assert ids == [newer_id, older_id]


def test_list_sort_created_at_asc(client):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    older_id = _create_item(created_at=now - timedelta(minutes=10))
    newer_id = _create_item(created_at=now)

    resp = client.get("/api/items", params={"sort": "created_at_asc"})

    ids = [item["id"] for item in resp.json()["items"]]
    assert ids == [older_id, newer_id]


def test_list_filter_by_category(client):
    tops_id = _create_item(category="tops")
    _create_item(category="bottoms")

    resp = client.get("/api/items", params={"category": "tops"})

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == tops_id


def test_list_filter_by_color_matches_primary_or_secondary(client):
    primary_id = _create_item(color_primary="赤", color_secondary=None)
    secondary_id = _create_item(color_primary="黒", color_secondary="赤系")
    _create_item(color_primary="青", color_secondary="白")

    resp = client.get("/api/items", params={"color": "赤"})

    ids = {item["id"] for item in resp.json()["items"]}
    assert ids == {primary_id, secondary_id}


def test_list_filter_by_pattern(client):
    dot_id = _create_item(pattern="ドット")
    _create_item(pattern="無地")

    resp = client.get("/api/items", params={"pattern": "ドット"})

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == dot_id


def test_list_filter_by_material(client):
    denim_id = _create_item(material="デニム")
    _create_item(material="ウール")

    resp = client.get("/api/items", params={"material": "デニム"})

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == denim_id


def test_list_filter_by_status(client):
    processing_id = _create_item(status="processing", original_image_path=None, transparent_image_path=None)
    _create_item(status="completed")

    resp = client.get("/api/items", params={"status": "processing"})

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == processing_id


def test_list_filter_combination_is_intersection(client):
    match_id = _create_item(category="tops", material="コットン")
    _create_item(category="tops", material="デニム")
    _create_item(category="bottoms", material="コットン")

    resp = client.get("/api/items", params={"category": "tops", "material": "コットン"})

    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == match_id


def test_list_filter_returns_empty_for_no_match(client):
    _create_item(category="tops")

    resp = client.get("/api/items", params={"category": "shoes"})

    body = resp.json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_list_pagination(client):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ids = [_create_item(created_at=now - timedelta(minutes=i)) for i in range(5)]

    resp = client.get("/api/items", params={"page": 2, "page_size": 2})

    body = resp.json()
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert [item["id"] for item in body["items"]] == ids[2:4]


def test_list_page_size_over_100_is_422(client):
    resp = client.get("/api/items", params={"page_size": 101})

    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "validation_error"


def test_list_page_size_zero_is_422(client):
    resp = client.get("/api/items", params={"page_size": 0})

    assert resp.status_code == 422


def test_list_page_zero_is_422(client):
    resp = client.get("/api/items", params={"page": 0})

    assert resp.status_code == 422


def test_list_invalid_sort_is_422(client):
    resp = client.get("/api/items", params={"sort": "invalid_sort"})

    assert resp.status_code == 422


def test_detail_returns_item_response_fields_with_urls(client):
    item_id = _create_item(
        category="tops",
        color_primary="白",
        color_secondary="紺",
        pattern="無地",
        material="コットン",
        silhouette="レギュラーフィット",
        yolo_pred_class="tops",
        yolo_confidence=0.91,
        num_instances=1,
    )

    resp = client.get(f"/api/items/{item_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == item_id
    assert body["status"] == "completed"
    assert body["category"] == "tops"
    assert body["color_primary"] == "白"
    assert body["color_secondary"] == "紺"
    assert body["original_image_url"] == f"/images/originals/{item_id}_original.jpg"
    assert body["transparent_image_url"] == f"/images/transparent/{item_id}_transparent.png"
    assert "original_image_path" not in body
    assert "transparent_image_path" not in body


def test_detail_returns_404_for_missing_item(client):
    resp = client.get(f"/api/items/{uuid.uuid4()}")

    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "item_not_found"


def test_detail_does_not_trigger_stale_recovery(client):
    """T2-2の対象は6.5節のItemResponse返却のみ。stale復旧は/statusエンドポイント専用(8.6節(b))。"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    item_id = _create_item(
        status="processing",
        original_image_path=None,
        transparent_image_path=None,
        updated_at=now - timedelta(minutes=999),
    )

    resp = client.get(f"/api/items/{item_id}")

    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"


def test_patch_updates_specified_fields_and_marks_user_corrected(client):
    item_id = _create_item(category="tops", color_primary="白", is_user_corrected=False)

    resp = client.patch(f"/api/items/{item_id}", json={"category": "outer", "silhouette": "オーバーサイズ"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "outer"
    assert body["silhouette"] == "オーバーサイズ"
    assert body["color_primary"] == "白"
    assert body["is_user_corrected"] is True


def test_patch_color_secondary_null_clears_secondary_color(client):
    item_id = _create_item(color_primary="黒", color_secondary="白")

    resp = client.patch(f"/api/items/{item_id}", json={"color_secondary": None})

    assert resp.status_code == 200
    body = resp.json()
    assert body["color_secondary"] is None
    assert body["color_primary"] == "黒"


def test_patch_returns_404_for_missing_item(client):
    resp = client.patch(f"/api/items/{uuid.uuid4()}", json={"category": "tops"})

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "item_not_found"


def test_patch_enum_violation_is_422(client):
    item_id = _create_item()

    resp = client.patch(f"/api/items/{item_id}", json={"category": "コート"})

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "validation_error"


def test_patch_category_explicit_null_is_422(client):
    """categoryはcolor_secondaryと違い非nullable(design.md 6.6節)。"""
    item_id = _create_item()

    resp = client.patch(f"/api/items/{item_id}", json={"category": None})

    assert resp.status_code == 422


def test_patch_processing_item_is_409(client):
    item_id = _create_item(status="processing", original_image_path=None, transparent_image_path=None)

    resp = client.patch(f"/api/items/{item_id}", json={"category": "tops"})

    assert resp.status_code == 409
    assert resp.json()["error_code"] == "item_is_processing"


def test_patch_failed_item_is_409(client):
    item_id = _create_item(status="failed", failure_reason="no_mask", original_image_path=None, transparent_image_path=None)

    resp = client.patch(f"/api/items/{item_id}", json={"category": "tops"})

    assert resp.status_code == 409
    assert resp.json()["error_code"] == "item_not_editable"


def _override_get_db_failing_commit():
    """design.md 13.2節: commit()失敗時に503 database_errorへ変換されることを確認するためのDependsオーバーライド。"""

    def _override():
        db = database_module.SessionLocal()
        real_commit = db.commit

        def _commit():
            db.commit = real_commit
            raise SQLAlchemyError("simulated commit failure")

        db.commit = _commit
        try:
            yield db
        finally:
            db.close()

    return _override


def test_patch_commit_failure_returns_503_database_error(client, monkeypatch):
    item_id = _create_item(category="tops", color_primary="白")
    monkeypatch.setitem(main_module.app.dependency_overrides, get_db, _override_get_db_failing_commit())

    resp = client.patch(f"/api/items/{item_id}", json={"category": "outer"})

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "database_error"


def test_delete_commit_failure_returns_503_database_error(client, monkeypatch):
    item_id = _create_item(status="completed")
    monkeypatch.setitem(main_module.app.dependency_overrides, get_db, _override_get_db_failing_commit())

    resp = client.delete(f"/api/items/{item_id}")

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "database_error"


def _write_item_files(item_id, ext="jpg"):
    original = storage_service.original_path(item_id, ext)
    original.write_bytes(b"fake original")
    transparent = storage_service.transparent_path(item_id)
    transparent.write_bytes(b"fake transparent")
    mask = storage_service.mask_path(item_id)
    mask.write_bytes(b"fake mask")
    annotated = storage_service.annotated_path(item_id)
    annotated.write_bytes(b"fake annotated")
    return original, transparent, mask, annotated


def test_delete_processing_item_is_409_and_keeps_record_and_files(client):
    item_id = _create_item(status="processing", original_image_path=None, transparent_image_path=None)
    original, transparent, mask, annotated = _write_item_files(item_id)

    resp = client.delete(f"/api/items/{item_id}")

    assert resp.status_code == 409
    assert resp.json()["error_code"] == "item_is_processing"
    assert original.exists()
    assert transparent.exists()
    assert mask.exists()
    assert annotated.exists()
    db = database_module.SessionLocal()
    assert db.get(ClothingItem, item_id) is not None
    db.close()


def test_delete_completed_item_returns_204_and_removes_files_and_record(client):
    item_id = _create_item(status="completed")
    original, transparent, mask, annotated = _write_item_files(item_id)

    resp = client.delete(f"/api/items/{item_id}")

    assert resp.status_code == 204
    assert not original.exists()
    assert not transparent.exists()
    assert not mask.exists()
    assert not annotated.exists()
    db = database_module.SessionLocal()
    assert db.get(ClothingItem, item_id) is None
    db.close()


def test_delete_failed_item_removes_remaining_original_image_too(client):
    item_id = _create_item(status="failed", failure_reason="no_mask", original_image_path=None, transparent_image_path=None)
    original = storage_service.original_path(item_id, "jpg")
    original.write_bytes(b"fake original")

    resp = client.delete(f"/api/items/{item_id}")

    assert resp.status_code == 204
    assert not original.exists()
    db = database_module.SessionLocal()
    assert db.get(ClothingItem, item_id) is None
    db.close()


def test_delete_is_idempotent_when_files_already_missing(client):
    item_id = _create_item(status="completed", original_image_path=None, transparent_image_path=None)

    resp = client.delete(f"/api/items/{item_id}")

    assert resp.status_code == 204
    db = database_module.SessionLocal()
    assert db.get(ClothingItem, item_id) is None
    db.close()


def test_delete_returns_404_for_missing_item(client):
    resp = client.delete(f"/api/items/{uuid.uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "item_not_found"
