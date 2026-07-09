# Evaluation Rule

## Purpose

PoC性能評価

---

### YOLOのセグメンテーション評価

今回は対象物を切り出し、マスクを生成することが重要である。そのため、YOLOの予測クラスが正解クラスと一致しているかどうかは主評価にしない。

| 評価 | 基準 |
|---|---|
| ○ | 対象物を見つけ、きちんと切り出している |
| △ | 一部欠損、または背景混入がある |
| × | 検出失敗、または登録に使えない |

### LLMによる属性認識評価

| 項目 | ○ | △ | × |
|---|---|---|---|
| category | 正しい分類 | 近い分類・上位概念 | 明確に違う分類 |
| color_primary | 主色が一致 | 近い色・明暗差程度 | 違う色 |
| pattern | 柄が一致 | 近い柄・判断が微妙 | 違う柄 |
| material | 素材感が一致 | 近い素材・判断が微妙 | 違う素材 |


### 最終登録判定

| 評価 | 基準 |
|---|---|
| ○ | YOLO切り出し○、category○、color_primary○、pattern○、material○ |
| △ | YOLO△、または属性が一部△ |
| × | YOLO×、または登録不可レベルの誤り |

# Current PoC Result

| Item | Success | Acceptable |
|------|---------|------------|
| YOLO | 80.1% | 91.6% |
| Category | 97.2% | 97.6% |
| Color | 99.6% | 99.8% |
| Pattern | 96.0% | 98.8% |
| Material | 88.0% | 96.0% |
| Final Registration | 64.5% | 84.9% |

---

# Known Issues

## YOLO

- Watchのベルト欠損
- Shoesのマスク欠損
- Bagのショルダー誤切り出し

## Prompt

dressに

- つなぎ
- オーバーオール

を含める定義不足

---

# Future Improvements

- Watchセグメンテーション改善
- Prompt改善
- YOLO再学習
- VLM比較
- 本番データ評価