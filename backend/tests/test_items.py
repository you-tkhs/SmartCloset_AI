"""design.md 6.4節・6.5節: GET /api/items(一覧・フィルタ・ページング)。"""

import uuid
from datetime import datetime, timedelta, timezone

import app.database as database_module
from app.models.clothing_item import ClothingItem


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
