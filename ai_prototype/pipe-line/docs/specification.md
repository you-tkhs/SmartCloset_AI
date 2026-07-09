# SmartCloset AI Specification

## 1. Overview

SmartCloset AIは、単一のファッションアイテム画像を入力として、衣服領域の切り出し、衣服属性の抽出、クローゼット登録を自動化するAIシステムである。

本システムはAIを活用し、衣服情報の登録コストを大幅に削減することを目的とする。

将来的には以下の機能を実装予定である。

- クローゼット管理
- コーディネート推薦
- 天気連携
- LLMスタイリスト
- Webアプリケーション化

---

# 2. Current Development Phase

現在はPoC（Proof of Concept）段階であり、AIパイプラインの有効性を検証した。

PoCでは以下を実施した。

- YOLOv8-segによる衣服領域抽出
- 背景透過PNG生成
- OpenAI GPT-5.4-nanoによる属性抽出
- CSV保存
- 人手評価
- 成功率・許容率の算出

---

# 3. Target Input

入力画像は単一ファッションアイテム画像とする。

対応形式

- jpg
- jpeg
- png
- webp

PoCではコーディネート画像ではなく、
単一アイテム画像のみを対象とする。

---

# 4. Recognition Pipeline

```
Input Image
        │
        ▼
YOLOv8-seg
        │
        ▼
Mask Generation
        │
        ▼
Transparent PNG
        │
        ▼
OpenAI GPT-5.4-nano
        │
        ▼
Metadata JSON
        │
        ▼
CSV
        │
        ▼
Manual Evaluation
        │
        ▼
PoC Summary
```

---

# 5. Supported Categories

現在認識対象とするカテゴリは9種類である。

| Category | Definition |
|-----------|------------|
| outer | コート・ジャケット・ブルゾン・カーディガンなど羽織る衣服 |
| tops | Tシャツ・シャツ・ブラウス・パーカー・ニットなど上半身のみの衣服 |
| bottoms | パンツ・スカート・ショートパンツなど下半身のみの衣服 |
| dress | ワンピース・ドレス・つなぎ・ジャンプスーツ・オールインワン・オーバーオールなど上下が一体となった衣服 |
| shoes | スニーカー・革靴・ブーツ・サンダル |
| bag | ハンドバッグ・ショルダーバッグ・リュック |
| hat | キャップ・ハット・ニット帽 |
| watch | 腕時計 |
| glasses | メガネ・サングラス |

---

# 6. AI Models

## 6.1 Segmentation

モデル

YOLOv8-seg

学習データ

Fashionpedia

出力

- segmentation mask
- transparent PNG
- annotated image
- predicted class
- confidence
- detected instance数

---

## 6.2 Attribute Extraction

モデル

OpenAI GPT-5.4-nano

入力

YOLOによって生成された背景透過PNG

出力

JSON

---

# 7. Output Metadata

LLMは以下のJSONを返す。

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

各フィールドの意味

| Field | Description |
|---------|-------------|
| category | 衣服カテゴリ |
| color_primary | 主色 |
| color_secondary | 副色（存在しなければnull） |
| pattern | 柄 |
| material | 見た目から推定される代表的な素材 |
| silhouette | 形状・シルエット・デザイン特徴 |

---

# 8. Pattern Candidates

patternは以下から必ず1つ選択する。

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

---

# 9. Material Candidates

materialは以下から必ず1つ選択する。

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

materialは実際の素材ではなく、

**画像から推定される最も代表的な素材**

を表す。

そのため、

- 本革
- 合成皮革

など画像のみでは判別困難な場合は、
見た目から最も妥当な素材を返す。

---

# 10. PoC Dataset

対象画像数

251枚

対象

単一アイテム画像

カテゴリ

- outer
- tops
- bottoms
- dress
- shoes
- bag
- hat
- watch
- glasses

---

# 11. PoC Result

| Metric | Success | Acceptable |
|---------|---------:|-----------:|
| YOLO Segmentation | 80.1% | 91.6% |
| Category | 97.2% | 97.6% |
| Primary Color | 99.6% | 99.8% |
| Pattern | 96.0% | 98.8% |
| Material | 88.0% | 96.0% |
| Final Registration | 64.5% | 84.9% |

---

# 12. Current Findings

PoCより以下が確認できた。

## LLM

GPT-5.4-nanoは

- category
- color
- pattern

において非常に高い精度を示した。

materialも88%の成功率を示し、
画像からの素材推定は十分実用可能であることを確認した。

---

## dress

PoC実施時点では、

LLMプロンプト内で

- つなぎ
- オーバーオール
- ジャンプスーツ

をdressカテゴリに含めることを明示していなかった。

そのため、

一部をtopsまたはbottomsへ誤分類するケースが確認された。

これはLLM性能ではなく、
カテゴリ定義・プロンプト設計に起因する問題である。

---

## YOLO

最終登録成功率を下げた最大要因は
YOLOv8-segによる切り出し精度であった。

特に

- watch
- shoes
- bag

でマスク欠損が多く確認された。

一方、

watchを除くカテゴリでは許容率90%以上となり、

Fashionpediaのみの学習モデルと比較すると
追加ファインチューニングは大きな改善となった。

---

# 13. Known Issues

## YOLO

watch

- ベルト欠損

shoes

- マスク欠損

bag

- ショルダー部と背景が混ざる

---

## Prompt

PoC実施時のプロンプトでは

dressカテゴリに

- つなぎ
- オーバーオール
- ジャンプスーツ

を含める定義が不足していた。

最新版プロンプトでは改善済み。

---

# 14. Future Development

システム全体として以下を実装予定。

Backend

- FastAPI

Database

- PostgreSQL

Frontend

- Next.js

Application

- クローゼット管理
- 衣服検索
- フィルタ検索
- コーディネート推薦
- 天気連携
- LLMスタイリスト

---

# 15. Future Improvements

今後のAI改善方針

- watchを中心とした小物カテゴリの追加学習
- セグメンテーション精度改善
- Prompt設計改善
- 実ユーザー画像による評価
- コーディネート画像への対応
- VLMとの性能比較