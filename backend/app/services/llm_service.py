"""design.md 8.3節・付録B.1: llm_service.extract_metadata()。

ノートブックのextract_metadata_with_openai()/parse_json_safely()を移植。
response_formatはノートブックの不完全な指定({"type": "json_schema"}のみ)を
修正し、スキーマ本体を含む完全形式で送信する。
"""

import base64
import json
import logging
import time
from pathlib import Path

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from app.config import settings
from app.prompts.metadata_prompt import METADATA_JSON_SCHEMA, METADATA_PROMPT

logger = logging.getLogger(__name__)

_RETRYABLE_API_ERRORS = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)
_METADATA_KEYS = ["category", "color_primary", "color_secondary", "pattern", "material", "silhouette"]
_INITIAL_RETRY_DELAY_SECONDS = 1.0


class LlmServiceError(Exception):
    """OpenAI呼び出しがリトライ後も失敗した場合。"""


def parse_json_safely(text: str | None) -> dict:
    """OpenAIの出力をJSONとして安全に読み込む(ノートブックと同一ロジック)。"""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        cleaned = (text or "").strip().replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(cleaned)
        except (TypeError, ValueError):
            return {
                **{key: None for key in _METADATA_KEYS},
                "raw_response": text,
                "openai_error": "json_parse_error",
            }

    for key in _METADATA_KEYS:
        if key not in data:
            data[key] = None

    return data


def _image_to_base64(image_path: Path) -> str:
    return base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")


def _is_valid_metadata(data: dict) -> bool:
    if "openai_error" in data:
        return False
    if any(key not in data for key in _METADATA_KEYS):
        return False
    category_enum = METADATA_JSON_SCHEMA["properties"]["category"]["enum"]
    pattern_enum = METADATA_JSON_SCHEMA["properties"]["pattern"]["enum"]
    material_enum = METADATA_JSON_SCHEMA["properties"]["material"]["enum"]
    if data.get("category") not in category_enum:
        return False
    if data.get("pattern") not in pattern_enum:
        return False
    if data.get("material") not in material_enum:
        return False
    if not isinstance(data.get("color_primary"), str) or not data.get("color_primary"):
        return False
    if not isinstance(data.get("silhouette"), str) or not data.get("silhouette"):
        return False
    return True


def extract_metadata(client: OpenAI, image_path: Path) -> dict:
    """透過PNGをbase64で送り、6属性のdictを返す。

    OpenAI呼び出しはOPENAI_MAX_RETRIES回まで指数バックオフ(1秒→2秒)でリトライする。
    リトライ後も失敗した場合は LlmServiceError を送出する。
    """
    base64_image = _image_to_base64(image_path)
    delay = _INITIAL_RETRY_DELAY_SECONDS
    last_error: Exception | None = None

    for attempt in range(settings.OPENAI_MAX_RETRIES + 1):
        is_last_attempt = attempt == settings.OPENAI_MAX_RETRIES

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": METADATA_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "clothing_metadata",
                        "strict": True,
                        "schema": METADATA_JSON_SCHEMA,
                    },
                },
            )
        except _RETRYABLE_API_ERRORS as e:
            last_error = e
            logger.warning("OpenAI API call failed (attempt %d/%d): %s", attempt + 1, settings.OPENAI_MAX_RETRIES + 1, type(e).__name__)
            if not is_last_attempt:
                time.sleep(delay)
                delay *= 2
            continue

        data = parse_json_safely(response.choices[0].message.content)
        if _is_valid_metadata(data):
            return data

        last_error = LlmServiceError("json_parse_error")
        logger.warning("OpenAI response JSON invalid (attempt %d/%d)", attempt + 1, settings.OPENAI_MAX_RETRIES + 1)
        if not is_last_attempt:
            time.sleep(delay)
            delay *= 2

    logger.error("metadata extraction failed after retries")
    raise LlmServiceError("metadata extraction failed after retries") from last_error
