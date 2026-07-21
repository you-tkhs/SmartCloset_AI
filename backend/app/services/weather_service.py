"""design.md 11.3節: OpenWeatherMap Current Weather Data APIクライアント。失敗時は例外を送出せずNoneを返す。"""

import logging

import httpx

from app.config import settings
from app.schemas.weather import WeatherInfo

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0
_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"


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
