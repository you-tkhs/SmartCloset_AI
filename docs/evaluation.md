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

# Model-level Metrics (mAP)

学習時の `model.val()` による標準指標(Box/Mask の P・R・mAP50・mAP50-95、クラス別)は
[val_result_9class_30epoch_data_augmentation.md](val_result_9class_30epoch_data_augmentation.md) を参照。
全体では Mask mAP50 = 0.704 / mAP50-95 = 0.530。

## 人手評価との対応(考察)

- **shoes / bag**: mAP50 は高いが mAP50-95 が大きく低下(shoes 0.763→0.453、bag 0.663→0.458)。
  「おおまかには検出できるが境界精度が甘い」ことを示し、人手評価の「shoesマスク欠損」「bagショルダー誤切り出し」と数値的に整合する。
- **watch**: val では全クラス最高(Mask mAP50 0.880 / mAP50-95 0.781)だが、人手評価では最悪(ベルト欠損)。
  watch の学習・検証データは Roboflow 補強データ由来であり、アノテーション定義が文字盤中心に寄っている可能性が高い。
  つまり watch の問題はモデルの能力不足ではなく**アノテーション定義とプロダクト要件(ベルト込みの切り出し)のずれ**と診断できる。
  改善は再学習パラメータの調整ではなく「ベルト込みでアノテーションされたデータの追加」が正攻法。
- **tops**: Mask Recall 0.464 と最弱だが、これは Fashionpedia に重ね着・遮蔽ありのインスタンスが多いため。
  実運用は「単品撮影+最高信頼度1件採用」のため低 Recall の実害は小さく、実際に PoC の切り出し許容率は 91.6% だった。

mAP はモデルレベルのベンチマーク、人手○△×評価はプロダクトレベルの指標であり、両者は補完関係にある。

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