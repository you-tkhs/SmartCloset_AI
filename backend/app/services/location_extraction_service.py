"""design.md 11.3.2節・付録B.3: location_extraction_service.extract_location_date()。

天気解決のためのベストエフォート抽出。リトライは行わない(1回勝負)。
失敗しても提案全体をブロックしないことを最優先する(11.3節と同じfail-soft哲学)。
"""

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from openai import OpenAI, OpenAIError

from app.config import settings
from app.prompts.location_prompt import LOCATION_JSON_SCHEMA, LOCATION_SYSTEM_PROMPT, build_location_user_prompt

logger = logging.getLogger(__name__)

_JST = ZoneInfo("Asia/Tokyo")


@dataclass
class LocationDateExtraction:
    city: str | None
    days_offset: int | None


_DEFAULT_EXTRACTION = LocationDateExtraction(city=None, days_offset=None)


def _now_jst_date() -> date:
    return datetime.now(_JST).date()


def _parse_json_safely(text: str | None) -> dict | None:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        cleaned = (text or "").strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            return None


def _is_valid_extraction(data: dict | None) -> bool:
    if not isinstance(data, dict):
        return False
    if "city" not in data or not (data["city"] is None or isinstance(data["city"], str)):
        return False
    if data.get("days_offset") not in range(7):
        return False
    return True


def extract_location_date(
    client: OpenAI | None, request_text: str, today: date | None = None
) -> LocationDateExtraction:
    """request_textから場所(city)・日付(days_offset)をLLMで抽出する。

    リトライは行わない。失敗時は例外を送出せずLocationDateExtraction(None, None)を返す。
    """
    if client is None:
        return _DEFAULT_EXTRACTION

    resolved_today = today or _now_jst_date()

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": LOCATION_SYSTEM_PROMPT},
                {"role": "user", "content": build_location_user_prompt(request_text, resolved_today)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "location_date_extraction",
                    "strict": True,
                    "schema": LOCATION_JSON_SCHEMA,
                },
            },
        )
    except OpenAIError as e:
        logger.info("location extraction failed, falling back to default: %s", type(e).__name__)
        return _DEFAULT_EXTRACTION

    data = _parse_json_safely(response.choices[0].message.content)
    if not _is_valid_extraction(data):
        logger.info("location extraction returned invalid response, falling back to default")
        return _DEFAULT_EXTRACTION

    return LocationDateExtraction(city=data["city"], days_offset=data["days_offset"])
