"""design.md 付録B.3: 場所・日付抽出プロンプト・JSON Schema(正本。全文を一字一句同一にすること)。"""

from datetime import date

_WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

LOCATION_SYSTEM_PROMPT = """あなたはユーザーの文章から、天気を調べるために必要な「場所」と「日付」だけを
抽出するアシスタントです。コーディネートの提案は行わず、場所と日付の抽出のみを行ってください。"""

_USER_PROMPT_TEMPLATE = """# 本日の日付
{today}({weekday})

# ユーザーの文章
{request_text}

# 指示
- 文章中に地名(市区町村・都道府県・国・地方名等)があれば city に設定する。都道府県名や地方名のみの場合も対象
  (例: 「沖縄」「北海道」も地名として扱う)
- city は OpenWeatherMap で検索可能な英語の代表都市名に変換する
  (例: 沖縄→"Naha,JP"、北海道→"Sapporo,JP"、那覇→"Naha,JP"、東京→"Tokyo,JP"、大阪→"Osaka,JP")
- city を null にしてよいのは、文章中に地名が一切登場しない場合のみ
- 文章中の日付表現(今日、明日、明後日、○月○日、来週の月曜日 等)を本日の日付を基準に判断し、
  本日からの経過日数を days_offset に設定する(今日または日付指定なしは0、明日は1、明後日は2、
  というように最大5まで)
- 6日以上先の日付、または過去の日付・不明瞭な日付の場合は days_offset を6にする
"""


def build_location_user_prompt(request_text: str, today: date | None = None) -> str:
    today = today or date.today()
    return _USER_PROMPT_TEMPLATE.format(
        today=today.isoformat(), weekday=_WEEKDAY_JA[today.weekday()], request_text=request_text
    )


LOCATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": ["string", "null"]},
        "days_offset": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5, 6]},
    },
    "required": ["city", "days_offset"],
    "additionalProperties": False,
}
