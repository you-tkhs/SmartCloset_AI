# SmartCloset_AI

服の写真をアップロードすると、AI(YOLOv8-seg + OpenAI GPT-5.4-nano)が背景透過と属性抽出を行い、
クローゼット閲覧とLLMコーディネート提案ができるWebアプリを開発するリポジトリ。
AIロジックのPoCは完了済み。現在は docs/todo.md に沿ってアプリ本体(FastAPI + Next.js)を実装するフェーズ。

## ドキュメントの正本と読み方(重要)

- **正本は `docs/design.md`(設計書 ver2.0)、作業指示書は `docs/todo.md`**。実装判断に迷ったら必ず design.md に従う
- **2ファイルとも全文を読み込まないこと**(合計10万トークン超でコンテキストを圧迫する)。読み方:
  1. `docs/todo.md` から「現在のタスク」のセクションだけを読む(未チェックの最初のタスク。Grepでタスク ID や `実装済み [ ]` を検索して位置を特定し、offset/limit で部分読み)
  2. タスク本文が参照する design.md の節(例:「design.md 7.3節」)だけを、章見出しをGrepしてから部分読みする
  3. design.md 全体の索引は付録C.3(相互参照マップ)にある
- `docs/specification.md` / `prompt_design.md` / `evaluation.md` / `poc_history.md` はPoC記録。enum・プロンプトの出典として必要時のみ参照
- `docs/archive/` は歴史的記録。**実装の参照元にしない**

## 開発の進め方(厳守)

- タスク完了時は `docs/todo.md` のチェック欄・commit hash欄を更新する
- 設計変更が必要になったら: ①design.md更新 → ②todo.md更新 → ③設計変更commit → ④実装 → ⑤テスト → ⑥実装commit。コード先行の変更は禁止
- テスト: `cd backend && python -m pytest -m "not yolo" -q`(YOLO実推論込みは `-m yolo`。モデル重み `models/*.pt` はGit管理外)

## Git運用(厳守)

- **commit / push / merge はユーザーの明示的な指示があったときのみ実行する**
- mainへの直接実装禁止。Phaseごとに `phase/N-...` ブランチ(todo.md 0.1節)
- force push禁止(`--force-with-lease` も禁止)。Conventional Commits形式
- push前に .env・APIキー・DB・画像・モデル重みの混入がないか確認

## 実装の不変条件(design.mdを読まなくても守ること)

- status は `processing / completed / failed`(`complete` は使用禁止)
- エラー応答は `{detail, error_code, retryable}` に統一。レスポンスに絶対パス・スタックトレース・APIキーを含めない
- BackgroundTasks に渡すのは `item_id`(文字列)のみ。タスク内で新規DB Sessionを作りfinallyでclose
- ファイル削除は `storage_service.py` の共通関数のみ使用(重複実装禁止)
- uvicornは単一ワーカー(`--workers 1`)。シングルユーザー(user_id=1固定)
- 依存は `backend/requirements.txt`(ルートのrequirements.txtは研究環境用で使わない)

## 応答

日本語で応答する。既存ファイルの削除・上書き、新規ファイル作成は事前にユーザーへ確認する。
