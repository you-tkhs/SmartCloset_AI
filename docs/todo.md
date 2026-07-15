# SmartCloset AI 実装TODO(作業指示書)

**ver 1.0 / 2026-07 — `docs/design.md` ver 2.0 に対応**

本書は `docs/design.md` を実装に落とすための作業指示書である。Claude Code は本書を**上から順に**実行する。各タスクは design.md の該当節を参照しており、**両ファイルのみで実装・テスト・commit・GitHubへのpushまで完遂できる**ことを完成条件とする。

---

## 0. 運用ルール

### 0.1 Git運用(design.md 17.2節。厳守)

- mainブランチへの直接実装は行わない。Phase開始時に `main` から `phase/N-...` ブランチを作成する
- 小さな論理単位ごとにcommitする。相互依存する小タスクは1つの論理commitにまとめてよいが、**Phaseをまたぐ変更を同一commitに含めない**
- 各commit前: 対象テストを実行し、`git diff` と `git diff --cached` を確認する
- 各Phase完了時: 全テスト実行 → セルフレビュータスク消化 → GitHubへpush → mainへmerge
- **force push禁止(`--force-with-lease` も禁止)**
- push前に `.env`・APIキー・認証情報・SQLite DB・画像・ログ・モデル重み・大容量ファイルが含まれていないことを確認する
- **commit・push・mergeなどリポジトリを書き換える操作は、ユーザーの明示的な指示・承認のもとでのみ実行する**

### 0.2 コミットメッセージ(Conventional Commits)

```text
feat(upload): add validated image upload flow
fix(storage): clean files after persistence failure
feat(pipeline): recover interrupted processing records
test(upload): cover invalid image and storage failures
docs(design): define upload compensation workflow
chore(backend): scaffold project structure
```

### 0.3 設計変更時の手順(厳守。design.md 1.4節)

1. `docs/design.md` を更新 → 2. `docs/todo.md` を更新 → 3. 設計変更をcommit → 4. コード実装 → 5. テスト追加/修正 → 6. 実装commit → 7. Phase完了時にpush。
**コードのみを先に変更し、設計書を後から合わせる運用は禁止。**

### 0.4 タスク記載フォーマット

各タスクは以下の項目を持つ。チェック欄・commit hash欄は実施時に記入する。

> **目的 / 前提条件 / 変更対象ファイル / 実装内容 / 影響範囲 / 完了条件 / 検証コマンド / 想定される正常結果 / 想定される異常結果 / 推奨コミットメッセージ / チェック欄 / commit hash / 備考**

### 0.5 Phase完了セルフレビュー(全Phase共通の固定チェックリスト)

各Phaseの最終タスク(`TN-SR`)で以下を必ず実施する。

```
[ ] 実装と docs/design.md の差分確認(差分があれば0.3の手順で先に設計書を更新)
[ ] 実装と docs/todo.md の差分確認(完了タスクのチェック・hash記入漏れ含む)
[ ] API仕様(design.md 6章)と実装の差分確認
[ ] DBモデルとDDL(design.md 9章)の差分確認
[ ] 環境変数・設定値一覧(design.md 5章)と実装の差分確認
[ ] テスト計画(design.md 14.1節)と実装済みテストの差分確認
[ ] .gitignore の確認(backend/storage, backend/data, .env が除外されているか)
[ ] 機密情報混入確認(git diff --stat origin/main、grep でAPIキー・パスワードを確認)
[ ] 全テスト実行(cd backend && python -m pytest -m "not yolo" -q → 可能なら pytest -q)
[ ] Phase完了commit
[ ] GitHubへのpush(ユーザー承認のもと)
[ ] push済みcommit hashを本書に記録
```

### 0.6 検証コマンドの前提

