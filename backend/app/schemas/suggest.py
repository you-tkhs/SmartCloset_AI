from pydantic import BaseModel, Field, field_validator

from app.schemas.item import ItemResponse
from app.schemas.weather import WeatherInfo


class SuggestRequest(BaseModel):
    request_text: str = Field(min_length=1, max_length=500)
    city: str | None = None
    use_weather: bool = True

    @field_validator("request_text")
    @classmethod
    def _reject_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("request_text must not be blank")
        return v


class SuggestResponse(BaseModel):
    suggestion_text: str
    styling_reason: str
    items: list[ItemResponse]
    weather: WeatherInfo | None = None
    weather_available: bool
    log_id: str
