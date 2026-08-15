"""design.md 11.1〜11.2節・付録B.2: suggest_service.create_suggestion()。

completedアイテムのみでクローゼットJSONを構築(画像は送らない)、strictスキーマで
LLMを呼び出し、返却されたitem_idsをDB照合して無効IDを除外し、coordinate_logsに記録する。
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAIError, RateLimitError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.clothing_item import ClothingItem
from app.models.coordinate_log import CoordinateLog
from app.prompts.suggest_prompt import SUGGEST_JSON_SCHEMA, SUGGEST_SYSTEM_PROMPT, build_suggest_user_prompt
from app.schemas.weather import WeatherInfo
from app.services.llm_service import LlmServiceError

logger = logging.getLogger(__name__)

_RETRYABLE_API_ERRORS = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)
_INITIAL_RETRY_DELAY_SECONDS = 1.0
_CLOSET_ITEM_KEYS = ("id", "category", "color_primary", "color_secondary", "pattern", "material", "silhouette")
_WARM_MATERIALS = frozenset({"ウール", "フリース", "ファー", "ボア"})


@dataclass
class SuggestionResult:
    suggestion_text: str
    styling_reason: str
    items: list[ClothingItem]
    weather: WeatherInfo | None
    log_id: str


def _filter_weather_appropriate(items: list[ClothingItem], weather: WeatherInfo | None) -> list[ClothingItem]:
    if weather is None or weather.feels_like < settings.HOT_WEATHER_TEMP_THRESHOLD_C:
        return items
    filtered = [item for item in items if item.material not in _WARM_MATERIALS]
    if len(filtered) < len(items):
        logger.info("suggest: excluded %d warm-material item(s) for hot weather", len(items) - len(filtered))
    # 除外後に候補が0件になる場合は、乏しくても最善を提案する既存方針(11.2節)を優先しフィルタを適用しない
    return filtered if filtered else items


def _closet_json(items: list[ClothingItem]) -> str:
    closet = [{key: getattr(item, key) for key in _CLOSET_ITEM_KEYS} for item in items]
    return json.dumps(closet, ensure_ascii=False)


def _parse_suggestion_json(text: str | None) -> dict | None:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        cleaned = (text or "").strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            return None


def _is_valid_suggestion(data: dict | None) -> bool:
    if not isinstance(data, dict):
        return False
    item_ids = data.get("item_ids")
    if not isinstance(item_ids, list) or not all(isinstance(x, str) for x in item_ids):
        return False
    if not isinstance(data.get("suggestion_text"), str):
        return False
    if not isinstance(data.get("styling_reason"), str):
        return False
    return True


def _call_llm(client, user_prompt: str) -> dict:
    delay = _INITIAL_RETRY_DELAY_SECONDS
    last_error: Exception | None = None

    for attempt in range(settings.OPENAI_MAX_RETRIES + 1):
        is_last_attempt = attempt == settings.OPENAI_MAX_RETRIES

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SUGGEST_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "coordinate_suggestion",
                        "strict": True,
                        "schema": SUGGEST_JSON_SCHEMA,
                    },
                },
            )
        except _RETRYABLE_API_ERRORS as e:
            last_error = e
            logger.warning(
                "suggest LLM call failed (attempt %d/%d): %s",
                attempt + 1,
                settings.OPENAI_MAX_RETRIES + 1,
                type(e).__name__,
            )
            if not is_last_attempt:
                time.sleep(delay)
                delay *= 2
            continue
        except OpenAIError as e:
            logger.warning("suggest LLM call failed with non-retryable error: %s", type(e).__name__)
            raise LlmServiceError("non-retryable OpenAI API error") from e

        data = _parse_suggestion_json(response.choices[0].message.content)
        if _is_valid_suggestion(data):
            return data

        last_error = LlmServiceError("json_parse_error")
        logger.warning("suggest LLM response JSON invalid (attempt %d/%d)", attempt + 1, settings.OPENAI_MAX_RETRIES + 1)
        if not is_last_attempt:
            time.sleep(delay)
            delay *= 2

    logger.error("suggest generation failed after retries")
    raise LlmServiceError("suggest generation failed after retries") from last_error


def create_suggestion(db: Session, request_text: str, weather: WeatherInfo | None) -> SuggestionResult:
    # 遅延import: main.py(app定義)とsuggest_serviceの循環importを避けるため
    # モジュールレベルではなく関数内でimportする(pipeline_serviceと同じ方針)。
    from app.main import app as fastapi_app

    client = fastapi_app.state.openai_client
    if client is None:
        logger.warning("OpenAI client is not configured (OPENAI_API_KEY unset)")
        raise LlmServiceError("openai client not configured")

    completed_items = (
        db.query(ClothingItem).filter(ClothingItem.user_id == 1, ClothingItem.status == "completed").all()
    )

    items_for_closet = _filter_weather_appropriate(completed_items, weather)
    user_prompt = build_suggest_user_prompt(weather, request_text, _closet_json(items_for_closet))
    data = _call_llm(client, user_prompt)

    items_by_id = {item.id: item for item in items_for_closet}
    requested_ids = data["item_ids"]
    recommended_ids = [item_id for item_id in requested_ids if item_id in items_by_id]
    invalid_ids = [item_id for item_id in requested_ids if item_id not in items_by_id]
    if invalid_ids:
        logger.warning("suggest: LLM returned invalid item_ids, excluding: %s", invalid_ids)

    log = CoordinateLog(
        id=str(uuid.uuid4()),
        request_text=request_text,
        weather_json=weather.model_dump_json() if weather is not None else None,
        suggestion_text=data["suggestion_text"],
        styling_reason=data["styling_reason"],
        recommended_item_ids=json.dumps(recommended_ids, ensure_ascii=False),
        model_name=settings.OPENAI_MODEL,
    )
    db.add(log)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.error("suggest: coordinate log commit failed")
        raise

    return SuggestionResult(
        suggestion_text=data["suggestion_text"],
        styling_reason=data["styling_reason"],
        items=[items_by_id[item_id] for item_id in recommended_ids],
        weather=weather,
        log_id=log.id,
    )
