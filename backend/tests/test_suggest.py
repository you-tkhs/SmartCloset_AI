"""design.md 11.3節・6.9節: weather_service, GET /api/weather(T3-1)。"""

import httpx

from app.config import settings
from app.services import weather_service


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
