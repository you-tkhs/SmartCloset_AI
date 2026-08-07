"""design.md 11.3.1節: OpenWeatherMapクライアント(現在天気+予報)。失敗時は例外を送出せずNoneを返す。"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.schemas.weather import WeatherInfo

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0
_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
_FORECAST_ENDPOINT = "https://api.openweathermap.org/data/2.5/forecast"
_MAX_FORECAST_DAYS_OFFSET = 5


def get_current_weather(city: str) -> WeatherInfo | None:
    if not settings.OPENWEATHER_API_KEY:
        logger.warning("weather fetch skipped: OPENWEATHER_API_KEY is not set")
        return None

    params = {
        "q": city,
        "units": "metric",
        "lang": "ja",
        "appid": settings.OPENWEATHER_API_KEY,
    }

    try:
        response = httpx.get(_ENDPOINT, params=params, timeout=_TIMEOUT_SECONDS)
    except httpx.HTTPError:
        logger.warning("weather fetch failed for city=%s", city)
        return None

    if response.status_code != 200:
        logger.warning("weather fetch returned non-200 status=%s city=%s", response.status_code, city)
        return None

    try:
        data = response.json()
        return WeatherInfo(
            city=data["name"],
            temp=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            description=data["weather"][0]["description"],
            humidity=data["main"]["humidity"],
            wind_speed=data["wind"]["speed"],
        )
    except (KeyError, IndexError, TypeError, ValueError) as e:
        logger.warning("weather response parse failed for city=%s: %s", city, e)
        return None


def get_forecast_weather(city: str, days_offset: int) -> WeatherInfo | None:
    """OpenWeatherMap 5 Day / 3 Hour Forecast APIを呼ぶ。失敗時はNoneを返す(例外を送出しない)。

    days_offsetは1〜5(0は呼び出し元がget_current_weatherを使うため対象外)。
    """
    if not settings.OPENWEATHER_API_KEY:
        logger.warning("forecast fetch skipped: OPENWEATHER_API_KEY is not set")
        return None
    if not (1 <= days_offset <= _MAX_FORECAST_DAYS_OFFSET):
        logger.warning("forecast fetch skipped: days_offset out of range (%s)", days_offset)
        return None

    params = {"q": city, "units": "metric", "lang": "ja", "appid": settings.OPENWEATHER_API_KEY}
    try:
        response = httpx.get(_FORECAST_ENDPOINT, params=params, timeout=_TIMEOUT_SECONDS)
    except httpx.HTTPError:
        logger.warning("forecast fetch failed for city=%s", city)
        return None

    if response.status_code != 200:
        logger.warning("forecast fetch returned non-200 status=%s city=%s", response.status_code, city)
        return None

    try:
        data = response.json()
        tz_offset_seconds = data.get("city", {}).get("timezone", 0)
        tz_offset = timedelta(seconds=tz_offset_seconds)
        target_date = (datetime.now(timezone.utc) + tz_offset + timedelta(days=days_offset)).date()

        best_entry = None
        best_score = None
        for entry in data["list"]:
            local_dt = datetime.fromtimestamp(entry["dt"], tz=timezone.utc) + tz_offset
            if local_dt.date() != target_date:
                continue
            score = abs((local_dt.hour + local_dt.minute / 60) - 12.0)
            if best_score is None or score < best_score:
                best_entry, best_score = entry, score

        if best_entry is None:
            logger.warning("forecast fetch: no entries for target date city=%s offset=%s", city, days_offset)
            return None

        return WeatherInfo(
            city=data.get("city", {}).get("name", city),
            temp=best_entry["main"]["temp"],
            feels_like=best_entry["main"]["feels_like"],
            description=best_entry["weather"][0]["description"],
            humidity=best_entry["main"]["humidity"],
            wind_speed=best_entry["wind"]["speed"],
            forecast_date=target_date.isoformat(),
        )
    except (KeyError, IndexError, TypeError, ValueError) as e:
        logger.warning("forecast response parse failed for city=%s: %s", city, e)
        return None
