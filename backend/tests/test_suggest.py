"""design.md 11.1〜11.3節・6.9節: weather_service/GET /api/weather(T3-1)、suggest_service(T3-2)。"""

import json
import uuid
from unittest.mock import MagicMock

import httpx
import pytest

import app.database as database_module
import app.main as main_module
from app.config import settings
from app.models.clothing_item import ClothingItem
from app.models.coordinate_log import CoordinateLog
from app.schemas.suggest import SuggestRequest
from app.schemas.weather import WeatherInfo
from app.services import weather_service
from app.services.llm_service import LlmServiceError
from app.services.suggest_service import create_suggestion


class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


_SUCCESS_PAYLOAD = {
    "name": "Morioka",
    "main": {"temp": 24.3, "feels_like": 25.1, "humidity": 60},
    "weather": [{"description": "晴れ"}],
    "wind": {"speed": 3.2},
}


def test_weather_get_current_weather_success(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, _SUCCESS_PAYLOAD))

    result = weather_service.get_current_weather("Morioka")

    assert result is not None
    assert result.city == "Morioka"
    assert result.temp == 24.3
    assert result.feels_like == 25.1
    assert result.description == "晴れ"
    assert result.humidity == 60
    assert result.wind_speed == 3.2


def test_weather_get_current_weather_timeout_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")

    def _raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(httpx, "get", _raise_timeout)

    assert weather_service.get_current_weather("Morioka") is None


def test_weather_get_current_weather_non_200_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(401, {}))

    assert weather_service.get_current_weather("Morioka") is None


def test_weather_get_current_weather_missing_api_key_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", None)

    assert weather_service.get_current_weather("Morioka") is None


def test_weather_endpoint_returns_200_with_weather_info(client, monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, _SUCCESS_PAYLOAD))

    resp = client.get("/api/weather")

    assert resp.status_code == 200
    body = resp.json()
    assert body["city"] == "Morioka"
    assert body["temp"] == 24.3


def test_weather_endpoint_returns_503_when_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", None)

    resp = client.get("/api/weather")

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "service_unavailable"


def _fake_openai_response(content: str):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


def _create_completed_item(**overrides):
    item_id = overrides.pop("id", str(uuid.uuid4()))
    defaults = {
        "id": item_id,
        "status": "completed",
        "idempotency_key": str(uuid.uuid4()),
        "upload_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
        "category": "tops",
        "color_primary": "白",
        "pattern": "無地",
        "material": "コットン",
        "silhouette": "レギュラーフィット",
    }
    defaults.update(overrides)

    db = database_module.SessionLocal()
    item = ClothingItem(**defaults)
    db.add(item)
    db.commit()
    db.close()
    return item_id


