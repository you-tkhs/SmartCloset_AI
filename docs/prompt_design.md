# Prompt Design

## Overview

本システムでは、YOLOv8-segにより背景透過した単一ファッションアイテム画像を入力とし、
OpenAI GPT-5.4-nanoを用いて衣服属性を抽出する。

出力はJSONのみとし、後続のデータベース登録およびコーディネート推薦に利用する。

---

# Model

- GPT-5.4-nano

---

# Input

- Background Removed PNG (RGBA)
- 単一ファッションアイテム画像

---

# Output Format

必ず以下のJSON形式のみを返す。

```json
{
  "category": "",
  "color_primary": "",
  "color_secondary": "",
  "pattern": "",
  "material": "",
  "silhouette": ""
}
```

JSON以外の説明・Markdown・コードブロックは出力しない。

---

# Category Rules

categoryは必ず以下の9カテゴリから1つ選択する。

| category | 対象 |
|----------|------|
| outer | コート、ジャケット、ブルゾン、カーディガンなど羽織る衣服 |
| tops | Tシャツ、シャツ、ブラウス、パーカー、ニットなど上半身のみの衣服 |
| bottoms | パンツ、スカート、ショートパンツなど下半身のみの衣服 |
| dress | ワンピース、ドレス、つなぎ、ジャンプスーツ、オールインワン、オーバーオールなど上下が一体となった衣服 |
| shoes | スニーカー、革靴、ブーツ、サンダル |
| bag | ハンドバッグ、ショルダーバッグ、リュック |
| hat | キャップ、ハット、ニット帽 |
| watch | 腕時計 |
| glasses | メガネ、サングラス |

最も近いカテゴリを必ず1つ返す。

---

# Color Rules

## color_primary

衣服の面積が最も大きい色を返す。

例

- 黒
- 白
- ネイビー
- グレー
- ベージュ
- ブラウン
- カーキ
- 赤
- 青
- 緑

など。

## color_secondary

副色が明確に存在する場合のみ返す。

存在しない場合

```json
null
```

とする。

---

# Pattern Rules

patternは必ず以下から1つ選択する。

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

### 注意

デニム・ニット・レザーなどは柄ではない。

例

×

pattern = デニム

○

pattern = 無地

material = デニム

---

# Material Rules

materialは必ず以下から1つ選択する。

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

時計・眼鏡など複数素材から構成される場合は、
見た目で最も支配的な素材を選択する。

どうしても判断できない場合のみ

```
その他
```

とする。

---

# Silhouette Rules

silhouetteには衣服の形状を20文字程度で簡潔に記述する。

例

- ロングコート
- オーバーサイズ
- ストレートパンツ
- ワイドパンツ
- フレアスカート
- ニット帽
- ラウンドフレーム

自由記述とする。

---

# Priority Rules

以下を優先する。

- JSON以外は出力しない
- categoryは必ず9カテゴリから選択する
- patternは必ず候補から1つ選択する
- materialは必ず候補から1つ選択する
- color_secondaryは存在しなければnull
- 空文字は禁止

---

# Failure Handling

判別が難しい場合

- category：最も近いカテゴリ
- pattern：その他
- material：その他

を返す。

---

# Prompt Improvement History

## PoC v1

PoCではdressカテゴリの定義として

- つなぎ
- ジャンプスーツ
- オールインワン
- オーバーオール

を明示していなかったため、
これらをtopsまたはbottomsへ誤分類するケースが確認された。

## Current Version

dressカテゴリの定義を明確化し、
上下が一体となった衣服をすべてdressとして扱う仕様へ変更した。