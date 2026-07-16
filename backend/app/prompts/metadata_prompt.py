"""design.md 付録B.1: 属性抽出プロンプト・JSON Schema(正本)。

文言はノートブック確定版(ai_prototype/pipe-line/smartcloset_pipeline_functioned.ipynb
の build_metadata_prompt())と一字一句同一にすること。
"""

METADATA_PROMPT = """
このファッションアイテム画像を解析してください。

以下のJSON形式のみで返してください。

{
  "category": "",
  "color_primary": "",
  "color_secondary": "",
  "pattern": "",
  "material": "",
  "silhouette": ""
}

ルール:
- category は outer, tops, bottoms, dress, shoes, bag, hat, watch, glasses のいずれかに近いカテゴリで答える
- dress には ワンピース, ドレス, つなぎ, オーバーオール, ジャンプスーツ など上下が一体になった衣服を含める
- color_primary は主色を答える
- color_secondary は副色がなければ null
- pattern は柄・デザインを答える
- material は素材・質感を答える
- silhouette は形状・サイズ感・デザイン特徴を簡潔に答える
- 日本語で出力する
- JSON以外を出力しない
- 空欄は禁止
- 判断が難しい場合は「その他」を選ぶ

pattern は以下から最も近いものを必ず1つ選ぶ:
- 無地
- ストライプ
- ボーダー
- チェック
- ドット
- 花柄
- ロゴ
- プリント
- カモフラ
- その他

material は以下から最も近いものを必ず1つ選ぶ:
- コットン
- デニム
- ニット
- レザー
- ナイロン
- フリース
- ウール
- スウェット
- ファー
- ボア
- 金属
- 樹脂
- その他

注意:
- デニム、ニット、レザー、ナイロンなどは pattern ではなく material に入れる
- 無地のウィンドブレーカーは pattern=無地, material=ナイロン
- デニムパンツは pattern=無地, material=デニム
- ニット帽は pattern=無地, material=ニット
- ファーコートは pattern=無地, material=ファー
- ボアジャケットは pattern=無地, material=ボア
- 時計や眼鏡など素材判定が難しい場合は見た目から最も近い material を選ぶ
- 分からない場合は material="その他" とする
- material を空欄や null にしない
- pattern を空欄や null にしない

例:
{
  "category": "outer",
  "color_primary": "ブラウン",
  "color_secondary": null,
  "pattern": "無地",
  "material": "ファー",
  "silhouette": "ロングコート"
}
"""

METADATA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["outer", "tops", "bottoms", "dress", "shoes", "bag", "hat", "watch", "glasses"],
        },
        "color_primary": {"type": "string"},
        "color_secondary": {"type": ["string", "null"]},
        "pattern": {
            "type": "string",
            "enum": ["無地", "ストライプ", "ボーダー", "チェック", "ドット", "花柄", "ロゴ", "プリント", "カモフラ", "その他"],
        },
        "material": {
            "type": "string",
            "enum": [
                "コットン",
                "デニム",
                "ニット",
                "レザー",
                "ナイロン",
                "フリース",
                "ウール",
                "スウェット",
                "ファー",
                "ボア",
                "金属",
                "樹脂",
                "その他",
            ],
        },
        "silhouette": {"type": "string"},
    },
    "required": ["category", "color_primary", "color_secondary", "pattern", "material", "silhouette"],
    "additionalProperties": False,
}
