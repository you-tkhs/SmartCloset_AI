"""design.md 6.9節: GET /api/weather。取得失敗時は503 service_unavailable。"""

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.schemas.weather import WeatherInfo
from app.services.weather_service import get_current_weather

router = APIRouter()


def _error(status_code: int, error_code: str, detail: str, retryable: bool) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "error_code": error_code, "retryable": retryable},
    )


@router.get("/api/weather", response_model=WeatherInfo)
def get_weather(city: str | None = Query(default=None)):
    weather = get_current_weather(city or settings.DEFAULT_CITY)
    if weather is None:
        raise _error(
            503,
            "service_unavailable",
            "提案の生成に失敗しました。しばらく待ってから再度お試しください。",
            True,
        )

    return weather
