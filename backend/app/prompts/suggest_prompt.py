"""design.md 付録B.2: コーディネート提案プロンプト・JSON Schema(正本。全文を一字一句同一にすること)。"""

from app.schemas.weather import WeatherInfo

SUGGEST_SYSTEM_PROMPT = """あなたはプロのファッションスタイリストです。
ユーザーのクローゼットに実際にある衣服の中から、天気とユーザーの要望に最適な
コーディネートを提案してください。クローゼットにない衣服を提案してはいけません。"""

_USER_PROMPT_TEMPLATE = """# 天気情報
{weather_block}

# ユーザーの要望
{request_text}

# クローゼット(JSON)
{closet_json}

# ルール
- item_ids には上記クローゼットJSONに存在する id のみを含める
- dress を選ぶ場合は tops と bottoms を同時に選ばない
- 同一カテゴリからは原則1点まで(bag, hat, watch, glasses などの小物は状況に応じて任意)
- 基本構成は「tops + bottoms」または「dress」。outer や shoes、小物は天候・状況に応じて加える
- 該当するアイテムが乏しい場合も、その旨を suggestion_text で伝えつつ最善の組み合わせを提案する
- 天気情報がある場合は、天気に触れながら提案理由を自然に述べる(例:「明日は28℃予想なので涼しい素材を選びました」)
- suggestion_text は200字以内の提案文、styling_reason は選定理由を簡潔に書く
- 日本語で出力する"""

_WEATHER_UNAVAILABLE_BLOCK = "天気情報なし(天気を考慮せずに提案してください)"


def _format_date_ja(iso_date: str) -> str:
    _, month, day = iso_date.split("-")
    return f"{int(month)}月{int(day)}日"


def build_suggest_user_prompt(weather: WeatherInfo | None, request_text: str, closet_json: str) -> str:
    if weather is None:
        weather_block = _WEATHER_UNAVAILABLE_BLOCK
    else:
        date_part = f" / 日付: {_format_date_ja(weather.forecast_date)}" if weather.forecast_date else ""
        weather_block = (
            f"都市: {weather.city} / 気温: {weather.temp}°C / 体感: {weather.feels_like}°C / "
            f"天候: {weather.description} / 湿度: {weather.humidity}%{date_part}"
        )

    return _USER_PROMPT_TEMPLATE.format(
        weather_block=weather_block, request_text=request_text, closet_json=closet_json
    )


SUGGEST_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "item_ids": {"type": "array", "items": {"type": "string"}},
        "suggestion_text": {"type": "string"},
        "styling_reason": {"type": "string"},
    },
    "required": ["item_ids", "suggestion_text", "styling_reason"],
    "additionalProperties": False,
}
