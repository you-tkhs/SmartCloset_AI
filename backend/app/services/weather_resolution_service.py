"""design.md 11.3.3節: weather_resolution_service.resolve_weather()。

request_textから場所・日付を抽出し、現在天気/予報のどちらを取得すべきか判定して呼び分ける。
抽出・取得のいずれが失敗してもweather=Noneに落ちるだけで、提案全体はブロックしない。
"""

import logging

from app.config import settings
from app.schemas.weather import WeatherInfo
from app.services.location_extraction_service import extract_location_date
from app.services.weather_service import get_current_weather, get_forecast_weather

logger = logging.getLogger(__name__)

_FAR_FUTURE_SENTINEL = 6


def resolve_weather(request_text: str, explicit_city: str | None) -> WeatherInfo | None:
    # 遅延import: create_suggestion/run_pipeline_for_itemと同じ循環import回避パターン
    from app.main import app as fastapi_app

    extraction = extract_location_date(fastapi_app.state.openai_client, request_text)
    city = explicit_city or extraction.city or settings.DEFAULT_CITY
    days_offset = extraction.days_offset if extraction.days_offset is not None else 0

    if days_offset == 0:
        return get_current_weather(city)
    if days_offset >= _FAR_FUTURE_SENTINEL:
        logger.info("resolve_weather: date beyond forecast window, skipping weather")
        return None
    return get_forecast_weather(city, days_offset)