def test_suggest_service_create_suggestion_returns_valid_items(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")
    bottoms_id = _create_completed_item(category="bottoms", color_primary="黒", pattern="無地", material="デニム")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {
                "item_ids": [tops_id, bottoms_id],
                "suggestion_text": "きれいめカジュアルな組み合わせです。",
                "styling_reason": "白トップスとデニムでバランス良く。",
            }
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    db = database_module.SessionLocal()
    result = create_suggestion(db, "オフィスカジュアルで", None)
    # 返却されたClothingItemはdbセッションに紐づくため、閉じる前に属性を読み切る
    # (T3-3のルーターではリクエストスコープのセッションを応答生成後に閉じるため実運用上は問題ない)。
    item_ids = {item.id for item in result.items}
    db.close()

    assert item_ids == {tops_id, bottoms_id}
    assert result.suggestion_text == "きれいめカジュアルな組み合わせです。"
    assert result.styling_reason == "白トップスとデニムでバランス良く。"
    assert result.weather is None
    assert result.log_id

    log_db = database_module.SessionLocal()
    log = log_db.get(CoordinateLog, result.log_id)
    assert log is not None
    assert log.weather_json is None
    assert json.loads(log.recommended_item_ids) == [tops_id, bottoms_id]
    assert log.model_name == settings.OPENAI_MODEL
    log_db.close()


def test_suggest_service_excludes_invalid_item_ids(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {
                "item_ids": [tops_id, "nonexistent-id"],
                "suggestion_text": "シンプルなトップス中心のコーデです。",
                "styling_reason": "手持ちの白トップスを主役に。",
            }
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    db = database_module.SessionLocal()
    result = create_suggestion(db, "普段着で", None)
    item_ids = [item.id for item in result.items]
    db.close()

    assert item_ids == [tops_id]

    log_db = database_module.SessionLocal()
    log = log_db.get(CoordinateLog, result.log_id)
    assert json.loads(log.recommended_item_ids) == [tops_id]
    log_db.close()


def test_suggest_service_stores_weather_json_when_present(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")
    weather = WeatherInfo(city="Morioka", temp=24.3, feels_like=25.1, description="晴れ", humidity=60, wind_speed=3.2)

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps({"item_ids": [tops_id], "suggestion_text": "晴天向けの軽装です。", "styling_reason": "気温に合わせて。"})
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    db = database_module.SessionLocal()
    result = create_suggestion(db, "散歩に行きたい", weather)
    db.close()

    assert result.weather == weather

    log_db = database_module.SessionLocal()
    log = log_db.get(CoordinateLog, result.log_id)
    assert log.weather_json is not None
    assert json.loads(log.weather_json)["city"] == "Morioka"
    log_db.close()


def test_suggest_service_raises_llm_service_error_when_client_missing(client, monkeypatch):
    _create_completed_item(category="tops")
    monkeypatch.setattr(main_module.app.state, "openai_client", None, raising=False)

    db = database_module.SessionLocal()
    with pytest.raises(LlmServiceError):
        create_suggestion(db, "オフィスカジュアルで", None)
    db.close()


def test_suggest_service_retries_on_invalid_json_then_succeeds(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_openai_response("not valid json"),
        _fake_openai_response(
            json.dumps({"item_ids": [tops_id], "suggestion_text": "リトライ後の提案です。", "styling_reason": "妥当な組み合わせ。"})
        ),
    ]
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)
    monkeypatch.setattr("app.services.suggest_service.time.sleep", lambda *_: None)

    db = database_module.SessionLocal()
    result = create_suggestion(db, "オフィスカジュアルで", None)
    db.close()

    assert result.suggestion_text == "リトライ後の提案です。"
    assert fake_client.chat.completions.create.call_count == 2


def test_suggest_request_rejects_blank_text():
    with pytest.raises(Exception):
        SuggestRequest(request_text="   ")


def test_suggest_request_accepts_valid_text():
    req = SuggestRequest(request_text="今日は会議です")
    assert req.use_weather is True
    assert req.city is None


def test_suggest_endpoint_returns_400_when_no_completed_items(client, monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ"})

    assert resp.status_code == 400
    assert resp.json()["error_code"] == "no_completed_items"
    assert fake_client.chat.completions.create.call_count == 0


def test_suggest_endpoint_excludes_processing_and_failed_items_from_closet(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")
    processing_id = _create_completed_item(id=str(uuid.uuid4()), status="processing")
    failed_id = _create_completed_item(id=str(uuid.uuid4()), status="failed", failure_reason="no_mask")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {"item_ids": [tops_id], "suggestion_text": "シンプルな一着です。", "styling_reason": "手持ちを活用。"}
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ", "use_weather": False})

    assert resp.status_code == 200
    user_message = fake_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert tops_id in user_message
    assert processing_id not in user_message
    assert failed_id not in user_message


def test_suggest_endpoint_weather_failure_returns_200_with_weather_unavailable(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", None)

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {
                "item_ids": [tops_id],
                "suggestion_text": "軽装で問題ありません。",
                "styling_reason": "気候不明のため無難な提案。",
            }
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["weather_available"] is False
    assert body["weather"] is None

    log_db = database_module.SessionLocal()
    log = log_db.get(CoordinateLog, body["log_id"])
    assert log.weather_json is None
    log_db.close()


def test_suggest_endpoint_excludes_invalid_item_ids_from_response(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {
                "item_ids": [tops_id, "ghost-id"],
                "suggestion_text": "シンプルにまとめました。",
                "styling_reason": "実在アイテムのみ採用。",
            }
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ", "use_weather": False})

    assert resp.status_code == 200
    body = resp.json()
    assert [item["id"] for item in body["items"]] == [tops_id]


def test_suggest_endpoint_all_invalid_item_ids_returns_empty_items(client, monkeypatch):
    _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {
                "item_ids": ["ghost-1", "ghost-2"],
                "suggestion_text": "該当するアイテムが見つかりませんでした。",
                "styling_reason": "在庫不足。",
            }
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ", "use_weather": False})

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["suggestion_text"] == "該当するアイテムが見つかりませんでした。"


def test_suggest_endpoint_llm_failure_returns_503_and_no_log(client, monkeypatch):
    _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response("not valid json")
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)
    monkeypatch.setattr("app.services.suggest_service.time.sleep", lambda *_: None)

    log_db = database_module.SessionLocal()
    logs_before = log_db.query(CoordinateLog).count()
    log_db.close()

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ", "use_weather": False})

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "service_unavailable"

    log_db = database_module.SessionLocal()
    logs_after = log_db.query(CoordinateLog).count()
    log_db.close()
    assert logs_after == logs_before


def test_suggest_endpoint_blank_request_text_is_422(client):
    resp = client.post("/api/suggest", json={"request_text": "   "})

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "validation_error"
