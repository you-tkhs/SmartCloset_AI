# SmartCloset AI

**服の写真を撮るだけ。AIが切り抜き・属性抽出してクローゼット化し、天気と気分に合わせてコーディネートを提案するWebアプリ。**

- 開発ステータス: **AIロジックのPoC完了(2026-07)** → 現在Webアプリ実装フェーズ([ロードマップ](#ロードマップ))
- 技術スタック: YOLOv8-seg(ファインチューニング) / OpenAI GPT-5.4-nano / FastAPI / Next.js / SQLite / Docker + Caddy(Oracle Cloud ¥0運用)

<!-- TODO(デモ): PoCパイプラインの4連画像(Original / Mask / Transparent / Annotated)と完成後のアプリ画面を掲載する。
     ai_prototype/Poc/output/ は .gitignore 対象のため、掲載する画像は選抜して docs/images/ に意図的にcommitすること -->

## できること

1. **衣服の自動登録** — 服の写真をアップロードすると、ファインチューニング済みYOLOv8-segが背景を切り抜き、GPT-5.4-nanoがカテゴリ・色(2種)・柄・素材・シルエットを抽出して自動登録
2. **クローゼット閲覧** — 登録した服を背景透過画像で一覧・検索(カテゴリ/色/柄/素材フィルタ)
3. **コーディネート提案** — 「今日は大事な会議。きちんと見せたい」と入力すると、現在地の天気・気温とクローゼットの中身を踏まえてLLMが提案

## 背景

衣服管理アプリは「登録が面倒」で使われなくなる。1着ずつブランド・色・カテゴリを手入力し、背景まで綺麗に撮らなければならないからだ。本プロジェクトは**登録コストをAIで限りなくゼロに近づける**ことで、クローゼットのデジタル化と、毎朝の「何を着るか」という決断疲れの解消を狙う。

## 技術ハイライト

### 1. ドメインシフトを特定し、評価体系を作り直した

学習データ(Fashionpedia)の検証精度は良いのに実画像では機能しない——原因は、Fashionpediaが「人物着用の全身写真」で時計や帽子が極小に写るのに対し、本アプリの入力は「単品アップ写真」というスケールの根本的なずれ(ドメインシフト)だった。そこで実ユースケースに沿った**独自テストセット251枚**を構築し、プロダクト指標での評価に切り替えた。→ [開発経緯](docs/development_history.md)

### 2. クラス設計は3回作り直した(7→13→9クラス)

「accessory」1クラスが13種の形状の寄せ集めで学習が頭打ちになる問題を診断して分割。最終的に「良質な学習データが確保できない×プロダクト重要度が低い」4クラスを**捨てる判断**をして9クラスに確定した。→ [開発経緯](docs/development_history.md)

### 3. 弱点クラスはデータで解決した

Fashionpediaだけでは検出できなかった shoes / watch / glasses 等を、Roboflow Universe の補強データで統合(**train 52,784枚**)。破滅的忘却を避けるため追加学習ではなくゼロから再学習し、データ拡張+30epochで弱点クラスの認識に成功した。

### 4. モデル指標×プロダクト指標の二層評価

学習時の標準指標(**Mask mAP50 0.704**)と、実画像251枚の人手評価(**最終登録許容率84.9%**)の両方で評価。両者の乖離分析から「watchはvalで全クラス最高なのに実画像で最悪 → **アノテーション定義とプロダクト要件のずれ**」という診断まで行った。→ [評価と考察](docs/evaluation.md)

### 5. AI駆動開発を設計で統制する

アプリ実装はコーディングエージェント(Claude Code)に委譲する前提で、**設計書だけを見て実装できる粒度の設計書**([design.md](docs/design.md)・約1,800行)と**タスク単位の作業指示書**([todo.md](docs/todo.md))を整備。設計変更はコードより先に設計書を更新する design-first 運用で進める。

## アーキテクチャ

```
[ブラウザ/スマホ]
      │ HTTPS + Basic認証
      ▼
Caddy(:443) ── 外部公開はここのみ・自動HTTPS
 ├─ /api → FastAPI ── BackgroundTasks: YOLOv8-seg(9クラス) → 背景透過PNG
 │            │                        → GPT-5.4-nano属性抽出 → SQLite保存
 │            └─ OpenWeatherMap / OpenAI API
 └─ / → Next.js(クローゼットUI・コーデ提案UI)

デプロイ: Oracle Cloud Always Free ARM VM + Docker Compose(月額¥0 + OpenAI API従量のみ)
```

詳細は [docs/design.md](docs/design.md)(システム構成・API・DB・エラー設計・デプロイ)を参照。

## PoC結果(実画像251枚・人手評価)

| 指標 | 成功率 | 許容率 |
|---|---:|---:|
| YOLOセグメンテーション | 80.1% | 91.6% |
| カテゴリ抽出 | 97.2% | 97.6% |
| 主色抽出 | 99.6% | 99.8% |
| 柄抽出 | 96.0% | 98.8% |
| 素材抽出 | 88.0% | 96.0% |
| **最終登録判定** | **64.5%** | **84.9%** |

- 評価基準: [docs/evaluation.md](docs/evaluation.md) / モデルレベルの mAP: [docs/val_result_9class_30epoch_data_augmentation.md](docs/val_result_9class_30epoch_data_augmentation.md)
- 登録率のボトルネックはYOLO切り出し精度(watch等)。アプリではメタデータの手動補正機能で運用カバーし、補正データを再学習に還元する設計([design.md 18.2節](docs/design.md))

## 動かし方(現時点: AIパイプライン)

Webアプリは実装中のため、現在動かせるのはAIパイプラインのNotebookです。

```bash
git clone https://github.com/you-tkhs/SmartCloset_AI.git
cd SmartCloset_AI
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
jupyter lab ai_prototype/pipe-line/smartcloset_pipeline_functioned.ipynb
```

- **注意**: 学習済みモデル重み(`models/fashionpedia_9class_with_data_augmentation.pt`)はGit管理外のため、リポジトリのcloneだけでは実行できません(再現には Fashionpedia+補強データでの学習が必要。手順は `training/` のNotebook参照)
- Webアプリ(FastAPI + Next.js)の起動手順は Phase 5 完了時にここへ追記します <!-- TODO(T5-3) -->

## ロードマップ

実装は [docs/todo.md](docs/todo.md) のタスクに沿って進行(進捗の正本もtodo.md)。

- [x] AIロジックPoC(セグメンテーション・属性抽出・評価)
- [ ] Phase 0: backend基盤(FastAPI・SQLite・ヘルスチェック)
- [ ] Phase 1: 画像アップロード+AIパイプライン(非同期処理・異常系)
- [ ] Phase 2: クローゼットCRUD(閲覧・手動補正・削除)
- [ ] Phase 3: コーディネート提案(天気API+LLM)
- [ ] Phase 4: フロントエンド(Next.js 4画面)
- [ ] Phase 5: 仕上げ(エラー処理・ログ・README起動手順)
- [ ] Phase 6: デプロイ(Oracle Cloud・¥0運用・バックアップ)

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [docs/design.md](docs/design.md) | 設計書 ver2.0(正本)— アーキテクチャ・API・DB・異常系・デプロイ |
| [docs/todo.md](docs/todo.md) | 実装作業指示書(Phase 0〜6・全タスク) |
| [docs/development_history.md](docs/development_history.md) | 開発経緯 — 技術的意思決定の記録(ドメインシフト発見・クラス設計の変遷) |
| [docs/specification.md](docs/specification.md) | AIシステム仕様・PoC結果 |
| [docs/prompt_design.md](docs/prompt_design.md) | LLMプロンプト設計・改善履歴 |
| [docs/evaluation.md](docs/evaluation.md) | 評価基準・mAPと人手評価の対応考察 |
| [docs/val_result_9class_30epoch_data_augmentation.md](docs/val_result_9class_30epoch_data_augmentation.md) | 学習時のクラス別mAP |
| [docs/archive/](docs/archive/) | 初期構想メモ・旧設計書(歴史的記録) |

<!-- TODO: 開発記事(Zenn等)を書いたらここにリンクを追加 -->

## 作者

髙橋 葉(岩手大学大学院 修士1年)— UAV空撮画像による水田の3次元復元・収量予測を研究。E資格保有。