- backend作業は `backend/` を作業ディレクトリとし、venv(例: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`)を使用
- 開発サーバー: `uvicorn app.main:app --reload --port 8000`(ルートから見ると `cd backend` して実行)
- pytest: `python -m pytest -q`(YOLO実推論を除くときは `-m "not yolo"`)
- モデル重み `models/fashionpedia_9class_with_data_augmentation.pt` がローカルに存在すること(Git管理外)

---

# Phase 0: backend基盤(ブランチ: `phase/0-backend-foundation`)

**ゴール**: uvicorn起動、`/api/health` が `model_loaded:true` を返し、pytestが通る。

## T0-1: ブランチ作成とプロジェクト雛形

- **目的**: backendの骨格と依存関係・Git除外設定を整える
- **前提条件**: mainが最新であること
- **変更対象ファイル**: `.gitignore`、`backend/requirements.txt`、`backend/.env.example`、`backend/app/`配下の空パッケージ(`__init__.py`群)、`backend/tests/`、`backend/storage/.gitkeep`は置かない(生成はコードで行う)
- **実装内容**:
  - `git switch -c phase/0-backend-foundation`
  - design.md 4.1節のディレクトリを作成(空の `__init__.py` を各パッケージに)
  - design.md 4.3節の `requirements.txt` を作成
  - design.md 4.4節の `.gitignore` 追記(`backend/storage/` `backend/data/` `backend/.env` `deploy/.env`)
  - design.md 5.1節の `.env.example`(キー名のみ・実値なし)
- **影響範囲**: 新規のみ(既存コードに影響なし)
- **完了条件**: `pip install -r requirements.txt` が成功。`git status` で storage/data/.env が追跡されない
- **検証コマンド**: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python -c "import fastapi, ultralytics, openai"`
- **想定される正常結果**: importエラーなし
- **想定される異常結果**: ARM/CUDA関連でtorchの解決に失敗する場合はCPU版を明示(design.md 15.2節)
- **推奨コミットメッセージ**: `chore(backend): scaffold project structure and dependencies`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `b1da784`
- **備考**: ルートrequirements.txtは使わない(design.md 18.3節)

## T0-2: config.py(設定一元管理)

- **目的**: design.md 5.2節の全設定値を pydantic-settings で定義する
- **前提条件**: T0-1
- **変更対象ファイル**: `backend/app/config.py`
- **実装内容**: `Settings` クラスに 5.2節の**全設定名・初期値**を定義(MODEL_PATH, CONF_THRES, OPENAI_MODEL, OPENAI_MAX_RETRIES, MAX_UPLOAD_SIZE_MB, UPLOAD_CHUNK_SIZE_BYTES, MAX_IMAGE_WIDTH/HEIGHT/PIXELS, MAX_IMAGE_LONG_SIDE, SQLITE_BUSY_TIMEOUT_MS, PROCESSING_STALE_MINUTES, AI_MAX_CONCURRENCY, MIN_FREE_STORAGE_MB, BACKUP_RETENTION_COUNT, STORAGE_DIR, DATA_DIR, CORS_ORIGINS, DATABASE_URL, OPENAI_API_KEY, OPENWEATHER_API_KEY, DEFAULT_CITY)。`.env` 読み込み対応
- **影響範囲**: 全モジュールが参照する基盤
- **完了条件**: 設定値が環境変数で上書きできる
- **検証コマンド**: `cd backend && python -c "from app.config import settings; print(settings.CONF_THRES, settings.SQLITE_BUSY_TIMEOUT_MS)"`
- **想定される正常結果**: `0.25 5000`
- **想定される異常結果**: .env未配置でもデフォルト値で動作する(APIキーはNone許容とし、使用時にチェック)
- **推奨コミットメッセージ**: `feat(config): add centralized settings with pydantic-settings`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `f49c0e0`
- **備考**: 設定名・初期値は design.md 5.2節と一字一句一致させる

## T0-3: database.py とSQLAlchemyモデル

- **目的**: SQLite(WAL・busy_timeout)+Session管理+2テーブルの定義(design.md 9章)
- **前提条件**: T0-2
- **変更対象ファイル**: `backend/app/database.py`、`backend/app/models/clothing_item.py`、`backend/app/models/coordinate_log.py`
- **実装内容**:
  - engine(`check_same_thread=False`)+connectイベントで `PRAGMA journal_mode=WAL` / `PRAGMA busy_timeout`(sqlite時のみ分岐)
  - `get_db()`(yield依存性)、`create_session()`(BackgroundTasks用)、`init_db()`
  - `ClothingItem` / `CoordinateLog` を design.md 9.2〜9.3節のDDLと一致するよう定義(UUID文字列PK・UTC日時・idempotency_key UNIQUE)
- **影響範囲**: 全ルーター・サービス
- **完了条件**: create_allでDDL相当のテーブルが生成され、WALが有効
- **検証コマンド**: `cd backend && python -c "from app.database import init_db, engine; init_db(); import sqlite3; c=sqlite3.connect('data/smartcloset.db'); print(c.execute('PRAGMA journal_mode').fetchone()); print([r[1] for r in c.execute('PRAGMA table_info(clothing_items)')])"`
- **想定される正常結果**: `('wal',)` と design.md 9.2節の全カラム名
- **想定される異常結果**: カラム名の不一致(→design.mdに合わせて修正)
- **推奨コミットメッセージ**: `feat(db): add sqlite engine with WAL and ORM models`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `2a71cc6`
- **備考**: SQLite固有処理をdatabase.py外に書かない(design.md 9.4節)

## T0-4: storage_service 基盤

- **目的**: ディレクトリ初期化・冪等削除・空き容量確認・URL変換(design.md 10章)
- **前提条件**: T0-2
- **変更対象ファイル**: `backend/app/services/storage_service.py`
- **実装内容**: `init_storage()`(tmp/originals/transparent/masks/annotated+data作成)、`delete_item_files()` / `delete_generated_files()` / `delete_tmp()`(冪等・例外を送出しない・失敗はWARNINGログ)、`check_free_space()`(shutil.disk_usage)、`to_public_url()`(originals/transparent以外はNone)。パス生成ヘルパー(`original_path(item_id, ext)` 等、命名規則10.2節)
- **影響範囲**: upload・pipeline・items(DELETE)・health
- **完了条件**: 単体テストが通る(存在しないファイル削除で例外が出ない、URL変換の正誤)
- **検証コマンド**: `cd backend && python -m pytest tests/test_services.py -q -k storage`
- **想定される正常結果**: pass
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(storage): add storage service with idempotent deletion`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `a489b1a`
- **備考**: 削除処理は今後この関数群のみを使う(重複実装禁止。design.md 10.4節)

## T0-5: main.py(lifespan)と health ルーター

- **目的**: 起動時チェック(design.md 5.3節)とヘルスチェック(6.10節)
- **前提条件**: T0-3, T0-4
- **変更対象ファイル**: `backend/app/main.py`、`backend/app/routers/health.py`、`backend/app/schemas/error.py`
- **実装内容**:
  - lifespan: init_storage → init_db → **MODEL_PATH存在チェック(無ければRuntimeErrorで起動失敗)** → YOLOロードを `app.state.yolo_model` へ → OpenAIクライアントを `app.state.openai_client` へ(キー未設定ならNone+WARNINGログ) → tmp掃除。stale復旧の呼び出しはT1-8で追加
  - CORS(settings.CORS_ORIGINS)、StaticFilesマウント(originals/transparentの2つのみ)
  - `GET /api/health`: model_loaded / database_available / storage_writable / storage_free_mb。絶対パスを含めない
  - `ErrorResponse` スキーマとグローバル例外ハンドラの骨格(13.1節。HTTPException→統一形式、未処理例外→500 internal_error)
- **影響範囲**: アプリ全体
- **完了条件**: uvicorn起動、healthがok。MODEL_PATHをダミー値にすると起動失敗する
- **検証コマンド**: `cd backend && uvicorn app.main:app --port 8000 &` → `curl -s localhost:8000/api/health`
- **想定される正常結果**: `{"status":"ok","model_loaded":true,"database_available":true,"storage_writable":true,"storage_free_mb":<数値>}`
- **想定される異常結果**: 重み欠落時に起動失敗しRuntimeErrorがログに出る(これが正しい挙動)
- **推奨コミットメッセージ**: `feat(app): add lifespan startup checks and health endpoint`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `93c5cc2`
- **備考**: uvicornは常に単一ワーカー(design.md 18.3節)

## T0-6: テスト基盤(conftest)と health テスト

- **目的**: 一時SQLite+一時storageで動くTestClient基盤(design.md 14.1節)
- **前提条件**: T0-5
- **変更対象ファイル**: `backend/tests/conftest.py`、`backend/tests/test_health.py`、`backend/tests/test_services.py`
- **実装内容**: tmp_path系フィクスチャで STORAGE_DIR/DATA_DIR/DATABASE_URL を上書きした `TestClient`。YOLOロードはモデル存在時のみ(無ければ `app.state.yolo_model` にダミーを注入するフィクスチャを用意し、YOLO実推論テストは `@pytest.mark.yolo`)。pytest.ini(またはpyproject)に `markers = yolo` を定義
- **影響範囲**: 以後の全テスト
- **完了条件**: `pytest -m "not yolo" -q` がgreen
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `test(app): add test infrastructure and health tests`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `ac2f7ae`
- **備考**: 本番DB/storageを触らないことをconftestで保証する。conftestでのDB/storage差し替えを機能させるため、database.py(build_engine関数への分離)・main.py(モジュールレベルinit_storage呼び出し削除、StaticFilesのcheck_dir=False化)をあわせて調整

## T0-SR: Phase 0 セルフレビューと完了処理

- **目的**: Phase 0の整合確認とmain反映
- **前提条件**: T0-1〜T0-6完了
- **実装内容**: 0.5節の共通チェックリストを全消化 → ユーザー承認のもと push・mainへmerge
- **完了条件**: チェックリスト全項目済み、mainにmerge済み
- **検証コマンド**: `cd backend && python -m pytest -q` / `git log --oneline -5`
- **推奨コミットメッセージ**: `chore(backend): complete phase 0 foundation`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [ ] / push済み [ ]
- **push済みcommit hash**: ______
- **備考**: セルフレビュー実施結果は本タスク実施時のセッションログ参照。設計との差分なし

# Phase 1: アップロード+AIパイプライン(ブランチ: `phase/1-upload-pipeline`)

**ゴール**: fixture画像をアップロード→ポーリング→completed→6属性+透過PNGを確認。**正常系だけではPhase完了にしない**。T1-1〜T1-10の異常系サブタスクをすべて消化して完了とする。

## T1-1: image_validation_service(画像実データ検証)

- **目的**: design.md 7.2節・7.4節の検証・正規化を実装する
- **前提条件**: Phase 0完了
- **変更対象ファイル**: `backend/app/services/image_validation_service.py`、`backend/tests/fixtures/`(生成スクリプト可)、`backend/tests/test_upload.py`(検証部)
- **実装内容**:
  - `validate_and_normalize(tmp_path, declared_content_type, original_filename) -> NormalizedImage`
  - 拡張子・申告MIME・**ファイルシグネチャ**(JPEG `FF D8 FF` / PNG `89 50 4E 47 0D 0A 1A 0A`)→ `Image.verify()` → 再オープンして実デコード → 幅/高さ/総ピクセル検証 → `ImageOps.exif_transpose()` → 色空間正規化(CMYK→RGB、PNGはRGBA可)→ 複数フレームは先頭フレームのみ → EXIF除去(再エンコード)
  - `PIL.Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS`、`DecompressionBombWarning` をエラー化
  - 独自例外 `UnsupportedMediaTypeError` / `InvalidImageError`(メッセージに絶対パスを含めない)
  - fixture作成: `tops.jpg` `shoes.jpg` `no_clothing.jpg`(実画像。`ai_prototype/development/input/` や `ai_prototype/Poc/test_images/` から適切な3枚をコピーしてよい)、`fake.jpg`(テキスト)、`broken.png`(切断PNG)、`huge_pixels.png`(Pillowで生成)
- **サブタスク(異常系。各1テスト以上)**:
  - [ ] 不正拡張子(.gif等)→ UnsupportedMediaTypeError
  - [ ] MIMEタイプ不一致・偽装jpg(fake.jpg)→ UnsupportedMediaTypeError
  - [ ] 壊れた画像(broken.png)→ InvalidImageError
  - [ ] MAX_IMAGE_PIXELS超過(huge_pixels.png)→ InvalidImageError
  - [ ] EXIF Orientation付きJPEGが正しく回転される
  - [ ] CMYK JPEGがRGBに変換される
- **影響範囲**: uploadルーター(T1-6)
- **完了条件**: 上記サブタスク含む単体テストがgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k validation`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add image validation and normalization service`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 検証順序は design.md 7.3節の手順5〜10と一致させる

## T1-2: チャンク受信とtmp保存

- **目的**: design.md 7.3節手順2〜4・7.8節(一括読み込み禁止・実受信サイズ基準・容量事前確認)
- **前提条件**: T1-1
- **変更対象ファイル**: `backend/app/services/storage_service.py`(`save_upload_to_tmp()` 追加)、`backend/tests/test_upload.py`
- **実装内容**:
  - `save_upload_to_tmp(file: UploadFile) -> TmpUploadResult{tmp_path, size, sha256}`: `UPLOAD_CHUNK_SIZE_BYTES` ごとの `await file.read(n)` ループでtmpに書き込み。累積サイズ計測+SHA-256逐次計算。**上限超過の時点で書き込みを中断しtmp削除→FileTooLargeError**
  - Content-Length事前確認(ヘッダーがあれば超過即413。ただし**実受信サイズを最終基準**とする)
  - `check_free_space()` をアップロード前に呼ぶ(`MIN_FREE_STORAGE_MB` 未満→InsufficientStorageError)
  - `ENOSPC` を個別捕捉(InsufficientStorageError)。その他のOSError(権限等)はStorageError。種別ごとにログ
- **サブタスク(異常系)**:
  - [ ] 10MB超過(実受信)→ 413 file_too_large、tmpが残らない
  - [ ] Content-Length偽装(小さく申告して大きく送る)→ 実受信サイズで413
  - [ ] 空き容量不足(check_free_spaceをモック)→ 503 insufficient_storage
  - [ ] tmp書き込み失敗(書き込み関数をモックで例外化)→ 500 storage_error、tmpが残らない
- **影響範囲**: uploadルーター
- **完了条件**: サブタスク含むテストgreen。`await file.read()` の一括読み込みがコード中に存在しない
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k "chunk or too_large or storage"` / `grep -rn "file.read()" app/ | grep -v read(` の結果が空
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add chunked upload with size and storage guards`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: MVPでは507は使わず503に統一(design.md 7.8節)

## T1-3: yolo_service 移植

- **目的**: ノートブック `segment_item()` の移植(design.md 8.2節。ロジック変更禁止)
- **前提条件**: Phase 0完了
- **変更対象ファイル**: `backend/app/services/yolo_service.py`、`backend/tests/test_services.py`
- **実装内容**: `SegmentResult` dataclassと `segment_item(model, image_path, conf)`。モデルは引数受け取り(グローバル禁止)。最高信頼度検出を代表クラス、同クラス全マスクをnp.maximum合成、元サイズへresize、RGBA化
- **テスト**(`@pytest.mark.yolo`・実重み使用): tops.jpgでstatus=success・infoにpred_class等が入る / shoes.jpgでnum_instances≥1 / no_clothing.jpgでstatus=no_mask / 存在しないパスでimage_read_error
- **影響範囲**: pipeline_service
- **完了条件**: yoloマーカーテストgreen(重みがある環境で)
- **検証コマンド**: `cd backend && python -m pytest tests/test_services.py -q -m yolo -k segment`
- **想定される正常結果**: all passed(重み無し環境ではskipped)
- **想定される異常結果**: no_clothing.jpgで検出が出てしまう場合はより衣服から遠い画像に差し替える
- **推奨コミットメッセージ**: `feat(pipeline): port YOLO segmentation service from notebook`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 移植元: `ai_prototype/pipe-line/smartcloset_pipeline_functioned.ipynb`(参照は任意)

## T1-4: llm_service 移植(strictスキーマ+リトライ)

- **目的**: design.md 8.3節・付録B.1。ノートブックの不完全な response_format を修正して移植
- **前提条件**: Phase 0完了
- **変更対象ファイル**: `backend/app/services/llm_service.py`、`backend/app/prompts/metadata_prompt.py`、`backend/tests/test_services.py`
- **実装内容**:
  - `METADATA_PROMPT` / `METADATA_JSON_SCHEMA` を付録B.1の**全文どおり**定義
  - `extract_metadata(client, image_path)`: base64送信、response_formatは完全形式(`{"type":"json_schema","json_schema":{"name":"clothing_metadata","strict":True,"schema":...}}`)
  - `parse_json_safely()` をフォールバックとして移植(コードブロック除去+キー補完)
  - リトライ: 接続エラー・5xx・レートリミット・JSON不正で1秒→2秒の指数バックオフ、最大 `OPENAI_MAX_RETRIES` 回。失敗で `LlmServiceError`
- **サブタスク(異常系。OpenAIクライアントはモック)**:
  - [ ] OpenAI API失敗(例外)→ 2回リトライ後に LlmServiceError
  - [ ] OpenAI JSON不正(コードブロック付き応答)→ parse_json_safelyで回復
  - [ ] JSON不正(回復不能)→ リトライ→ LlmServiceError
- **影響範囲**: pipeline_service
- **完了条件**: モックテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_services.py -q -k llm`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(pipeline): port metadata extraction with strict json schema and retry`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: プロンプト文言は付録B.1と一字一句一致させる(正本: `docs/prompt_design.md`)

## T1-5: pipeline_service(排他制御・Session管理・失敗処理)

- **目的**: design.md 8.4〜8.5節。`run_pipeline_for_item(item_id)` 本体
- **前提条件**: T1-3, T1-4
- **変更対象ファイル**: `backend/app/services/pipeline_service.py`、`backend/app/services/storage_service.py`(`save_pipeline_outputs()` 追加)、`backend/tests/test_services.py`
- **実装内容**:
  - モジュールレベル `_ai_semaphore = threading.BoundedSemaphore(settings.AI_MAX_CONCURRENCY)`。`with` で取得・解放(例外時も解放保証)。待機時間ログ
  - 8.4節の手順1〜10: 新規Session(`create_session()`)→レコードロード(processing以外は警告終了)→長辺1280超なら推論用一時コピー→segment→save_pipeline_outputs(masks/transparent/annotated、`{item_id}_{kind}.png`)→extract_metadata→completed更新
  - `mark_item_failed(db, item, reason)`: failed更新+`delete_generated_files(item_id)`(**原画像は残す**)+ERRORログ(スタックトレースはログのみ)
  - finally: 一時コピー削除→Session close→ロック解放
  - 各段階の所要時間をINFOログ
- **サブタスク(異常系)**:
  - [ ] no_mask画像 → failed / failure_reason=no_mask、**自動リトライされない**(YOLOが1回しか呼ばれない)
  - [ ] LLM失敗 → failed / llm_error、透過・マスク・annotatedが削除され原画像が残る
  - [ ] 予期しない例外(モックで注入)→ failed / internal_error
  - [ ] 排他制御: 2タスク同時起動で実行が直列化される(実行順ログまたはロック取得時刻で検証)
  - [ ] Sessionがタスクごとに生成・closeされる(モック/spyで検証)
- **影響範囲**: uploadルーター、stale復旧
- **完了条件**: サブタスク含むテストgreen(YOLOはモック、実推論はT1-10で確認)
- **検証コマンド**: `cd backend && python -m pytest tests/test_services.py -q -k pipeline`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(pipeline): add pipeline orchestration with concurrency lock`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 引数はitem_idのみ。Session/UploadFile/モデルオブジェクトを渡さない(design.md 2.4節)

## T1-6: upload ルーター(17段階+補償処理)

- **目的**: design.md 7.3節の処理順序と7.5節の補償処理を実装する
- **前提条件**: T1-1, T1-2, T1-5
- **変更対象ファイル**: `backend/app/routers/upload.py`、`backend/app/schemas/item.py`(UploadAcceptedResponse)、`backend/tests/test_upload.py`
- **実装内容**:
  - `POST /api/upload`: 手順1〜17を**この順序で**実装。202は手順15完了後のみ
  - 原画像保存名は `{item_id}_original.{jpg|png}`(元ファイル名は `original_filename` 列にのみ記録)
  - 補償処理: DB仮登録失敗→tmp削除のみ / 正式保存失敗→レコード削除+ファイル削除 / パス反映失敗→レコード削除+原画像削除 / add_task失敗→レコード削除+原画像削除
  - tmpは **finallyで必ず削除**
  - BackgroundTasksディスパッチは1箇所に隔離(`background_tasks.add_task(run_pipeline_for_item, item_id)`。Celery移行点コメントを付す)
- **サブタスク(異常系。依存関数をモックで失敗させる)**:
  - [ ] DB仮登録失敗 → 503 database_error、tmp・originalsに何も残らない
  - [ ] 正式保存失敗 → 500 storage_error、DBレコードが存在しない
  - [ ] パス反映コミット失敗 → 503、レコード・原画像が残らない
  - [ ] 正常系でも異常系でもtmpが残らない(テスト後に `storage/tmp` が空)
  - [ ] Idempotency-Keyヘッダー欠落 → 422 validation_error
- **影響範囲**: フロントエンド、status API
- **完了条件**: 正常系(202→BackgroundTasks同期実行→completed)+サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add validated image upload flow` / `fix(storage): clean files after persistence failure`(補償は分けてもよい)
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 202を返す条件はdesign.md 6.2節の定義に厳密に従う

## T1-7: Idempotency-Key(二重登録防止)

- **目的**: design.md 7.7節。通信切断後の再送で二重登録しない
- **前提条件**: T1-6
- **変更対象ファイル**: `backend/app/routers/upload.py`、`backend/tests/test_upload.py`
- **実装内容**: 既存キー照合(tmp受信・SHA-256確定後に一致判定)。一致→既存item_id+status応答(processing:202 / completed:200 / failed:200+failure_reason)。不一致→409 idempotency_key_conflict。UNIQUE制約違反(同時競合)→既存レコード応答へフォールバック
- **サブタスク**:
  - [ ] 同一キー+同一画像再送(processing)→ 202・レコード数が増えない
  - [ ] 同一キー+同一画像再送(completed)→ 200・status=completed
  - [ ] 同一キー+同一画像再送(failed)→ 200・failure_reason付き
  - [ ] 同一キー+異なる画像 → 409 idempotency_key_conflict
- **影響範囲**: フロントエンドの再送処理
- **完了条件**: サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k idempotency`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add idempotency key based duplicate prevention`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 画像ハッシュによる内容ベース重複判定は将来拡張(実装しない)

## T1-8: status API+stale processing復旧

- **目的**: design.md 6.3節・8.6節。ポーリングAPIとBackgroundTasks消失の補償
- **前提条件**: T1-5, T1-6
- **変更対象ファイル**: `backend/app/routers/items.py`(statusのみ)、`backend/app/services/pipeline_service.py`(`recover_stale_processing()`)、`backend/app/main.py`(lifespanに接続)、`backend/tests/test_upload.py`
- **実装内容**:
  - `GET /api/items/{id}/status`: 404対応+**lazy stale検出**(processingかつupdated_atがPROCESSING_STALE_MINUTES超過→その場でfailed/processing_interruptedに更新+生成物削除)
  - `recover_stale_processing(db)`: 起動時に閾値超過のprocessingを一括failed化(**failure_reason=processing_interrupted**、生成物削除、原画像保持、item_id+経過時間をWARNINGログ)。lifespanから呼ぶ
- **サブタスク**:
  - [ ] BackgroundTasks中断シミュレーション: processingレコードをupdated_at=古い時刻で直接作成→起動時復旧でfailed/processing_interruptedになる
  - [ ] lazy検出: 同様のレコードにstatus APIでアクセス→failed/processing_interruptedが返る
  - [ ] 閾値未満のprocessingは変更されない
  - [ ] processing_interruptedとinternal_errorが区別される(internal_errorはコード内例外時のみ)
- **影響範囲**: フロントエンドのポーリング・エラーメッセージ
- **完了条件**: サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k stale`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(pipeline): recover interrupted processing records`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ポーリングのUIタイムアウトはサーバーstatusを変更しない(design.md 12.5節)

## T1-9: 画像配信(公開範囲の限定)

- **目的**: design.md 10.3節。公開すべきものだけを公開する
- **前提条件**: T0-5(マウント自体は実装済み)、T1-6
- **変更対象ファイル**: `backend/tests/test_upload.py`(または `test_security.py` 新設)
- **実装内容**: マウントが originals/transparent の2つのみであることの確認テスト。ItemResponseの `*_image_url` が `/images/...` 形式で返ること(`to_public_url` 経由)
- **サブタスク(機密非漏洩)**:
  - [ ] `/images/tmp/...` `/images/masks/...` `/images/annotated/...` が404
  - [ ] `/images/../data/smartcloset.db` 等のトラバーサルが404
  - [ ] エラーレスポンスに絶対パス・スタックトレースが含まれない(アップロード異常系の応答本文を検査)
- **影響範囲**: セキュリティ
- **完了条件**: サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/ -q -k "public or security"`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `test(security): verify static file exposure is limited`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: design.md 13.4節(機密情報の取り扱い)

## T1-10: 統合テスト(実YOLOでのE2E)

- **目的**: アップロード→AI処理→completed→6属性+透過PNGの全経路を実重みで確認
- **前提条件**: T1-1〜T1-9
- **変更対象ファイル**: `backend/tests/test_upload.py`(`@pytest.mark.yolo` の統合テスト)
- **実装内容**: LLMのみモックし(固定の正常JSON)、tops.jpgをTestClientでアップロード→statusがcompleted→GET詳細で6属性・URL・透過PNGファイルの実在を確認
- **完了条件**: 統合テストgreen。あわせて手動確認: uvicorn起動して `curl -F "file=@tests/fixtures/tops.jpg" -H "Idempotency-Key: $(uuidgen)" localhost:8000/api/upload` → status APIポーリング → completed
- **検証コマンド**: `cd backend && python -m pytest -q -m yolo` および上記curl
- **想定される正常結果**: completed、`storage/transparent/{item_id}_transparent.png` が生成される
- **想定される異常結果**: OPENAI_API_KEY設定済み環境なら実LLMでの動作確認も可(任意)
- **推奨コミットメッセージ**: `test(upload): add end-to-end pipeline integration test`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T1-SR: Phase 1 セルフレビューと完了処理

- **目的**: Phase 1の整合確認とmain反映
- **前提条件**: T1-1〜T1-10完了(**異常系サブタスクのチェックがすべて埋まっていること**)
- **実装内容**: 0.5節の共通チェックリストを全消化 → ユーザー承認のもとpush・mainへmerge
- **完了条件**: チェックリスト全項目済み
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q && python -m pytest -q -m yolo`
- **推奨コミットメッセージ**: `chore(backend): complete phase 1 upload pipeline`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **push済みcommit hash**: ______
- **備考**: ______

# Phase 2: items CRUD(ブランチ: `phase/2-items-crud`)

**ゴール**: 一覧・詳細・手動補正・削除がAPIで完結する。

## T2-1: GET /api/items(一覧・フィルタ・ページング)

- **目的**: design.md 6.4〜6.5節
- **前提条件**: Phase 1完了
- **変更対象ファイル**: `backend/app/routers/items.py`、`backend/app/schemas/item.py`(ItemResponse/ItemListResponse)、`backend/tests/test_items.py`
- **実装内容**: category/color(primary・secondaryの部分一致)/pattern/material/status フィルタ、sort(created_at_desc/asc)、page/page_size(1〜100)、total件数。ItemResponseは内部パスでなくURLを返す
- **完了条件**: フィルタ組み合わせ・ページング・空結果のテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_items.py -q -k list`
- **想定される正常結果**: all passed
- **想定される異常結果**: page_size=101 → 422
- **推奨コミットメッセージ**: `feat(items): add item list with filters and pagination`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: user_id=1固定(シングルユーザー)

## T2-2: GET /api/items/{id}(詳細)

- **目的**: design.md 6.5節
- **前提条件**: T2-1
- **変更対象ファイル**: `backend/app/routers/items.py`、`backend/tests/test_items.py`
- **実装内容**: ItemResponse返却。存在しないIDは404 item_not_found
- **完了条件**: 正常・404テストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_items.py -q -k detail`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(items): add item detail endpoint`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T2-3: PATCH /api/items/{id}(手動補正)

- **目的**: design.md 6.6節。登録成功率64.5%を運用でカバーする中核機能
- **前提条件**: T2-2
- **変更対象ファイル**: `backend/app/routers/items.py`、`backend/app/schemas/item.py`(ItemUpdateRequest)、`backend/tests/test_items.py`
- **実装内容**: 部分更新(指定フィールドのみ)。category/pattern/materialは付録A enumで検証。更新時 `is_user_corrected=true`・`updated_at` 更新。completed以外は409(processing→item_is_processing / failed→item_not_editable)
- **サブタスク(異常系)**:
  - [ ] enum違反(category="コート"等)→ 422 validation_error
  - [ ] processing中のPATCH → 409 item_is_processing
  - [ ] failedのPATCH → 409 item_not_editable
  - [ ] color_secondary=null で副色が消せる
- **完了条件**: サブタスク含むテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_items.py -q -k patch`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(items): add metadata correction endpoint`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: enumはdesign.md付録Aが正本

## T2-4: DELETE /api/items/{id}(物理削除)

- **目的**: design.md 6.7節・7.6節
- **前提条件**: T2-2
- **変更対象ファイル**: `backend/app/routers/items.py`、`backend/tests/test_items.py`
- **実装内容**: processing→409 item_is_processing。completed/failed→`delete_item_files(item_id)`(原画像含む全種・冪等)→レコード削除→204。ファイル一部削除失敗でもレコード削除は続行しWARNINGログ
- **サブタスク(異常系)**:
  - [ ] processing中のDELETE → 409、レコード・ファイルが残る
  - [ ] completedのDELETE → 204、originals/transparent/masks/annotatedの実ファイルが消える
  - [ ] **failedアイテムのDELETE → 204、残っていた原画像も物理削除される**
  - [ ] 既にファイルが無い状態でのDELETE → 204(冪等)
- **完了条件**: サブタスク含むテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_items.py -q -k delete`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(items): add physical deletion endpoint`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 削除はstorage_serviceの共通関数のみ使用(重複実装禁止)

## T2-SR: Phase 2 セルフレビューと完了処理

- **前提条件**: T2-1〜T2-4完了
- **実装内容**: 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **推奨コミットメッセージ**: `chore(backend): complete phase 2 items crud`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **push済みcommit hash**: ______
- **備考**: ______

---

# Phase 3: コーディネート提案(ブランチ: `phase/3-suggest`)

**ゴール**: 天気あり/なし両系でコーデ提案が返り、ログが記録される。

## T3-1: weather_service と GET /api/weather

- **目的**: design.md 11.3節・6.9節
- **前提条件**: Phase 2完了
- **変更対象ファイル**: `backend/app/services/weather_service.py`、`backend/app/routers/weather.py`、`backend/app/schemas/weather.py`、`backend/tests/test_suggest.py`
- **実装内容**: `get_current_weather(city) -> WeatherInfo | None`(httpx、timeout 5秒、リトライなし、失敗はWARNINGログ+None)。`GET /api/weather`はNone時503 service_unavailable
- **サブタスク(異常系。httpxをモック)**:
  - [ ] タイムアウト → None
  - [ ] 非200応答 → None
  - [ ] APIキー未設定 → None(例外を出さない)
- **完了条件**: モックテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_suggest.py -q -k weather`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(weather): add openweathermap client with fallback`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 実APIでの動作確認は手動で1回行う(`curl "localhost:8000/api/weather"`)

## T3-2: suggest_prompt と suggest_service

- **目的**: design.md 11.1〜11.2節・付録B.2
- **前提条件**: T3-1
- **変更対象ファイル**: `backend/app/prompts/suggest_prompt.py`、`backend/app/services/suggest_service.py`、`backend/app/schemas/suggest.py`、`backend/tests/test_suggest.py`
- **実装内容**:
  - `SUGGEST_SYSTEM_PROMPT` / `build_suggest_user_prompt(weather, request_text, closet_json)` / `SUGGEST_JSON_SCHEMA` を付録B.2の**全文どおり**定義(天気ブロックの成功/失敗2形式含む)
  - `create_suggestion(db, request_text, weather)`: completedのみでクローゼットJSON構築(**画像は送らない**)→strictスキーマでLLM呼び出し(リトライはllm_serviceと同方針)→**item_idsをDB照合し無効IDを除外(WARNINGログ)**→coordinate_logsに記録
- **完了条件**: モックLLMで正常系green
- **検証コマンド**: `cd backend && python -m pytest tests/test_suggest.py -q -k service`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(suggest): add coordinate suggestion service with llm`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ルール(dress排他・同カテゴリ1点)はプロンプトで指示し、コード側では強制しない(LLM出力の検証はID実在のみ)

## T3-3: POST /api/suggest(異常系込み)

- **目的**: design.md 6.8節・11.4節
- **前提条件**: T3-2
- **変更対象ファイル**: `backend/app/routers/suggest.py`、`backend/tests/test_suggest.py`
- **実装内容**: SuggestRequest検証(request_text 1〜500文字)→completed 0件なら**LLMを呼ばず**400 no_completed_items→天気(use_weather/city)→create_suggestion→SuggestResponse(items/weather/weather_available/log_id)
- **サブタスク(異常系)**:
  - [ ] completed 0件 → 400 no_completed_items、LLMモックが呼ばれていない
  - [ ] processing/failedのアイテムがクローゼットJSONに含まれない
  - [ ] 天気失敗 → 200、weather_available=false、weather_json=NULLでログ記録
  - [ ] LLMが無効item_idを混ぜる → 有効IDのみ返る
  - [ ] 全item_id無効 → items:[] で suggestion_text が返る(200)
  - [ ] LLM失敗(リトライ後)→ 503 service_unavailable、coordinate_logsに記録されない
  - [ ] request_text空白のみ → 422
- **完了条件**: サブタスク含むテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_suggest.py -q`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(suggest): add suggestion endpoint with fallbacks`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 実LLMでの動作確認を手動で1回行う(衣服を数点登録した状態で `curl -X POST localhost:8000/api/suggest -H 'Content-Type: application/json' -d '{"request_text":"今日は大事な会議。きちんと見せたい"}'`)

## T3-SR: Phase 3 セルフレビューと完了処理

- **前提条件**: T3-1〜T3-3完了
- **実装内容**: 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **推奨コミットメッセージ**: `chore(backend): complete phase 3 suggestion`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **push済みcommit hash**: ______
- **備考**: ______

# Phase 4: フロントエンド(ブランチ: `phase/4-frontend`)

**ゴール**: ブラウザで「登録→閲覧→編集→提案」のE2Eフローが完結する。

## T4-1: Next.js雛形とAPIクライアント

- **目的**: design.md 12.2節の共通モジュール
- **前提条件**: Phase 3完了(APIが動作していること)
- **変更対象ファイル**: `frontend/`(create-next-app生成)、`frontend/src/lib/api.ts`、`frontend/src/lib/types.ts`
- **実装内容**: `npx create-next-app@latest frontend`(TypeScript / App Router / Tailwind / src ディレクトリ)。`types.ts` に design.md 6章のスキーマと1:1の型(ItemResponse / ItemListResponse / ItemStatusResponse / SuggestResponse / WeatherInfo / ErrorResponse)。`api.ts` にfetchラッパー(ベースURL `NEXT_PUBLIC_API_BASE_URL`、エラー時はErrorResponseをパースして型付き例外)
- **完了条件**: `npm run build` と `npx tsc --noEmit` が通る
- **検証コマンド**: `cd frontend && npm run build && npx tsc --noEmit`
- **想定される正常結果**: ビルド成功・型エラーなし
- **推奨コミットメッセージ**: `chore(frontend): scaffold next.js app with typed api client`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 開発時は `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`(`.env.local`、Git管理外)

## T4-2: クローゼット一覧画面(/)

- **目的**: design.md 12.1〜12.2節
- **前提条件**: T4-1
- **変更対象ファイル**: `frontend/src/app/page.tsx`、`components/ItemCard.tsx`、`components/ItemGrid.tsx`、`components/FilterBar.tsx`
- **実装内容**: GET /api/items で透過PNGのグリッド表示。FilterBar(category/color/pattern/materialフィルタ)。ページング。status≠completedのバッジ表示(processing: 「解析中」/ failed: 12.6節の文言)。カードクリックで `/items/[id]` へ
- **完了条件**: 登録済みデータが表示され、フィルタ・ページングが機能する(手動確認)
- **検証コマンド**: `cd frontend && npm run dev` → ブラウザで `http://localhost:3000/`(backend起動済み)
- **想定される正常結果**: 透過画像グリッドが表示される
- **想定される異常結果**: 0件時は「衣服を登録しましょう」の空状態表示
- **推奨コミットメッセージ**: `feat(frontend): add closet grid with filters`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T4-3: アップロード画面(/upload)— 状態機械

- **目的**: design.md 12.3〜12.7節。**本Phaseで最重要のタスク**
- **前提条件**: T4-1
- **変更対象ファイル**: `frontend/src/app/upload/page.tsx`、`components/UploadDropzone.tsx`、`components/ImagePreview.tsx`、`components/ProcessingStatus.tsx`
- **実装内容**:
  - 9状態の状態機械(idle/validating/uploading/accepted/processing/completed/upload_failed/processing_failed/polling_timeout)を12.3節の遷移どおり実装
  - クライアント事前チェック(JPEG/PNG、10MB)。任意最適化: 長辺1280超のCanvas縮小(12.7節)
  - **Idempotency-Key**: 送信前に `crypto.randomUUID()`。再試行(upload_failed)は同一キー、新画像選択で新キー
  - **二重送信防止**: uploading中はボタン無効化+送信中フラグ
  - **202受信時**: `localStorage["smartcloset_pending_upload"] = {item_id, idempotency_key, saved_at}`。ページ再訪問時に残っていればポーリング再開(completed/failed確認後に削除)
  - ポーリング: 2秒間隔・最大60秒。60秒で `polling_timeout`(**サーバーへの失敗通知はしない**。「処理は継続中の可能性があります」+クローゼット導線)
  - failure_reason別メッセージ(12.6節の表のとおり)
  - completed時: 抽出結果プレビュー+「クローゼットを見る」「続けて登録」
- **サブタスク(異常系・手動確認込み)**:
  - [ ] 二重送信防止: 送信ボタン連打で1リクエストのみ
  - [ ] 通信切断(202前): DevToolsオフライン化→再試行→同一キーで再送され二重登録されない
  - [ ] 通信切断(202後): 202直後にリロード→ポーリングが再開される
  - [ ] polling timeout: backendのパイプラインを一時的に遅延(またはPROCESSING_STALE_MINUTES内のprocessing放置)→60秒でタイムアウトUI
  - [ ] failed(no_mask): 衣服なし画像で「衣服を検出できませんでした」+新規アップロード導線(同一画像の自動再送をしない)
- **完了条件**: 正常系+サブタスクの手動確認。tsc通過
- **検証コマンド**: `cd frontend && npx tsc --noEmit` + ブラウザ手動確認
- **想定される正常結果**: 登録完了までUIがブロックせず遷移する
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(frontend): add upload flow with state machine and idempotent retry`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 状態名はdesign.md 12.3節と一致させる(コード上の定数名も同一)

## T4-4: アイテム詳細・編集画面(/items/[id])

- **目的**: design.md 12.1節。手動補正のUI
- **前提条件**: T4-2
- **変更対象ファイル**: `frontend/src/app/items/[id]/page.tsx`、`components/MetadataEditForm.tsx`
- **実装内容**: 原画像/透過画像の切替表示。6属性の編集フォーム(category/pattern/materialは付録Aのenumをセレクトボックスで)→PATCH。削除ボタン(確認ダイアログ→DELETE→一覧へ)。409(processing)時のエラートースト
- **完了条件**: 編集→一覧反映、削除→一覧から消える(手動確認)、tsc通過
- **検証コマンド**: `cd frontend && npx tsc --noEmit` + ブラウザ手動確認
- **想定される正常結果**: PATCH後に is_user_corrected が立つ(API応答で確認)
- **推奨コミットメッセージ**: `feat(frontend): add item detail with metadata correction`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: enumセレクトの選択肢はdesign.md付録Aと同期

## T4-5: コーデ提案画面(/suggest)

- **目的**: design.md 12.1節
- **前提条件**: T4-2
- **変更対象ファイル**: `frontend/src/app/suggest/page.tsx`、`components/SuggestForm.tsx`、`components/WeatherBadge.tsx`、`components/SuggestionResult.tsx`
- **実装内容**: WeatherBadge(GET /api/weather。503時「天気情報を取得できませんでした」で提案は継続可能)。要望入力(空は送信不可)→POST /api/suggest(送信中無効化)→suggestion_text/styling_reason+推奨ItemCardハイライト。400 no_completed_items時は登録導線を表示
- **サブタスク**:
  - [ ] weather_available=false でも提案が表示される
  - [ ] items:[](全ID無効)でもテキストだけ表示される
  - [ ] 503時にエラートースト+再試行可能
- **完了条件**: 手動確認+tsc通過
- **検証コマンド**: `cd frontend && npx tsc --noEmit` + ブラウザ手動確認
- **想定される正常結果**: 提案文と推奨アイテムがハイライト表示される
- **推奨コミットメッセージ**: `feat(frontend): add coordinate suggestion page`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T4-SR: Phase 4 セルフレビューと完了処理

- **前提条件**: T4-1〜T4-5完了
- **実装内容**: 0.5節の共通チェックリスト全消化(フロントは `npx tsc --noEmit` / `npm run build` を全テストに追加)→ ブラウザで登録→閲覧→編集→提案のE2E → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q` / `cd frontend && npm run build`
- **推奨コミットメッセージ**: `chore(frontend): complete phase 4 frontend`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **push済みcommit hash**: ______
- **備考**: ______

---

# Phase 5: 仕上げ(ブランチ: `phase/5-hardening`)

**ゴール**: 手動E2Eチェックリスト(design.md 14.3節 1〜7)全消化。

## T5-1: エラーハンドリング最終化と機密非漏洩監査

- **目的**: design.md 13章の完全準拠を確認・修正
- **前提条件**: Phase 4完了
- **変更対象ファイル**: `backend/app/main.py`(例外ハンドラ)、各router、`backend/tests/test_security.py`
- **実装内容**: 13.2節の全error_code・HTTPコード・retryable・文言と実装の突き合わせ。未処理例外→500 internal_error(スタックトレースはログのみ)。**監査テスト**: 全異常系レスポンス本文に絶対パス(`/users/`, `/app/`)・`Traceback`・APIキー文字列が含まれないことをアサート。ログ出力にAPIキーが含まれないこと(キー文字列でgrep)
- **完了条件**: 監査テストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_security.py -q` / `grep -rn "$OPENAI_API_KEY" logs等`(該当なし)
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `fix(app): finalize error responses and prevent information leaks`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: design.md 13.4節・9.6節(情報の役割分担)

## T5-2: ロギング整備

- **目的**: design.md 13.5節の必須ログ項目を揃える
- **前提条件**: T5-1
- **変更対象ファイル**: `backend/app/main.py`(logging設定)、各service
- **実装内容**: フォーマット統一(stdout)。必須項目(所要時間・ロック待機・リトライ・stale復旧・削除失敗・DBロック)の出力確認。1件アップロードして各段階のINFOログが出ることを目視確認
- **完了条件**: 手動アップロード1件でパイプライン各段階のログが確認できる
- **検証コマンド**: uvicorn起動→curlアップロード→コンソールログ確認
- **想定される正常結果**: resize/yolo/save/llm/db 各段階の所要時間ログ
- **推奨コミットメッセージ**: `feat(app): add structured operational logging`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T5-3: README(起動手順)

- **目的**: 開発環境の起動手順を文書化
- **前提条件**: T5-2
- **変更対象ファイル**: `README.md`
- **実装内容**: プロジェクト概要、必要なもの(Python/Node/モデル重み/APIキー)、backend起動手順、frontend起動手順、テスト実行方法、docs/design.md・todo.mdへの参照
- **完了条件**: READMEの手順どおりにクリーンな環境で起動できる
- **検証コマンド**: README記載のコマンドを順に実行
- **想定される正常結果**: 起動成功
- **推奨コミットメッセージ**: `docs(readme): add setup and run instructions`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T5-4: 手動E2Eチェックリスト消化

- **目的**: design.md 14.3節の1〜7を実施
- **前提条件**: T5-1〜T5-3
- **実装内容**:
  - [ ] 1. アップロード→処理中→完了→クローゼット表示
  - [ ] 2. 衣服なし写真→no_maskメッセージ
  - [ ] 3. category修正→反映・is_user_corrected
  - [ ] 4. 削除→一覧・storageから消える
  - [ ] 5. コーデ提案→提案文+ハイライト
  - [ ] 6. 通信切断→再送→二重登録なし
  - [ ] 7. アップロード直後にbackend再起動→failed(処理中断)表示(PROCESSING_STALE_MINUTESを一時的に短縮して確認してよい。確認後に戻す)
- **完了条件**: 7項目すべてチェック。発見した不具合は修正して再確認
- **検証コマンド**: (手動)
- **推奨コミットメッセージ**: (修正が出た場合)`fix(...): ...`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T5-SR: Phase 5 セルフレビューと完了処理

- **前提条件**: T5-1〜T5-4完了
- **実装内容**: 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -q` / `cd frontend && npm run build`
- **推奨コミットメッセージ**: `chore(app): complete phase 5 hardening`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **push済みcommit hash**: ______
- **備考**: ______

---

# Phase 6: デプロイ(ブランチ: `phase/6-deploy`)

**ゴール**: Oracle Cloud VM上の公開URLで、スマホからE2Eフロー成功(design.md 14.3節-8)。

## T6-1: backend Dockerfile

- **目的**: design.md 15.2節
- **前提条件**: Phase 5完了
- **変更対象ファイル**: `backend/Dockerfile`、`backend/.dockerignore`
- **実装内容**: `python:3.12-slim` ベース、**torch CPU版を先にインストール**(`--index-url https://download.pytorch.org/whl/cpu`)、requirements、`uvicorn --host 0.0.0.0 --port 8000 --workers 1`。.dockerignore(.venv/storage/data/tests)
- **完了条件**: ローカルでビルド・起動し、モデルをマウントしてhealthがok
- **検証コマンド**: `docker build -t smartcloset-backend backend/ && docker run --rm -v $(pwd)/models:/models:ro -v $(pwd)/backend/.env:/app/.env:ro -e MODEL_PATH=/models/fashionpedia_9class_with_data_augmentation.pt -p 8000:8000 smartcloset-backend` → `curl localhost:8000/api/health`
- **想定される正常結果**: `model_loaded:true`
- **想定される異常結果**: モデル未マウント時に起動失敗する(正しい挙動)
- **推奨コミットメッセージ**: `feat(deploy): add backend dockerfile with cpu torch`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ARM64ビルドはVM上で行う(ローカルがx86の場合はローカル検証はx86で可)

## T6-2: frontend Dockerfile

- **目的**: design.md 15.2節
- **前提条件**: T6-1
- **変更対象ファイル**: `frontend/Dockerfile`、`frontend/next.config.js`(`output: "standalone"`)、`.dockerignore`
- **実装内容**: multi-stage(node:20-slim)、standaloneビルド、`node server.js`。`NEXT_PUBLIC_API_BASE_URL` は空(同一オリジン)
- **完了条件**: ビルド・起動しトップページが表示される
- **検証コマンド**: `docker build -t smartcloset-frontend frontend/ && docker run --rm -p 3000:3000 smartcloset-frontend` → ブラウザ確認
- **想定される正常結果**: 画面表示(API未接続でも空状態表示)
- **推奨コミットメッセージ**: `feat(deploy): add frontend standalone dockerfile`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: ______

## T6-3: docker-compose と Caddy

- **目的**: design.md 15.3〜15.5節
- **前提条件**: T6-1, T6-2
- **変更対象ファイル**: `deploy/docker-compose.yml`、`deploy/Caddyfile`、`deploy/.env.example`
- **実装内容**: 15.5節のcompose(**backend/frontendはportsを公開しない**、restart: unless-stopped、モデルro マウント)。15.3節のCaddyfile(**basic_auth全パス**、request_body 12MB、/api・/imagesをbackendへ、他をfrontendへ)。`.env.example` に CADDY_DOMAIN/CADDY_BASIC_AUTH_USER/CADDY_BASIC_AUTH_HASH のキー名のみ
- **サブタスク**:
  - [ ] `docker compose up -d` 後、`caddy` 経由でのみアクセスできる(ホストの8000/3000が閉じている)
  - [ ] Basic認証なしで401、認証ありで表示
  - [ ] 12MB超のアップロードがCaddyで拒否される+FastAPI側413も機能(二重防御)
- **完了条件**: ローカル(またはVM)でcompose一式が起動しE2Eが通る
- **検証コマンド**: `cd deploy && docker compose up -d --build && curl -k -u user:pass https://localhost/api/health`
- **想定される正常結果**: healthがok、401/認証OKの切り替え確認
- **推奨コミットメッセージ**: `feat(deploy): add docker compose with caddy basic auth`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 平文パスワードをGit・composeファイルに書かない(ハッシュのみ.envへ)

## T6-4: Oracle VM セットアップと本番起動

- **目的**: design.md 15.6節の手順を実施
- **前提条件**: T6-3(mainにmerge済みであること)
- **変更対象ファイル**: (VM上の作業。リポジトリ変更は原則なし。手順の差異が出たらdesign.md 15.6節を更新)
- **実装内容**: アカウント作成→A1.Flexインスタンス確保→セキュリティリスト(80/443、SSHは自IP限定)→Docker導入+`systemctl enable docker`→git clone→**モデル重みscp転送**→`backend/.env`・`deploy/.env` 作成→`docker compose up -d --build`→DuckDNS等のDNS設定
- **サブタスク**:
  - [ ] VM再起動(`sudo reboot`)後にサービスが自動復旧する
  - [ ] `GET /api/health` が公開URLで `model_loaded:true`
- **完了条件**: 公開URLでhealth ok
- **検証コマンド**: `curl -u user:pass https://<domain>/api/health`
- **想定される正常結果**: `{"status":"ok",...}`
- **想定される異常結果**: A1確保失敗→OCPU減・時間帯変更でリトライ(design.md 15.6節)
- **推奨コミットメッセージ**: (手順差異があれば)`docs(design): update vm setup steps`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: APIキー・ハッシュはVM上の.envのみに置く

## T6-5: バックアップ・復元スクリプト

- **目的**: design.md 16章
- **前提条件**: T6-4
- **変更対象ファイル**: `scripts/backup.sh`、`scripts/restore.sh`
- **実装内容**: 16.1節の手順(backend停止→sqlite3 .backup→tar(tmp除外)→再開→世代整理BACKUP_RETENTION_COUNT=7)。同一タイムスタンプ命名 `smartcloset_backup_{YYYYMMDD_HHMMSS}.{db,tar.gz}`。restore.sh は16.2節(退避→配置→起動→**DB内画像パスと実ファイルの存在検証**)
- **サブタスク**:
  - [ ] VM上でbackup実行→2ファイル生成・タイムスタンプ一致
  - [ ] restore実行→アプリが復元データで動作・検証スクリプトが欠損ゼロを報告
  - [ ] 8世代目作成で最古が削除される
- **完了条件**: サブタスク全消化
- **検証コマンド**: `bash scripts/backup.sh && ls ~/smartcloset_backups/`
- **想定される正常結果**: `.db` と `.tar.gz` が同一タイムスタンプで生成
- **推奨コミットメッセージ**: `feat(ops): add consistent backup and restore scripts`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 同一VM内のみのバックアップはVM消失に無力(Known Limitation。将来Object Storage退避)

## T6-6: 本番E2E(スマホ)

- **目的**: design.md 14.3節-8
- **前提条件**: T6-4, T6-5
- **実装内容**: スマホブラウザで公開URLにアクセス(Basic認証)し、14.3節の1〜5を実施。カメラ撮影画像のアップロード(EXIF Orientation補正の実機確認を含む)
- **完了条件**: スマホで登録→閲覧→編集→提案が完結
- **検証コマンド**: (手動)
- **推奨コミットメッセージ**: (修正が出た場合)`fix(...): ...`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 縦撮り写真が横倒しにならないこと(EXIF補正の確認ポイント)

## T6-SR: Phase 6 セルフレビューと完了処理

- **前提条件**: T6-1〜T6-6完了
- **実装内容**: **READMEを完成状態に更新**(①ステータス行を「稼働中」へ ②デモ画像を選抜して `docs/images/` にcommitし掲載=README内の `TODO(デモ)` コメント参照 ③動かし方の最終確認 ④ロードマップ全チェック+「今後の展望」をdesign.md 18章から数行追記)→ 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q` / 公開URLでのhealth確認
- **推奨コミットメッセージ**: `chore(deploy): complete phase 6 deployment`
- **チェック**: 実装済み [ ] / テスト済み [ ] / commit済み [ ] / push済み [ ]
- **push済みcommit hash**: ______
- **備考**: ______

---

# 完成条件(全体)

- [ ] Phase 0〜6 の全タスク・全サブタスクのチェックが埋まっている
- [ ] `docs/design.md` と実装に差分がない(あれば0.3の手順で解消済み)
- [ ] 公開URL(Basic認証付きHTTPS)でスマホからE2Eフローが成功する
- [ ] 月額費用がOpenAI API従量分のみである(design.md 15.7節)
- [ ] バックアップ・復元が検証済みである

(以上 / SmartCloset AI 実装TODO ver 1.0)



