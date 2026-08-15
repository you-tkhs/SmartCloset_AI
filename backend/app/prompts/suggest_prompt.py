"""design.md 付録B.2: コーディネート提案プロンプト・JSON Schema(正本。全文を一字一句同一にすること)。"""

from app.schemas.weather import WeatherInfo

SUGGEST_SYSTEM_PROMPT = """あなたはプロのファッションスタイリストです。
ユーザーのクローゼットに実際にある衣服の中から、ユーザーの要望(用途・シーン)を最優先しつつ天気にも配慮した
コーディネートを提案してください。クローゼットにない衣服を提案してはいけません。"""

_USER_PROMPT_TEMPLATE = """# ユーザーの要望
{request_text}

# 天気情報
{weather_block}

# クローゼット(JSON)
{closet_json}

# ルール
- item_ids には上記クローゼットJSONに存在する id のみを含める
- dress を選ぶ場合は tops と bottoms を同時に選ばない
- 同一カテゴリからは原則1点まで(bag, hat, watch, glasses などの小物は状況に応じて任意)
- 基本構成は「tops + bottoms」または「dress」。outer や shoes、小物は天候・状況に応じて加える
- 該当するアイテムが乏しい場合も、その旨を suggestion_text で伝えつつ最善の組み合わせを提案する
- request_text から面接・デート・オフィス・カジュアルな外出などの「用途・シーン」を読み取り、フォーマル度・色柄の抑制・清潔感などTPOに合った選択を最優先で反映する
- 天気情報がある場合は、シーンに合わせた提案理由を主軸にしつつ天気にも簡潔に触れる(例:「面接向けにきちんと感のある一着に、明日は28℃予想なので涼しい素材を選びました」)
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
