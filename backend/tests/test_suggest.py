"""design.md 11.1〜11.4節・6.9節・付録B.3: weather_service/location_extraction_service/
weather_resolution_service/GET /api/weather(T3-1)、suggest_service(T3-2)。"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError

import app.database as database_module
import app.main as main_module
from app.config import settings
from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.models.coordinate_log import CoordinateLog
from app.prompts.suggest_prompt import build_suggest_user_prompt
from app.schemas.suggest import SuggestRequest
from app.schemas.weather import WeatherInfo
from app.services import location_extraction_service, weather_service
from app.services import weather_resolution_service as weather_resolution_module
from app.services.llm_service import LlmServiceError
from app.services.location_extraction_service import LocationDateExtraction
from app.services.suggest_service import create_suggestion
from app.services.weather_resolution_service import resolve_weather


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


def test_build_suggest_user_prompt_prioritizes_occasion_over_weather():
    prompt = build_suggest_user_prompt(
        WeatherInfo(city="Morioka", temp=28.0, feels_like=29.0, description="晴れ", humidity=50, wind_speed=1.0),
        "明日の面接に着ていく服を提案してください",
        "[]",
    )

    assert "用途・シーン" in prompt
    assert "TPOに合った選択を最優先" in prompt
    assert "シーンに合わせた提案理由を主軸に" in prompt
    assert prompt.index("# ユーザーの要望") < prompt.index("# 天気情報")


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


def test_suggest_endpoint_prompt_reflects_occasion_from_request_text(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {"item_ids": [tops_id], "suggestion_text": "きちんと感のある一着です。", "styling_reason": "面接向け。"}
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    resp = client.post(
        "/api/suggest", json={"request_text": "明日の面接に着ていく服を提案してください", "use_weather": False}
    )

    assert resp.status_code == 200
    user_message = fake_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "面接" in user_message
    assert "用途・シーン" in user_message


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


def test_suggest_endpoint_coordinate_log_commit_failure_returns_503_database_error(client, monkeypatch):
    """design.md 13.2節: coordinate_logs保存失敗はdatabase_errorへ変換する。"""
    _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps(
            {
                "item_ids": [],
                "suggestion_text": "きれいめカジュアルな組み合わせです。",
                "styling_reason": "白トップスとデニムでバランス良く。",
            }
        )
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    def _override_get_db_failing_commit():
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

    monkeypatch.setitem(main_module.app.dependency_overrides, get_db, _override_get_db_failing_commit)

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ", "use_weather": False})

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "database_error"


def test_suggest_endpoint_blank_request_text_is_422(client):
    resp = client.post("/api/suggest", json={"request_text": "   "})

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "validation_error"


# --- 11.3.1節: weather_service.get_forecast_weather ---


def _utc_ts_for_local(year, month, day, hour, tz_offset_hours=9):
    """JST(既定+9h)のy/m/d/h時点に対応するUTC unixtimeを返す(テスト用ヘルパー)。"""
    local_as_utc = datetime(year, month, day, hour, tzinfo=timezone.utc)
    return int((local_as_utc - timedelta(hours=tz_offset_hours)).timestamp())


class _FixedNowDatetime(datetime):
    _fixed_utc_now = datetime(2026, 8, 7, 3, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls._fixed_utc_now


_FORECAST_PAYLOAD = {
    "city": {"name": "Naha", "timezone": 32400},
    "list": [
        {
            "dt": _utc_ts_for_local(2026, 8, 8, 9),
            "main": {"temp": 27.0, "feels_like": 29.0, "humidity": 70},
            "weather": [{"description": "曇り"}],
            "wind": {"speed": 4.0},
        },
        {
            "dt": _utc_ts_for_local(2026, 8, 8, 12),
            "main": {"temp": 29.0, "feels_like": 31.0, "humidity": 65},
            "weather": [{"description": "晴れ"}],
            "wind": {"speed": 3.5},
        },
        {
            "dt": _utc_ts_for_local(2026, 8, 8, 15),
            "main": {"temp": 30.0, "feels_like": 33.0, "humidity": 60},
            "weather": [{"description": "晴れ"}],
            "wind": {"speed": 3.0},
        },
    ],
}


def test_weather_get_forecast_weather_picks_entry_closest_to_noon(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, _FORECAST_PAYLOAD))
    monkeypatch.setattr(weather_service, "datetime", _FixedNowDatetime)

    result = weather_service.get_forecast_weather("Naha,JP", 1)

    assert result is not None
    assert result.city == "Naha"
    assert result.temp == 29.0
    assert result.forecast_date == "2026-08-08"


def test_weather_get_forecast_weather_no_matching_date_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: _FakeResponse(200, {"city": {"name": "Naha", "timezone": 32400}, "list": []})
    )
    monkeypatch.setattr(weather_service, "datetime", _FixedNowDatetime)

    assert weather_service.get_forecast_weather("Naha,JP", 1) is None


def test_weather_get_forecast_weather_timeout_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")

    def _raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(httpx, "get", _raise_timeout)

    assert weather_service.get_forecast_weather("Naha,JP", 1) is None


def test_weather_get_forecast_weather_non_200_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(401, {}))

    assert weather_service.get_forecast_weather("Naha,JP", 1) is None


def test_weather_get_forecast_weather_missing_api_key_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", None)

    assert weather_service.get_forecast_weather("Naha,JP", 1) is None


def test_weather_get_forecast_weather_days_offset_out_of_range_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "dummy-key")

    assert weather_service.get_forecast_weather("Naha,JP", 0) is None
    assert weather_service.get_forecast_weather("Naha,JP", 6) is None


# --- 11.3.2節: location_extraction_service.extract_location_date ---


def test_extract_location_date_client_none_returns_default():
    result = location_extraction_service.extract_location_date(None, "明日沖縄で")

    assert result.city is None
    assert result.days_offset is None


def test_extract_location_date_success():
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps({"city": "Naha,JP", "days_offset": 1})
    )

    result = location_extraction_service.extract_location_date(fake_client, "明日沖縄で会議です")

    assert result.city == "Naha,JP"
    assert result.days_offset == 1
    assert fake_client.chat.completions.create.call_count == 1


def test_extract_location_date_invalid_json_returns_default_without_retry():
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response("not valid json")

    result = location_extraction_service.extract_location_date(fake_client, "今日のコーデ")

    assert result.city is None
    assert result.days_offset is None
    assert fake_client.chat.completions.create.call_count == 1


def test_extract_location_date_schema_mismatch_returns_default():
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps({"item_ids": [], "suggestion_text": "x", "styling_reason": "y"})
    )

    result = location_extraction_service.extract_location_date(fake_client, "今日のコーデ")

    assert result.city is None
    assert result.days_offset is None


# --- 11.3.3節: weather_resolution_service.resolve_weather ---


def test_resolve_weather_explicit_city_takes_priority(client, monkeypatch):
    monkeypatch.setattr(
        weather_resolution_module,
        "extract_location_date",
        lambda *a, **k: LocationDateExtraction(city="Naha,JP", days_offset=0),
    )
    called = {}
    monkeypatch.setattr(
        weather_resolution_module, "get_current_weather", lambda city: called.setdefault("city", city)
    )

    resolve_weather("明日沖縄で", "Tokyo,JP")

    assert called["city"] == "Tokyo,JP"


def test_resolve_weather_uses_extracted_city_when_no_explicit(client, monkeypatch):
    monkeypatch.setattr(
        weather_resolution_module,
        "extract_location_date",
        lambda *a, **k: LocationDateExtraction(city="Naha,JP", days_offset=0),
    )
    called = {}
    monkeypatch.setattr(
        weather_resolution_module, "get_current_weather", lambda city: called.setdefault("city", city)
    )

    resolve_weather("沖縄の天気は?", None)

    assert called["city"] == "Naha,JP"


def test_resolve_weather_days_offset_zero_calls_current(client, monkeypatch):
    monkeypatch.setattr(
        weather_resolution_module, "extract_location_date", lambda *a, **k: LocationDateExtraction(None, 0)
    )
    called = {}
    monkeypatch.setattr(
        weather_resolution_module, "get_current_weather", lambda city: called.setdefault("current", city)
    )
    monkeypatch.setattr(
        weather_resolution_module, "get_forecast_weather", lambda city, d: called.setdefault("forecast", (city, d))
    )

    resolve_weather("今日のコーデ", None)

    assert "current" in called
    assert "forecast" not in called


def test_resolve_weather_days_offset_in_range_calls_forecast(client, monkeypatch):
    monkeypatch.setattr(
        weather_resolution_module, "extract_location_date", lambda *a, **k: LocationDateExtraction("Naha,JP", 1)
    )
    called = {}
    monkeypatch.setattr(
        weather_resolution_module, "get_current_weather", lambda city: called.setdefault("current", city)
    )
    monkeypatch.setattr(
        weather_resolution_module, "get_forecast_weather", lambda city, d: called.setdefault("forecast", (city, d))
    )

    resolve_weather("明日沖縄で", None)

    assert called.get("forecast") == ("Naha,JP", 1)
    assert "current" not in called


def test_resolve_weather_sentinel_skips_fetch(client, monkeypatch):
    monkeypatch.setattr(
        weather_resolution_module, "extract_location_date", lambda *a, **k: LocationDateExtraction("Naha,JP", 6)
    )
    called = {}
    monkeypatch.setattr(
        weather_resolution_module, "get_current_weather", lambda city: called.setdefault("current", city)
    )
    monkeypatch.setattr(
        weather_resolution_module, "get_forecast_weather", lambda city, d: called.setdefault("forecast", (city, d))
    )

    result = resolve_weather("来月沖縄で", None)

    assert result is None
    assert called == {}


def test_resolve_weather_extraction_failure_falls_back_to_default_city_current(client, monkeypatch):
    monkeypatch.setattr(
        weather_resolution_module, "extract_location_date", lambda *a, **k: LocationDateExtraction(None, None)
    )
    called = {}
    monkeypatch.setattr(
        weather_resolution_module, "get_current_weather", lambda city: called.setdefault("current", city)
    )

    resolve_weather("今日のコーデ", None)

    assert called["current"] == settings.DEFAULT_CITY


# --- routerレベル統合テスト ---


def test_suggest_endpoint_uses_forecast_when_future_date_mentioned(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [
        _fake_openai_response(json.dumps({"city": "Naha,JP", "days_offset": 1})),
        _fake_openai_response(
            json.dumps(
                {"item_ids": [tops_id], "suggestion_text": "明日は暖かいので軽装です。", "styling_reason": "気温に合わせて。"}
            )
        ),
    ]
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    fake_weather = WeatherInfo(
        city="Naha", temp=29.0, feels_like=31.0, description="晴れ", humidity=65, wind_speed=3.5, forecast_date="2026-08-08"
    )
    monkeypatch.setattr(weather_resolution_module, "get_forecast_weather", lambda city, d: fake_weather)

    resp = client.post("/api/suggest", json={"request_text": "明日沖縄で会議です"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["weather"]["forecast_date"] == "2026-08-08"
    assert fake_client.chat.completions.create.call_count == 2


def test_suggest_endpoint_use_weather_false_skips_extraction_call(client, monkeypatch):
    tops_id = _create_completed_item(category="tops")

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_openai_response(
        json.dumps({"item_ids": [tops_id], "suggestion_text": "シンプルな一着です。", "styling_reason": "手持ちを活用。"})
    )
    monkeypatch.setattr(main_module.app.state, "openai_client", fake_client, raising=False)

    resp = client.post("/api/suggest", json={"request_text": "今日のコーデ", "use_weather": False})

    assert resp.status_code == 200
    assert fake_client.chat.completions.create.call_count == 1
