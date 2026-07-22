"""design.md 6.8節・11.1節・11.4節: POST /api/suggest。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.routers.items import to_item_response
from app.schemas.suggest import SuggestRequest, SuggestResponse
from app.services.llm_service import LlmServiceError
from app.services.suggest_service import create_suggestion
from app.services.weather_service import get_current_weather

router = APIRouter()


def _error(status_code: int, error_code: str, detail: str, retryable: bool) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "error_code": error_code, "retryable": retryable},
    )


@router.post("/api/suggest", response_model=SuggestResponse)
def post_suggest(payload: SuggestRequest, db: Session = Depends(get_db)):
    has_completed = (
        db.query(ClothingItem).filter(ClothingItem.user_id == 1, ClothingItem.status == "completed").first()
        is not None
    )
    if not has_completed:
        raise _error(
            400,
            "no_completed_items",
            "クローゼットに登録済みの衣服がありません。先に衣服を登録してください。",
            False,
        )

    weather = None
    if payload.use_weather:
        weather = get_current_weather(payload.city or settings.DEFAULT_CITY)

    try:
        result = create_suggestion(db, payload.request_text, weather)
    except LlmServiceError as e:
        raise _error(
            503,
            "service_unavailable",
            "提案の生成に失敗しました。しばらく待ってから再度お試しください。",
            True,
        ) from e
    except SQLAlchemyError as e:
        raise _error(
            503,
            "database_error",
            "サーバーが混み合っています。しばらく待ってから再度お試しください。",
            True,
        ) from e

    return SuggestResponse(
        suggestion_text=result.suggestion_text,
        styling_reason=result.styling_reason,
        items=[to_item_response(item) for item in result.items],
        weather=result.weather,
        weather_available=result.weather is not None,
        log_id=result.log_id,
    )
