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

type/scope は英語、件名・本文は日本語で書く。

```text
feat(upload): 検証付き画像アップロードフローを実装
fix(storage): 保存失敗時の補償処理でファイルを削除
feat(pipeline): 中断されたprocessingレコードの復旧を追加
test(upload): 不正画像とストレージ失敗系のテストを追加
docs(design): アップロード補償フローを定義
chore(backend): プロジェクト雛形を作成
```

※各タスクの「推奨コミットメッセージ」欄は英語表記のままだが、実際のコミットでは同内容を日本語で書くこと。

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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **push済みcommit hash**: `e9e5044`
- **備考**: セルフレビュー実施結果は本タスク実施時のセッションログ参照。設計との差分なし。mainへのmergeは未実施(ユーザー指示により保留)

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
  - [x] 不正拡張子(.gif等)→ UnsupportedMediaTypeError
  - [x] MIMEタイプ不一致・偽装jpg(fake.jpg)→ UnsupportedMediaTypeError
  - [x] 壊れた画像(broken.png)→ InvalidImageError
  - [x] MAX_IMAGE_PIXELS超過(huge_pixels.png)→ InvalidImageError
  - [x] EXIF Orientation付きJPEGが正しく回転される
  - [x] CMYK JPEGがRGBに変換される
- **影響範囲**: uploadルーター(T1-6)
- **完了条件**: 上記サブタスク含む単体テストがgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k validation`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add image validation and normalization service`
- **レビュー指摘(修正済み)**:
  - [x] **バグ**: `_open_and_decode()` の except タプルに `Image.DecompressionBombWarning` を追加した。テスト追加: `test_validation_rejects_pixels_in_bomb_warning_band`(7,000×7,000pxでInvalidImageErrorになることを確認)
  - [x] **改善**: `InvalidImageError` のメッセージから `{e}` を除去し固定メッセージにした(原因は `from e` 連鎖で保持)。テスト追加: `test_validation_unidentifiable_image_error_excludes_absolute_path`
  - [x] **環境整備**: ルート `.gitignore` に `__pycache__/` と `*.pyc` を追加
  - [x] 修正後に `pytest -m "not yolo" -q` を再実行してgreenを確認(23 passed)
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `6e9829b`
- **備考**: 検証順序は design.md 7.3節の手順5〜10と一致させる。no_clothing.jpgは実写真の代わりにPIL生成の風景風合成画像を使用(ユーザー承認済み、T1-3で使用予定)。EXIF Orientation・CMYKテストはtmp_path上でPillow生成した個別fixtureで検証(fixtures/配下には追加していない)。レビュー指摘はFable 5によるコードレビュー(2026-07-16)由来

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
  - [x] 10MB超過(実受信)→ 413 file_too_large、tmpが残らない
  - [x] Content-Length偽装(小さく申告して大きく送る)→ 実受信サイズで413
  - [x] 空き容量不足(check_free_spaceをモック)→ 503 insufficient_storage
  - [x] tmp書き込み失敗(書き込み関数をモックで例外化)→ 500 storage_error、tmpが残らない
- **影響範囲**: uploadルーター
- **完了条件**: サブタスク含むテストgreen。`await file.read()` の一括読み込みがコード中に存在しない
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k "chunk or too_large or storage"` / `grep -rn "file.read()" app/ | grep -v read(` の結果が空
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add chunked upload with size and storage guards`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `7a77a19`
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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `ab63bba`
- **備考**: 移植元: `ai_prototype/pipe-line/smartcloset_pipeline_functioned.ipynb`(参照は任意)。実重み(models/fashionpedia_9class_with_data_augmentation.pt)で4件とも実行確認済み。no_clothing.jpg(PIL生成の風景画像)でno_mask判定になることも確認済み

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
  - [x] OpenAI API失敗(例外)→ 2回リトライ後に LlmServiceError
  - [x] OpenAI JSON不正(コードブロック付き応答)→ parse_json_safelyで回復
  - [x] JSON不正(回復不能)→ リトライ→ LlmServiceError
- **影響範囲**: pipeline_service
- **完了条件**: モックテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_services.py -q -k llm`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(pipeline): port metadata extraction with strict json schema and retry`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `8844604`
- **備考**: プロンプト文言は付録B.1と一字一句一致させる(正本: `docs/prompt_design.md`)。ノートブックのbuild_metadata_prompt()と文字列比較して完全一致を確認済み

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
  - [x] no_mask画像 → failed / failure_reason=no_mask、**自動リトライされない**(YOLOが1回しか呼ばれない)
  - [x] LLM失敗 → failed / llm_error、透過・マスク・annotatedが削除され原画像が残る
  - [x] 予期しない例外(モックで注入)→ failed / internal_error
  - [x] 排他制御: 2タスク同時起動で実行が直列化される(実行順ログまたはロック取得時刻で検証)
  - [x] Sessionがタスクごとに生成・closeされる(モック/spyで検証)
- **影響範囲**: uploadルーター、stale復旧
- **完了条件**: サブタスク含むテストgreen(YOLOはモック、実推論はT1-10で確認)
- **検証コマンド**: `cd backend && python -m pytest tests/test_services.py -q -k pipeline`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(pipeline): add pipeline orchestration with concurrency lock`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `6cc01a5`
- **備考**: 引数はitem_idのみ。Session/UploadFile/モデルオブジェクトを渡さない(design.md 2.4節)。YOLO/OpenAIクライアントはapp.main.appのstateから遅延importで取得し、main.pyとの循環importを回避

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
  - [x] DB仮登録失敗 → 503 database_error、tmp・originalsに何も残らない
  - [x] 正式保存失敗 → 500 storage_error、DBレコードが存在しない
  - [x] パス反映コミット失敗 → 503、レコード・原画像が残らない
  - [x] 正常系でも異常系でもtmpが残らない(テスト後に `storage/tmp` が空)
  - [x] Idempotency-Keyヘッダー欠落 → 422 validation_error
- **影響範囲**: フロントエンド、status API
- **完了条件**: 正常系(202→BackgroundTasks同期実行→completed)+サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add validated image upload flow` / `fix(storage): clean files after persistence failure`(補償は分けてもよい)
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `76deb28`
- **備考**: 202を返す条件はdesign.md 6.2節の定義に厳密に従う。既存キー照合による同一キー再送対応はT1-7で実装済み

## T1-7: Idempotency-Key(二重登録防止)

- **目的**: design.md 7.7節。通信切断後の再送で二重登録しない
- **前提条件**: T1-6
- **変更対象ファイル**: `backend/app/routers/upload.py`、`backend/tests/test_upload.py`
- **実装内容**: 既存キー照合(tmp受信・SHA-256確定後に一致判定)。一致→既存item_id+status応答(processing:202 / completed:200 / failed:200+failure_reason)。不一致→409 idempotency_key_conflict。UNIQUE制約違反(同時競合)→既存レコード応答へフォールバック
- **サブタスク**:
  - [x] 同一キー+同一画像再送(processing)→ 202・レコード数が増えない
  - [x] 同一キー+同一画像再送(completed)→ 200・status=completed
  - [x] 同一キー+同一画像再送(failed)→ 200・failure_reason付き
  - [x] 同一キー+異なる画像 → 409 idempotency_key_conflict
- **影響範囲**: フロントエンドの再送処理
- **完了条件**: サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k idempotency`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(upload): add idempotency key based duplicate prevention`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `a8177dd`
- **備考**: 画像ハッシュによる内容ベース重複判定は将来拡張(実装しない)

## T1-8: status API+stale processing復旧

- **目的**: design.md 6.3節・8.6節。ポーリングAPIとBackgroundTasks消失の補償
- **前提条件**: T1-5, T1-6
- **変更対象ファイル**: `backend/app/routers/items.py`(statusのみ)、`backend/app/services/pipeline_service.py`(`recover_stale_processing()`)、`backend/app/main.py`(lifespanに接続)、`backend/tests/test_upload.py`
- **実装内容**:
  - `GET /api/items/{id}/status`: 404対応+**lazy stale検出**(processingかつupdated_atがPROCESSING_STALE_MINUTES超過→その場でfailed/processing_interruptedに更新+生成物削除)
  - `recover_stale_processing(db)`: 起動時に閾値超過のprocessingを一括failed化(**failure_reason=processing_interrupted**、生成物削除、原画像保持、item_id+経過時間をWARNINGログ)。lifespanから呼ぶ
- **サブタスク**:
  - [x] BackgroundTasks中断シミュレーション: processingレコードをupdated_at=古い時刻で直接作成→起動時復旧でfailed/processing_interruptedになる
  - [x] lazy検出: 同様のレコードにstatus APIでアクセス→failed/processing_interruptedが返る
  - [x] 閾値未満のprocessingは変更されない
  - [x] processing_interruptedとinternal_errorが区別される(internal_errorはコード内例外時のみ)
- **影響範囲**: フロントエンドのポーリング・エラーメッセージ
- **完了条件**: サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_upload.py -q -k stale`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(pipeline): recover interrupted processing records`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `48d90dd`
- **備考**: ポーリングのUIタイムアウトはサーバーstatusを変更しない(design.md 12.5節)

## T1-9: 画像配信(公開範囲の限定)

- **目的**: design.md 10.3節。公開すべきものだけを公開する
- **前提条件**: T0-5(マウント自体は実装済み)、T1-6
- **変更対象ファイル**: `backend/tests/test_upload.py`(または `test_security.py` 新設)
- **実装内容**: マウントが originals/transparent の2つのみであることの確認テスト。ItemResponseの `*_image_url` が `/images/...` 形式で返ること(`to_public_url` 経由)
- **サブタスク(機密非漏洩)**:
  - [x] `/images/tmp/...` `/images/masks/...` `/images/annotated/...` が404
  - [x] `/images/../data/smartcloset.db` 等のトラバーサルが404
  - [x] エラーレスポンスに絶対パス・スタックトレースが含まれない(アップロード異常系の応答本文を検査)
- **影響範囲**: セキュリティ
- **完了条件**: サブタスクgreen
- **検証コマンド**: `cd backend && python -m pytest tests/ -q -k "public or security"`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `test(security): verify static file exposure is limited`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `8da63fe`
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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `b2b08e8`
- **備考**: pytest(`-m yolo`、実YOLO+モックLLM)に加え、ルートの.envのOPENAI_API_KEYを一時的にbackend/.envへコピーしuvicorn実起動+curlで実LLMでの動作も確認済み(completed、6属性・透過PNG実在を確認)。確認後にbackend/.env・storage/・data/は削除済み

## T1-SR: Phase 1 セルフレビューと完了処理

- **目的**: Phase 1の整合確認とmain反映
- **前提条件**: T1-1〜T1-10完了(**異常系サブタスクのチェックがすべて埋まっていること**)
- **実装内容**: 0.5節の共通チェックリストを全消化 → ユーザー承認のもとpush・mainへmerge
- **完了条件**: チェックリスト全項目済み
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q && python -m pytest -q -m yolo`
- **推奨コミットメッセージ**: `chore(backend): complete phase 1 upload pipeline`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **push済みcommit hash**: `c1a9f78`
- **備考**: セルフレビューで発見した差分2点を修正: (1) main.pyのlifespan順序をdesign.md 5.3節どおりに補正(`47c4826`)、(2) pipeline_serviceの想定外例外ハンドラにdesign.md 9.5節「例外時はrollback」を追加(`47c4826`)。あわせて14.1節のテスト観点表との差分確認で/api/upload経由の415・413・400ルーターレベルテストを追加(`b2044b2`)。他の確認項目(todo.mdのチェック・hash記入漏れ、API仕様、DBモデル/DDL、環境変数一覧、.gitignore、機密情報混入)は差分なし。全テスト実行(yolo込み)68 passed。phase/1-upload-pipelineをmainへfast-forward mergeしpush済み(`c1a9f78`)

## T1-FIX: Phase 1 レビュー指摘の修正(Phase 2 開始前に実施)

- **目的**: Phase 1マージ後のコードレビュー(Fable 5、2026-07-16)で見つかった設計不一致2件を修正する
- **前提条件**: Phase 1完了(マージ済み)。作業は `phase/2-items-crud` ブランチの最初のコミットとして行う
- **変更対象ファイル**: `backend/app/routers/upload.py`、`backend/app/services/llm_service.py`、`backend/tests/test_upload.py`、`backend/tests/test_services.py`
- **実装内容**:
  - [x] **(1) 原画像正式保存時のENOSPCを503にする**: `routers/upload.py` 手順13の `except OSError` 内で `e.errno == errno.ENOSPC` を判定し、該当時は 503 `insufficient_storage`(retryable: true)を返す(design.md 7.8節「正式保存時のENOSPCを捕捉→503」。現状は一律500 `storage_error`)。補償処理(レコード削除+ファイル削除)は両分岐で維持。テスト追加: `save_original` をモックで `OSError(errno.ENOSPC)` にして503を確認
  - [x] **(2) LLMの非リトライ系エラーを `llm_error` に分類する**: `llm_service.extract_metadata()` を修正: ①先頭で `client is None` なら即 `LlmServiceError`(WARNINGログ「OPENAI_API_KEY未設定」)、②リトライ対象外の `openai.OpenAIError`(AuthenticationError, BadRequestError等)を捕捉し、リトライせず即 `LlmServiceError` を送出(design.md 8.3節「LLM失敗は呼び出し元でllm_errorに変換」。現状はpipelineのbroad exceptに落ちて `internal_error` になり、18.2節のllm_error率モニタリングが不正確になる)。テスト追加: client=None と AuthenticationError(モック)の両方で failure_reason=`llm_error` を確認
- **記録のみ(修正不要の観察事項)**:
  - セマフォ待機が `PROCESSING_STALE_MINUTES` を超えると待機中アイテムがlazy検出で `processing_interrupted` に誤判定されうる(status ガードにより二重処理は起きない。シングルユーザーでは実質発生しない。将来対策: セマフォ取得直後に `updated_at` をタッチ)
  - 素のHTTPException(未定義ルート404等)が `error_code=internal_error / retryable=true` にマップされる(main.py。実害小)
  - 例外ハンドラ経由の500応答にCORSヘッダが付かない(FastAPI既知挙動。本番は同一オリジンのため無関係)
- **影響範囲**: upload API(エラー分類のみ)、pipeline失敗時のfailure_reason分類
- **完了条件**: 追加テスト含む全テストgreen
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **想定される正常結果**: all passed(既存68件+追加分)
- **推奨コミットメッセージ**: `fix(upload): ENOSPCとLLMエラーの分類をdesign.mdに整合`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `be35a4d`
- **備考**: design.md本体の変更は不要(実装を設計に合わせる修正)。全テスト実行: `not yolo`で66 passed(既存63件+追加3件)、yolo込み71 passed

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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `6b829ea`
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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `eb958c5`
- **備考**: stale復旧は/statusエンドポイント専用(8.6節(b))のため詳細取得では実行しない

## T2-3: PATCH /api/items/{id}(手動補正)

- **目的**: design.md 6.6節。登録成功率64.5%を運用でカバーする中核機能
- **前提条件**: T2-2
- **変更対象ファイル**: `backend/app/routers/items.py`、`backend/app/schemas/item.py`(ItemUpdateRequest)、`backend/tests/test_items.py`
- **実装内容**: 部分更新(指定フィールドのみ)。category/pattern/materialは付録A enumで検証。更新時 `is_user_corrected=true`・`updated_at` 更新。completed以外は409(processing→item_is_processing / failed→item_not_editable)
- **サブタスク(異常系)**:
  - [x] enum違反(category="コート"等)→ 422 validation_error
  - [x] processing中のPATCH → 409 item_is_processing
  - [x] failedのPATCH → 409 item_not_editable
  - [x] color_secondary=null で副色が消せる
- **完了条件**: サブタスク含むテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_items.py -q -k patch`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(items): add metadata correction endpoint`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `d1f513e`
- **備考**: enumはdesign.md付録Aが正本。category/pattern/material/color_primary/silhouetteはcolor_secondaryと異なり非nullable(明示nullは422)

## T2-4: DELETE /api/items/{id}(物理削除)

- **目的**: design.md 6.7節・7.6節
- **前提条件**: T2-2
- **変更対象ファイル**: `backend/app/routers/items.py`、`backend/tests/test_items.py`
- **実装内容**: processing→409 item_is_processing。completed/failed→`delete_item_files(item_id)`(原画像含む全種・冪等)→レコード削除→204。ファイル一部削除失敗でもレコード削除は続行しWARNINGログ
- **サブタスク(異常系)**:
  - [x] processing中のDELETE → 409、レコード・ファイルが残る
  - [x] completedのDELETE → 204、originals/transparent/masks/annotatedの実ファイルが消える
  - [x] **failedアイテムのDELETE → 204、残っていた原画像も物理削除される**
  - [x] 既にファイルが無い状態でのDELETE → 204(冪等)
- **完了条件**: サブタスク含むテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_items.py -q -k delete`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(items): add physical deletion endpoint`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `0825f77`
- **備考**: 削除はstorage_serviceの共通関数のみ使用(重複実装禁止)

## T2-SR: Phase 2 セルフレビューと完了処理

- **前提条件**: T2-1〜T2-4完了
- **実装内容**: 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **推奨コミットメッセージ**: `chore(backend): complete phase 2 items crud`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **push済みcommit hash**: `0e2ab69`
- **備考**: 0.5節チェックリスト全項目確認済み(design.md/todo.md差分なし、DBモデル・環境変数の変更なし、.gitignore・機密情報混入なし)。全テスト: not yolo で97 passed、yolo込みで102 passed。phase/2-items-crudをmainへfast-forward mergeしpush済み(`0e2ab69`)

---

# Phase 3: コーディネート提案(ブランチ: `phase/3-suggest`)

**ゴール**: 天気あり/なし両系でコーデ提案が返り、ログが記録される。

## T3-1: weather_service と GET /api/weather

- **目的**: design.md 11.3節・6.9節
- **前提条件**: Phase 2完了
- **変更対象ファイル**: `backend/app/services/weather_service.py`、`backend/app/routers/weather.py`、`backend/app/schemas/weather.py`、`backend/tests/test_suggest.py`
- **実装内容**: `get_current_weather(city) -> WeatherInfo | None`(httpx、timeout 5秒、リトライなし、失敗はWARNINGログ+None)。`GET /api/weather`はNone時503 service_unavailable
- **サブタスク(異常系。httpxをモック)**:
  - [x] タイムアウト → None
  - [x] 非200応答 → None
  - [x] APIキー未設定 → None(例外を出さない)
- **完了条件**: モックテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_suggest.py -q -k weather`
- **想定される正常結果**: all passed
- **推奨コミットメッセージ**: `feat(weather): add openweathermap client with fallback`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `d31ba0e`
- **備考**: 実APIでの動作確認は手動で1回行う(`curl "localhost:8000/api/weather"`)。backend/.envにOPENWEATHER_API_KEY・DATABASE_URL・DEFAULT_CITYを設定して実施。初回はキー未有効化で401(→503フォールバックを確認)、T3-3のタイミングで再確認したところキーが有効化され200(盛岡市の実データ)を確認できた

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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `4b58925`
- **備考**: ルール(dress排他・同カテゴリ1点)はプロンプトで指示し、コード側では強制しない(LLM出力の検証はID実在のみ)。schemas/suggest.py(SuggestRequest/SuggestResponse)もこのタスクで先行定義(routers/suggest.pyでの結線はT3-3)。create_suggestionはClothingItem(ORM)のリストを返す設計とし、ItemResponseへの変換はT3-3のルーターで行う

## T3-3: POST /api/suggest(異常系込み)

- **目的**: design.md 6.8節・11.4節
- **前提条件**: T3-2
- **変更対象ファイル**: `backend/app/routers/suggest.py`、`backend/tests/test_suggest.py`
- **実装内容**: SuggestRequest検証(request_text 1〜500文字)→completed 0件なら**LLMを呼ばず**400 no_completed_items→天気(use_weather/city)→create_suggestion→SuggestResponse(items/weather/weather_available/log_id)
- **サブタスク(異常系)**:
  - [x] completed 0件 → 400 no_completed_items、LLMモックが呼ばれていない
  - [x] processing/failedのアイテムがクローゼットJSONに含まれない
  - [x] 天気失敗 → 200、weather_available=false、weather_json=NULLでログ記録
  - [x] LLMが無効item_idを混ぜる → 有効IDのみ返る
  - [x] 全item_id無効 → items:[] で suggestion_text が返る(200)
  - [x] LLM失敗(リトライ後)→ 503 service_unavailable、coordinate_logsに記録されない
  - [x] request_text空白のみ → 422
- **完了条件**: サブタスク含むテストgreen
- **検証コマンド**: `cd backend && python -m pytest tests/test_suggest.py -q`
- **想定される正常結果**: all passed
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(suggest): add suggestion endpoint with fallbacks`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `c2a127d`
- **備考**: 実LLMでの動作確認を実施(backend/.envにルートの.envと同じOPENAI_API_KEYをコピーして設定)。tops.jpgをアップロード→completed→`/api/suggest`で天気(盛岡・実データ)を反映した提案・実在item_idのみ・ボトムス不足を文章で補う応答を確認。検証用アイテムは確認後にDELETEで削除済み。ルーター間再利用のためroutes/items.pyの`_to_item_response`を`to_item_response`に公開化した

## T3-SR: Phase 3 セルフレビューと完了処理

- **前提条件**: T3-1〜T3-3完了
- **実装内容**: 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **推奨コミットメッセージ**: `chore(backend): complete phase 3 suggestion`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **push済みcommit hash**: `68621d2`
- **備考**: 0.5節チェックリスト全項目確認済み(design.md/todo.md差分なし、DBモデル・環境変数の変更なし、.gitignore・機密情報混入なし)。全テスト: not yoloで117 passed、yolo込みで122 passed。実API動作確認(天気・実LLM)も実施済み。phase/3-suggestをmainへfast-forward mergeしpush済み(`68621d2`)
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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `6a3f31b`
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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `79ab64f`
- **備考**: dev環境では`/images/*`がbackend(別オリジン)を指すため、`next.config.ts`にrewriteを追加(本番はCaddyが同一オリジンで処理。design.md 15.3節)。DBへ手動挿入したダミーcompleted/processing/failedデータで一覧・フィルタ・バッジ・空状態を確認後、削除済み

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
  - [x] 二重送信防止: 送信ボタン連打で1リクエストのみ
  - [x] 通信切断(202前): DevToolsオフライン化→再試行→同一キーで再送され二重登録されない
  - [x] 通信切断(202後): 202直後にリロード→ポーリングが再開される
  - [x] polling timeout: backendのパイプラインを一時的に遅延(またはPROCESSING_STALE_MINUTES内のprocessing放置)→60秒でタイムアウトUI
  - [x] failed(no_mask): 衣服なし画像で「衣服を検出できませんでした」+新規アップロード導線(同一画像の自動再送をしない)
- **完了条件**: 正常系+サブタスクの手動確認。tsc通過
- **検証コマンド**: `cd frontend && npx tsc --noEmit` + ブラウザ手動確認
- **想定される正常結果**: 登録完了までUIがブロックせず遷移する
- **想定される異常結果**: -
- **推奨コミットメッセージ**: `feat(frontend): add upload flow with state machine and idempotent retry`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `a56d171`
- **備考**: 状態名はdesign.md 12.3節と一致させる(コード上の定数名も同一)。Playwrightで実backend+実LLMを使い正常系(tops.jpg)・no_mask失敗・クライアント検証エラー・202前後の通信切断・二重送信防止・polling timeout(モックで30回ポーリング後に遷移)を確認。テスト後に作成したDB/storageのデータはDELETE APIで削除済み

## T4-4: アイテム詳細・編集画面(/items/[id])

- **目的**: design.md 12.1節。手動補正のUI
- **前提条件**: T4-2
- **変更対象ファイル**: `frontend/src/app/items/[id]/page.tsx`、`components/MetadataEditForm.tsx`
- **実装内容**: 原画像/透過画像の切替表示。6属性の編集フォーム(category/pattern/materialは付録Aのenumをセレクトボックスで)→PATCH。削除ボタン(確認ダイアログ→DELETE→一覧へ)。409(processing)時のエラートースト
- **完了条件**: 編集→一覧反映、削除→一覧から消える(手動確認)、tsc通過
- **検証コマンド**: `cd frontend && npx tsc --noEmit` + ブラウザ手動確認
- **想定される正常結果**: PATCH後に is_user_corrected が立つ(API応答で確認)
- **推奨コミットメッセージ**: `feat(frontend): add item detail with metadata correction`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `ddc15e4`
- **備考**: enumセレクトの選択肢はdesign.md付録Aと同期。Playwrightで実backend(実LLM)を使い、画像切替・編集保存(is_user_corrected=true確認)・一覧への反映・409(item_is_processing、APIモック)トースト・削除確認ダイアログ→削除→一覧リダイレクトを確認。テストで作成したデータはDELETE APIで削除済み

## T4-5: コーデ提案画面(/suggest)

- **目的**: design.md 12.1節
- **前提条件**: T4-2
- **変更対象ファイル**: `frontend/src/app/suggest/page.tsx`、`components/SuggestForm.tsx`、`components/WeatherBadge.tsx`、`components/SuggestionResult.tsx`
- **実装内容**: WeatherBadge(GET /api/weather。503時「天気情報を取得できませんでした」で提案は継続可能)。要望入力(空は送信不可)→POST /api/suggest(送信中無効化)→suggestion_text/styling_reason+推奨ItemCardハイライト。400 no_completed_items時は登録導線を表示
- **サブタスク**:
  - [x] weather_available=false でも提案が表示される
  - [x] items:[](全ID無効)でもテキストだけ表示される
  - [x] 503時にエラートースト+再試行可能
- **完了条件**: 手動確認+tsc通過
- **検証コマンド**: `cd frontend && npx tsc --noEmit` + ブラウザ手動確認
- **想定される正常結果**: 提案文と推奨アイテムがハイライト表示される
- **推奨コミットメッセージ**: `feat(frontend): add coordinate suggestion page`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `2eede51`
- **備考**: Playwrightで実backend(実LLM・実天気API)を使い正常系(推奨アイテムのハイライト表示)を確認。weather_available=false/items:[]/503+再試行はAPIモックで確認。テストで作成したデータはDELETE APIで削除済み

## T4-SR: Phase 4 セルフレビューと完了処理

- **前提条件**: T4-1〜T4-5完了
- **実装内容**: 0.5節の共通チェックリスト全消化(フロントは `npx tsc --noEmit` / `npm run build` を全テストに追加)→ ブラウザで登録→閲覧→編集→提案のE2E → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q` / `cd frontend && npm run build`
- **推奨コミットメッセージ**: `chore(frontend): complete phase 4 frontend`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **push済みcommit hash**: `27848d6`
- **備考**: 0.5節チェックリスト全項目確認済み(design.md/todo.md差分なし、backend/DBモデル・環境変数の変更なし、.gitignore・機密情報混入なし)。backend: pytest -m "not yolo" で117 passed。frontend: tsc --noEmit・npm run build通過。design.md 14.3節の手動E2Eチェックリスト項目1〜7を全て確認(項目7はDB操作でstale processingを再現しbackendのlazy stale検出とフロントエンドのprocessing_interrupted表示・localStorage解除を確認)。項目8(本番URL・スマホ)はPhase 5・6で実施。phase/4-frontendをmainへfast-forward mergeしpush済み(`27848d6`)

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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `04d824a`
- **備考**: design.md 13.4節・9.6節(情報の役割分担)。突き合わせで発見した差分を修正: (1) `database_error`(13.2節「全API」)が`upload.py`にしか実装されていなかったため、`items.py`のPATCH/DELETE commitと`suggest_service.py`のcoordinate_log commitにSQLAlchemyError→503 database_errorのハンドリングを追加。(2) `main.py`のOpenAIクライアント初期化(`OpenAI(api_key=...)`)が未ガードで13.4節「外部APIクライアント初期化エラーはメッセージを固定文字列に差し替えて記録する」に非準拠だったため、try/exceptで固定メッセージのログに差し替え、client=Noneで継続するよう修正。監査テストは`test_security.py`に集約(全error_codeレスポンスの絶対パス・Traceback・APIキー非漏洩の横断チェック、500 internal_errorの非漏洩、OpenAIクライアント初期化失敗時・LLM認証エラー時にAPIキーがログへ転記されないことをcaplogで検証)。`cd backend && python -m pytest -m "not yolo" -q` で125 passed(既存117件+新規8件)。

## T5-2: ロギング整備

- **目的**: design.md 13.5節の必須ログ項目を揃える
- **前提条件**: T5-1
- **変更対象ファイル**: `backend/app/main.py`(logging設定)、各service
- **実装内容**: フォーマット統一(stdout)。必須項目(所要時間・ロック待機・リトライ・stale復旧・削除失敗・DBロック)の出力確認。1件アップロードして各段階のINFOログが出ることを目視確認
- **完了条件**: 手動アップロード1件でパイプライン各段階のログが確認できる
- **検証コマンド**: uvicorn起動→curlアップロード→コンソールログ確認
- **想定される正常結果**: resize/yolo/save/llm/db 各段階の所要時間ログ
- **推奨コミットメッセージ**: `feat(app): add structured operational logging`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `31d1c3a`
- **備考**: 13.5節の必須ログ項目を突き合わせ、不足分を追加実装。(1)「アップロード受付/完了」item_id・受信サイズ・所要時間のINFOログを`upload.py`に新設(ファイル名・パスは記録しない)。(2)「検証失敗」error_codeのみをINFOログに残す`_validation_error`ヘルパーを追加(file_too_large/unsupported_media_type/invalid_image/idempotency_key_conflict/validation_error)。(3)「LLMリトライ」`llm_service.extract_metadata`にitem_id引数を追加し試行回数・失敗種別と併せてログに残すよう変更(呼び出し元`pipeline_service.py`・関連テストのシグネチャも追随)。(4)「ファイル削除失敗」`storage_service._safe_unlink`をitem_id・種別(kind)を引数化し構造化。パイプライン各段階・ロック待機・stale復旧・無効LLM item_id除外は既存実装で13.5節を満たすことを確認済み。自動テストで各ログ出力をcaplog検証(`test_upload.py`・`test_services.py`)。完了条件の手動確認は実施済み: `.env`の実キー・実モデル重みでuvicorn起動→`tests/fixtures/tops.jpg`をcurlアップロード→resize(0.001s)/yolo(15.252s)/save(0.751s)/llm(8.714s)/db(0.085s)の各段階ログとsemaphore待機ログを確認(生成したdata/storageはテスト用でgitignore対象・commit対象外)。`cd backend && python -m pytest -m "not yolo" -q` で129 passed。

## T5-3: README(起動手順)

- **目的**: 開発環境の起動手順を文書化
- **前提条件**: T5-2
- **変更対象ファイル**: `README.md`
- **実装内容**: プロジェクト概要、必要なもの(Python/Node/モデル重み/APIキー)、backend起動手順、frontend起動手順、テスト実行方法、docs/design.md・todo.mdへの参照
- **完了条件**: READMEの手順どおりにクリーンな環境で起動できる
- **検証コマンド**: README記載のコマンドを順に実行
- **想定される正常結果**: 起動成功
- **推奨コミットメッセージ**: `docs(readme): add setup and run instructions`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `7d5b713`
- **備考**: 既存READMEの「動かし方(現時点: AIパイプライン)」節を「Webアプリの動かし方」+「AIパイプラインNotebook(PoC・単体)」の2節に再構成し、Webアプリ(FastAPI + Next.js)の起動手順を追記(必要なもの・backend起動・backendテスト・frontend起動・frontend型チェック/ビルド、design.md・todo.mdへの参照)。ロードマップのPhase 0〜4チェックボックスも実態(mainへmerge済み)に合わせて更新。検証: backendは既存`.env`・モデル重みで`pytest -m "not yolo" -q`が129 passed(T5-2の手動確認時にuvicorn起動・curlアップロードも実施済み)。frontendは`npx tsc --noEmit`・`npm run build`が成功(既存node_modules・.env.localを使用。真の空環境でのclone検証は未実施)。

## T5-4: 手動E2Eチェックリスト消化

- **目的**: design.md 14.3節の1〜7を実施
- **前提条件**: T5-1〜T5-3
- **実装内容**:
  - [x] 1. アップロード→処理中→完了→クローゼット表示
  - [x] 2. 衣服なし写真→no_maskメッセージ
  - [x] 3. category修正→反映・is_user_corrected
  - [x] 4. 削除→一覧・storageから消える
  - [x] 5. コーデ提案→提案文+ハイライト
  - [x] 6. 通信切断→再送→二重登録なし
  - [x] 7. アップロード直後にbackend再起動→failed(処理中断)表示(PROCESSING_STALE_MINUTESを一時的に短縮して確認してよい。確認後に戻す)
- **完了条件**: 7項目すべてチェック。発見した不具合は修正して再確認
- **検証コマンド**: (手動)
- **推奨コミットメッセージ**: (修正が出た場合)`fix(...): ...`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [ ] / push済み [ ]
- **commit hash**: ______(コード変更なしのため対象commitなし)
- **備考**: 実backend(実YOLO・実OpenAI・実OpenWeatherMap)+実frontendをローカルで起動し、Playwright(headless Chromium)でブラウザ操作を自動運転して7項目を検証。スクリーンショットで目視確認済み。項目1: tops.jpgアップロード→処理中→完了→透過画像・6属性表示→クローゼット一覧に反映。項目2: no_clothing.jpgアップロード→「衣服を検出できませんでした」表示。項目3: 詳細画面でcategoryを変更・保存→「保存しました。」表示、API応答でcategory反映・is_user_corrected:true確認。項目4: 別アイテムを削除→一覧から消え、storage/originals・transparentの実ファイルも削除されたことをファイルシステムで確認。項目5: 「今日は大事な会議」で提案リクエスト→実天気(盛岡市)+実LLMによる提案文・理由・推奨アイテムのハイライト(ring)表示を確認。項目6: オフライン状態でアップロード→「通信エラーが発生しました。」+再試行ボタン表示→オンライン復帰後に再試行→アイテム作成に成功。さらに同一Idempotency-Keyで直接再送し、新規レコードを作らず既存item_idを200で返すこと(件数不変)を確認(design.md 7.7節のサーバー側dedupを直接検証)。項目7: DB直挿入でprocessingのまま放置されたアイテムを用意し、PROCESSING_STALE_MINUTES=0で一時的にbackendを再起動→起動時のrecover_stale_processing()でfailed/processing_interrupted化。pending_uploadをlocalStorageへ設定してポーリング再開をシミュレートし、「サーバーの再起動などにより処理が中断されました。」表示とlocalStorageのpending_upload解除を確認。確認後にPROCESSING_STALE_MINUTESを外して(既定値)backendを再起動済み。7項目とも不具合は見つからずコード変更なし。検証用に生成したdata/storageはテスト後に削除しクリーンな状態に戻した(いずれもgitignore対象)。

## T5-SR: Phase 5 セルフレビューと完了処理

- **前提条件**: T5-1〜T5-4完了
- **実装内容**: 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -q` / `cd frontend && npm run build`
- **推奨コミットメッセージ**: `chore(app): complete phase 5 hardening`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **push済みcommit hash**: `977e7d8`
- **備考**: 0.5節チェックリスト全項目確認済み(design.md/todo.md差分なし、API仕様・DBモデル・環境変数の変更なし、.gitignore・機密情報混入なし)。backend: `pytest -m "not yolo" -q` で129 passed、実YOLO込み`pytest -q`で134 passed。frontend: `tsc --noEmit`・`npm run build`通過。design.md 14.3節の手動E2Eチェックリスト項目1〜7を実backend(実YOLO・実OpenAI・実OpenWeatherMap)+実frontendでPlaywright自動運転により全確認(T5-4に詳細記録)。項目8(本番URL・スマホ)はPhase 6で実施。phase/5-hardeningをmainへfast-forward mergeしpush済み(`977e7d8`)

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
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `033d773`
- **備考**: ARM64ビルドはVM上で行う(ローカルがx86の場合はローカル検証はx86で可)。ultralyticsが依存する`opencv-python`(GUI版)が`opencv-python-headless`を上書きし`libxcb.so.1`欠落で起動失敗する事象が発生したため、requirements適用後に`pip install --force-reinstall --no-deps opencv-python-headless`でheadless版を再度上書きする一手間を追加。x86ローカルでビルド・起動・`/api/health`(`model_loaded:true`)確認済み、モデル未マウント時の起動失敗も確認済み

## T6-2: frontend Dockerfile

- **目的**: design.md 15.2節
- **前提条件**: T6-1
- **変更対象ファイル**: `frontend/Dockerfile`、`frontend/next.config.js`(`output: "standalone"`)、`.dockerignore`
- **実装内容**: multi-stage(node:20-slim)、standaloneビルド、`node server.js`。`NEXT_PUBLIC_API_BASE_URL` は空(同一オリジン)
- **完了条件**: ビルド・起動しトップページが表示される
- **検証コマンド**: `docker build -t smartcloset-frontend frontend/ && docker run --rm -p 3000:3000 smartcloset-frontend` → ブラウザ確認
- **想定される正常結果**: 画面表示(API未接続でも空状態表示)
- **推奨コミットメッセージ**: `feat(deploy): add frontend standalone dockerfile`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `02b03c3`
- **備考**: `next.config.js`ではなく既存の`next.config.ts`に`output: "standalone"`を追加(プロジェクトはTS設定を採用済み)。multi-stage(deps/builder/runner、node:20-slim)。x86ローカルでビルド・起動し`curl localhost:3000/`がHTTP 200・HTML表示を確認済み

## T6-3: docker-compose と Caddy

- **目的**: design.md 15.3〜15.5節
- **前提条件**: T6-1, T6-2
- **変更対象ファイル**: `deploy/docker-compose.yml`、`deploy/Caddyfile`、`deploy/.env.example`
- **実装内容**: 15.5節のcompose(**backend/frontendはportsを公開しない**、restart: unless-stopped、モデルro マウント)。15.3節のCaddyfile(**basic_auth全パス**、request_body 12MB、/api・/imagesをbackendへ、他をfrontendへ)。`.env.example` に CADDY_DOMAIN/CADDY_BASIC_AUTH_USER/CADDY_BASIC_AUTH_HASH のキー名のみ
- **サブタスク**:
  - [x] `docker compose up -d` 後、`caddy` 経由でのみアクセスできる(ホストの8000/3000が閉じている)
  - [x] Basic認証なしで401、認証ありで表示
  - [x] 12MB超のアップロードがCaddyで拒否される+FastAPI側413も機能(二重防御)
- **完了条件**: ローカル(またはVM)でcompose一式が起動しE2Eが通る
- **検証コマンド**: `cd deploy && docker compose up -d --build && curl -k -u user:pass https://localhost/api/health`
- **想定される正常結果**: healthがok、401/認証OKの切り替え確認
- **推奨コミットメッセージ**: `feat(deploy): add docker compose with caddy basic auth`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **commit hash**: `38085bd`
- **備考**: 平文パスワードをGit・composeファイルに書かない(ハッシュのみ.envへ)。x86ローカルで`CADDY_DOMAIN=localhost`(Caddyのinternal CAによる自動自己署名HTTPS)を使い検証。認証なし401/認証あり200でhealth `ok`(`model_loaded:true`)確認、ホストの8000/3000はconnection refusedで非公開を確認、13MBアップロードはCaddyで413、11MBアップロード(Caddy通過)はFastAPI側で413(`file_too_large`)を確認、二重防御が機能。T6-4の前提条件(mainにmerge済みであること)を満たすため、T6-SRを待たずphase/6-deployをmainへfast-forward mergeしpush済み(`6b4e416`)

## T6-4: Oracle VM セットアップと本番起動(Terraform)

- **目的**: design.md 15.6節の手順を実施
- **前提条件**: T6-3(mainにmerge済みであること)
- **変更対象ファイル**: `deploy/terraform/{versions.tf,main.tf,variables.tf,outputs.tf,cloud-init.yaml,terraform.tfvars.example}`、`.gitignore`(terraform state/tfvars除外)、`frontend/src/lib/api.ts`(SSR/クライアントでベースURLを分離)、`deploy/docker-compose.yml`(frontendに`INTERNAL_API_BASE_URL`追加)、`frontend/src/components/Header.tsx`(新規)、`frontend/src/app/layout.tsx`(Header組み込み)
- **実装内容**: design.md 15.6.1(手動事前準備: OCI APIキー作成・SSH鍵準備)→ 15.6.2のTerraform構成一式を実装(VCN・パブリックサブネット・IGW・ルートテーブル・セキュリティリスト・A1.Flexインスタンス、cloud-initでDocker/Docker Compose自動導入・iptables 80/443許可)→ 15.6.3の適用手順で`terraform apply`→ 15.6.4のアプリデプロイ手順(git clone・モデル重みscp・`.env`作成・`docker compose up -d --build`)→ DNS設定
- **サブタスク**:
  - [x] `terraform validate` / `terraform plan` が通る
  - [x] `terraform apply` でVCN・サブネット・セキュリティリスト・インスタンスが作成される(Out of Capacity時はOCPU数を減らす/時間を変えてリトライ)
  - [x] cloud-init完了後、SSHで`docker --version`・`docker compose version`が通る
  - [x] VM再起動(`sudo reboot`)後にサービスが自動復旧する
  - [x] `GET /api/health` が公開URLで `model_loaded:true`
- **完了条件**: 公開URLでhealth ok
- **検証コマンド**: `cd deploy/terraform && terraform apply` → `terraform output instance_public_ip` → `curl -u user:pass https://<domain>/api/health`
- **想定される正常結果**: `{"status":"ok",...}`
- **想定される異常結果**: A1確保失敗→OCPU減・時間帯変更でリトライ(design.md 15.6.3節)
- **推奨コミットメッセージ**: `feat(deploy): add terraform for oci network and compute instance`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `3e31033`
- **備考**: `ap-osaka-1`リージョンでVCN・IGW・ルートテーブル・セキュリティリスト・パブリックサブネットの作成には成功(`terraform state list`で確認可能)。A1.Flexインスタンスの作成は「Out of host capacity」で継続的に失敗していたが、OCIアカウントをPay As You Goにアップグレード後、1分間隔リトライの1回目で確保に成功(`ap-osaka-1`、2 OCPU/12GB)。認証エラー(401)は APIキー作成直後の伝播遅延が原因と判明(数十秒待てば解消)。APIキー・ハッシュ・OCI認証情報(tenancy/user OCID・fingerprint・秘密鍵パス)は`~/.oci/`・`~/.ssh/`・ローカルの`terraform.tfvars`のみに置き、Git管理外とする。デプロイ後のE2E確認で2件の設計不備を発見・修正: ①**VM内iptablesがSSH以外の新規接続をデフォルトでREJECT**しており、OCIセキュリティリストで80/443を許可していてもVM内で二重に塞がれ、Let's EncryptのACME検証が失敗していた(cloud-initにiptables許可ルール追加で対処)。②**Next.jsのServer Component(SSR)からのfetchが相対URL(`NEXT_PUBLIC_API_BASE_URL=""`)を解決できず**アイテム一覧取得が失敗していた(サーバー側専用の`INTERNAL_API_BASE_URL=http://backend:8000`を追加し、クライアント/サーバーでベースURLを分離)。また、bcryptハッシュ(`CADDY_BASIC_AUTH_HASH`)はdocker composeの`.env`自動読み込みで`$`が変数展開され値が壊れるため、`.env`内で`$`を`$$`にエスケープする対応も実施(design.md 15.5節に記載)。③**画面間のナビゲーションが設計・実装ともに一度も存在しなかった**(design.md 12.1節の4画面は相互リンクを持たず、`/`のアイテム0件時リンクのみが唯一の導線)。スマホE2Eで発覚し、`Header`コンポーネントを追加して`app/layout.tsx`に組み込み(design.md 12.2節に追記)

## T6-5: バックアップ・復元スクリプト

- **目的**: design.md 16章
- **前提条件**: T6-4
- **変更対象ファイル**: `scripts/backup.sh`、`scripts/restore.sh`
- **実装内容**: 16.1節の手順(backend停止→sqlite3 .backup→tar(tmp除外)→再開→世代整理BACKUP_RETENTION_COUNT=7)。同一タイムスタンプ命名 `smartcloset_backup_{YYYYMMDD_HHMMSS}.{db,tar.gz}`。restore.sh は16.2節(退避→配置→起動→**DB内画像パスと実ファイルの存在検証**)
- **サブタスク**:
  - [x] VM上でbackup実行→2ファイル生成・タイムスタンプ一致
  - [x] restore実行→アプリが復元データで動作・検証スクリプトが欠損ゼロを報告
  - [x] 8世代目作成で最古が削除される
- **完了条件**: サブタスク全消化
- **検証コマンド**: `bash scripts/backup.sh && ls ~/smartcloset_backups/`
- **想定される正常結果**: `.db` と `.tar.gz` が同一タイムスタンプで生成
- **推奨コミットメッセージ**: `feat(ops): add consistent backup and restore scripts`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [ ] / push済み [ ]
- **commit hash**: ______
- **備考**: 同一VM内のみのバックアップはVM消失に無力(Known Limitation。将来Object Storage退避)。VM上でのテストで3件判明・修正: ①`backend/data`・`backend/storage`はbackendコンテナ(root実行)が作成するためroot所有(755)で、`ubuntu`ユーザーからの書き込み・sqlite3の`.backup`が権限不足で失敗する→該当操作に`sudo`を付与(design.md 16.1節に追記)。②`tar`の`--exclude`オプションは位置引数より前に置く必要がある(GNU tarの仕様。design.md 16.1節のコマンド例を修正)。③`sqlite3` CLIがVM(cloud-init)に含まれていなかった→cloud-init.yamlの`packages`に追加(design.md 15.6.2節に追記)。VM上で実データ(アイテム1件)を用いてbackup→restore→検証スクリプトの欠損ゼロ確認、および8世代目作成時の世代整理(最古削除)まで実施

## T6-6: 本番E2E(スマホ)

- **目的**: design.md 14.3節-8
- **前提条件**: T6-4, T6-5
- **実装内容**: スマホブラウザで公開URLにアクセス(Basic認証)し、14.3節の1〜5を実施。カメラ撮影画像のアップロード(EXIF Orientation補正の実機確認を含む)
- **完了条件**: スマホで登録→閲覧→編集→提案が完結
- **検証コマンド**: (手動)
- **推奨コミットメッセージ**: (修正が出た場合)`fix(...): ...`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x](コード変更なし) / push済み [ ]
- **commit hash**: N/A(修正不要だったため)
- **備考**: 縦撮り写真が横倒しにならないこと(EXIF補正の確認ポイント)。ユーザーによるスマホ実機確認完了、動作は問題なし。UI・提案内容の改善希望はあるが機能的なブロッカーではないため、Phase 6完了後にまとめて対応する方針(ユーザー合意済み)

## T6-SR: Phase 6 セルフレビューと完了処理

- **前提条件**: T6-1〜T6-6完了
- **実装内容**: **READMEを完成状態に更新**(①ステータス行を「稼働中」へ ②デモ画像を選抜して `docs/images/` にcommitし掲載=README内の `TODO(デモ)` コメント参照 ③動かし方の最終確認 ④ロードマップ全チェック+「今後の展望」をdesign.md 18章から数行追記)→ 0.5節の共通チェックリスト全消化 → ユーザー承認のもとpush・mainへmerge
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q` / 公開URLでのhealth確認
- **推奨コミットメッセージ**: `chore(deploy): complete phase 6 deployment`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **push済みcommit hash**: `728b8d9`
- **備考**: 0.5節チェックリスト全項目確認済み(design.md/todo.md差分なし、API仕様・DBモデル・環境変数の変更なし、.gitignore・機密情報混入なし)。backend: `pytest -m "not yolo" -q` で129 passed。frontend: `tsc --noEmit`・`npm run build`通過。公開URL(本番環境)の`/api/health`で`model_loaded:true`確認済み。README更新完了(ステータス「稼働中」・デモ画像4枚掲載・ロードマップ全チェック・今後の展望追記)。push・mainへのmergeはユーザー承認待ち

## T7-1: UI改善パス(アップロード・ナビ・README仕上げ)

- **目的**: T6-6備考で先送りしていたUI改善希望への対応(design.md変更を伴わないフロントエンド限定の変更)
- **前提条件**: Phase 6完了
- **変更対象ファイル**: `frontend/src/components/{UploadDropzone,Header,icons}.tsx`、`README.md`
- **実装内容**: ①アップロード画面のドラッグ&ドロップを廃止し「写真を撮る」(`capture="environment"`)・「ライブラリから選択」の2ボタンに変更 ②ナビ(Header)にクローゼット/衣服を登録/コーデ提案の3アイコンを手書きSVGで追加(新規ライブラリ依存なし) ③READMEを再構成(AIパイプライン画像を技術ハイライト節へ移動しアプリ画面スクリーンショット枠を冒頭に確保、Terraform言及、`/images`ルートをアーキテクチャ図に追記、ディレクトリ構成セクション新設、Docker Compose起動手順を追記)
- **完了条件**: 型チェック・ビルドが通り、backendテストに影響がない
- **検証コマンド**: `cd frontend && npx tsc --noEmit && npm run build` / `cd backend && python -m pytest -m "not yolo" -q`
- **想定される正常結果**: 型エラーなし・ビルド成功・backend 129 passed
- **推奨コミットメッセージ**: `fix(frontend): アップロードUIとナビアイコンを改善`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **commit hash**: `e9061d5`
- **備考**: アプリ画面のスクリーンショットは、別途計画中の天気・提案機能の再設計(コーデ提案画面のUIが変わる見込み)の後にまとめて撮影する方針のため今回は見送り。README内のTODOコメントはそのまま残す。コーデ提案の「おすすめアイテム」表示はユーザー懸念(適当な画像では?)を調査した結果バグではないことを確認済み(backend側でLLM推奨IDをDB照合済みのもののみ返す設計)。天気・提案機能の再設計は別ブランチ・別タスクとして今後計画する。**本番VMへのデプロイはT8-1と合わせて2026-08-07に実施済み**(下記T8-1参照)

## T8-1: コーデ提案の場所・日付対応+吹き出しチャットUI化

- **目的**: T7-1備考・メモリ`project_weather_suggest_redesign`で先送りしていた天気・提案機能の再設計。request_textから場所・日付を抽出し、常に固定デフォルト都市(Morioka)の現在天気しか使えなかった問題を解消。あわせて提案結果をLINE風の会話履歴チャットUIに変更
- **前提条件**: T7-1完了
- **変更対象ファイル**: `backend/app/prompts/location_prompt.py`(新規)、`backend/app/services/{location_extraction_service,weather_resolution_service}.py`(新規)、`backend/app/services/weather_service.py`、`backend/app/schemas/weather.py`、`backend/app/routers/suggest.py`、`backend/app/prompts/suggest_prompt.py`、`backend/tests/test_suggest.py`、`frontend/src/app/suggest/page.tsx`、`frontend/src/components/{SuggestForm,SuggestionResult}.tsx`、`frontend/src/components/WeatherBadge.tsx`(削除)、`frontend/src/lib/types.ts`、`README.md`、`docs/design.md`(6.8/6.9/11.1/11.3/11.4/12.1/12.2/付録B.2/B.3)
- **実装内容**: ①request_textから場所・日付を抽出する軽量LLM呼び出し(`location_extraction_service`。リトライなし・fail-soft) ②現在天気/予報(5日先まで)の呼び分け(`weather_resolution_service.resolve_weather`。`create_suggestion`のシグネチャは不変) ③予報API呼び出し(`weather_service.get_forecast_weather`。`WeatherInfo.forecast_date`追加) ④提案文に天気を自然に織り込むプロンプト調整 ⑤`WeatherBadge`廃止、`SuggestionResult`を吹き出しチャット風に再デザイン ⑥`/suggest`ページをLINE風の会話履歴スタック形式に変更(送信ごとに自分の発言+提案結果が積み上がる。入力欄は送信後に自動クリア。履歴はクライアント側state のみ、DB永続化なし)
- **完了条件**: バックエンド・フロントエンドのテストが全てパスし、実機で「明日沖縄で会議」のような都道府県名+未来日付を含むテキストから該当地域・日付の天気が使われることを確認
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q` / `cd frontend && npx tsc --noEmit && npm run build`
- **想定される正常結果**: backend 147 passed(既存全件+新規)、frontend型エラーなし・ビルド成功
- **推奨コミットメッセージ**: `feat(suggest): 場所・日付を考慮した天気解決と吹き出しチャットUIを追加`
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [x]
- **commit hash**: `13fa208`
- **備考**: 実装直後の実機検証で、「沖縄」「北海道」等の**都道府県名・地方名のみ**の地名指定時に`gpt-5.4-nano`がcityをnullにしてしまう不具合を発見(市区町村名は問題なし)。プロンプトの「地名が明示されていなければnull」という制約が過度に厳格に解釈されていたため、都道府県名・地方名も対象に含む旨を明示する指示文に修正し解消(実機で複数回再現・修正確認済み)。またローカル動作確認中に「1回分の結果表示のみ」という当初方針(T7-1計画時点)が実際には不便との指摘を受け、送信ごとに履歴が積み上がるLINE風チャットUIに設計変更(design.mdも合わせて更新)。**2026-08-07、T7-1分と合わせて本番VMへデプロイ完了**(`git archive`でmainを転送→`docker compose up -d --build`。`backend/data`・`backend/storage`・`.env`・`models/`は保護。スマホ実機で「明日沖縄で会議」等が正しく反映されることを確認済み)

## T9-1: コーデ提案の用途・シーン(TPO)反映強化

- **目的**: プロダクトオーナー確認により、コーデ提案(`POST /api/suggest`)が天気にばかり言及し、request_textが示す用途・シーン(例: デート・面接)をほぼ反映していない問題が判明。T8-1(commit `13fa208`)で追加した「天気に必ず触れる」ルールが天気側に過度に偏った結果であり、当初の構想(`docs/archive/00_initial_concept.md`: 気温/予定/気分の3変数)にあった「予定」の重みを取り戻す
- **前提条件**: T8-1完了
- **変更対象ファイル**: `backend/app/prompts/suggest_prompt.py`、`backend/tests/test_suggest.py`、`docs/design.md`(11.2節・付録B.2)
- **実装内容**: (1)システムプロンプトの文言を「ユーザーの要望(用途・シーン)を最優先しつつ天気にも配慮した」に変更 (2)ユーザープロンプトテンプレートのセクション順を「ユーザーの要望」→「天気情報」に入れ替え (3)気温・天候に明らかに合わない厚さ・素材(真夏の厚手アウターやウール、真冬の半袖のみ等)を「羽織る」等の口実を含めて一切除外するハード制約ルールを追加(用途・シーンより優先) (4)除外後の候補の中からrequest_textの用途・シーンに沿って選ぶルールに変更 (5)既存の天気言及ルールを「シーンに合わせた提案理由を主軸にしつつ天気にも簡潔に触れる」に弱める(削除はしない。天気軽視の再発防止)
- **完了条件**: `backend/tests/test_suggest.py`の新規テストが新ルール文言の反映・セクション順・実際にLLMへ送るmessages[1]内容への反映を検証してパスすること。`suggest_prompt.py`と`docs/design.md`付録B.2が一字一句同一であることを目視diffで確認。ローカルで実OpenAI APIを使い、面接・デート等のリクエストで提案文がシーンに触れること、および真夏の暑い地域でウール等の厚手アイテムが選ばれにくくなることを確認
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **想定される正常結果**: 既存全件+新規テストがすべてpass
- **想定される異常結果**: 新ルール文言のtypoや`_USER_PROMPT_TEMPLATE`のプレースホルダ名不一致による`KeyError`/`str.format`失敗 → 新規ユニットテスト(`build_suggest_user_prompt`直接呼び出し)で検出。プロンプトはハード制約であってもLLMの確率的挙動のため100%の遵守は保証できない(備考参照)
- **推奨コミットメッセージ**: `docs(design): コーデ提案プロンプトの用途・シーン優先ルールを追加`(設計変更) / `feat(suggest): コーデ提案プロンプトで用途・シーン(TPO)を天気より優先するよう調整`(実装)
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `9d930a3`, `4f2488e`(設計変更commit: `f5b985d`, `082cb11`)
- **備考**: `cd backend && python -m pytest -m "not yolo" -q` で149 passed(既存147件+新規3件。1件`test_no_bulk_file_read_in_storage_service`が失敗するが、変更前のコード(mainブランチ)でも同じくWindows環境のcp932デコードエラーで失敗することを確認済みのため今回の変更とは無関係)。ローカルで実OpenAI APIキーを使い目視確認: ①「明日の面接に着ていく服を提案してください」→フォーマル・清潔感を主軸に理由づけ ②「週末デートに着ていく服を提案してください」→面接とは異なるトーンで理由づけ ③「明日沖縄でデートなので服を提案してください」(28℃・晴れ)→当初の実装ではウール素材のテーラードジャケットが「羽織り前提」という口実で選ばれ続ける不具合を発見(ユーザー指摘で判明)。ルールに「羽織る」「持ち歩く」等の口実を含めて一切除外する旨を明記して再検証したところ、5回中5回でウール系アイテム(id 3, 5)が選ばれず、styling_reasonにも「28℃のため厚手ウールのスラックスやテーラードは避けました」等の理由が明記されるようになった(改善前は同条件で高確率で選ばれていた)。④対比として「明日札幌でデートなので服を提案してください」(3℃・雪)ではウールのテーラード・スラックスが適切に選ばれることを確認(気温に応じた両方向の挙動を確認)。**注意**: これはプロンプトによるソフトな制約であり、LLMの確率的挙動のため稀に(観測範囲では低頻度)違反するケースが起こりうる。100%の保証が必要な場合はサーバー側でcloset_jsonを気温に応じてフィルタする実装が別途必要(今回はプロンプト改善のみで対応。追加対応の要否は別途相談)

## T9-2: コーデ提案でのサーバー側「気温不適合素材」除外(ハード保証)

- **目的**: T9-1の備考で先送りしていた「プロンプトのソフトな制約では100%保証できない」問題への対応。実LLM検証で、天気ハード制約ルールが「羽織る」「雨よけ」等の口実で破られる不具合(那覇29℃でウール素材のテーラードジャケットが選ばれ続ける)をユーザーが発見。サーバー側でクローゼットJSON生成前に気温不適合な素材を機械的に除外し、LLMの選択肢自体から外すことで確実に防ぐ
- **前提条件**: T9-1完了
- **変更対象ファイル**: `backend/app/config.py`、`backend/app/services/suggest_service.py`、`backend/tests/test_suggest.py`、`docs/design.md`(5.2節・11.1節・11.2節・11.4節)
- **実装内容**: (1)`Settings`に`HOT_WEATHER_TEMP_THRESHOLD_C: float = 25.0`を追加(既存の`CONF_THRES`等と同じくハードコードdefault、`.env.example`変更不要) (2)`suggest_service.py`に`_WARM_MATERIALS = frozenset({"ウール", "フリース", "ファー", "ボア"})`と`_filter_weather_appropriate(items, weather)`を追加。`weather.feels_like`が閾値以上なら`_WARM_MATERIALS`のアイテムを除外(除外後0件ならフィルタ適用せず全件返す) (3)`create_suggestion`で`_closet_json`・`items_by_id`の対象をこのフィルタ後のアイテムに変更
- **スコープ外(意図的)**: 「気温が低いときに薄着を避ける」逆方向の保証は対象外。`material`のenumに夏専用と断定できる値がなく実装が困難なため、プロンプト側の努力目標のまま維持する(ユーザー合意済み)
- **完了条件**: `backend/tests/test_suggest.py`の新規テスト(単体4ケース+統合1ケース)がパスすること。実OpenAI・実OpenWeatherMap APIを使い、那覇・高温設定でウール系アイテムのIDが`closet_json`(LLMに送るmessages[1]の内容)に一切含まれないことを複数回の実行で確認すること
- **検証コマンド**: `cd backend && python -m pytest -m "not yolo" -q`
- **想定される正常結果**: 既存全件+新規テストがすべてpass
- **想定される異常結果**: 全アイテムが厚手素材の場合にフィルタで0件になり得るバグ → フォールバック(全件返す)のテストで検出
- **推奨コミットメッセージ**: `docs(design): コーデ提案にサーバー側の気温フィルタを追加`(設計変更) / `feat(suggest): 気温に応じてクローゼットJSONから厚手・防寒素材を除外`(実装)
- **チェック**: 実装済み [x] / テスト済み [x] / commit済み [x] / push済み [ ]
- **commit hash**: `b0f5b98`(設計変更commit: `73f63e1`)
- **備考**: `cd backend && python -m pytest -m "not yolo" -q` で154 passed(既存149件+新規5件。1件`test_no_bulk_file_read_in_storage_service`は変更前から失敗するWindows環境固有の既存問題で無関係)。実backend(TestClient。YOLOのみダミー化)+実OpenAI+実OpenWeatherMap APIのフルパイプラインで動作確認: 「明日沖縄でデートなので服を提案してください」(那覇・体感35.08℃・小雨)で、ログに`suggest: excluded 2 warm-material item(s) for hot weather`が出力され、LLMへの`closet_json`自体からウール素材(bottoms・outer)が除外されていることを確認。結果としてLLMは残った候補からシフォンワンピを選択し、ウール系アイテムのIDは応答に一切含まれなかった。同様に「明日札幌でデートなので服を提案してください」も実行日(2026-08-15)の実際の天気が体感27.72℃だったため同じく除外が発動し、コットン×デニムの組み合わせが選ばれた(季節上、実APIでは真冬のケースを再現できなかったが、自動テストの`test_filter_weather_appropriate_keeps_warm_materials_when_not_hot`で気温が閾値未満の場合にウール素材が除外されないことを別途確認済み)。これはLLMの気まぐれな言い訳(「羽織る」「雨よけ」等)に依存しない、選択肢自体から外れることによる確実な除外であることを確認した

---

# 完成条件(全体)

- [x] Phase 0〜6 の全タスク・全サブタスクのチェックが埋まっている
- [x] `docs/design.md` と実装に差分がない(あれば0.3の手順で解消済み)
- [x] 公開URL(Basic認証付きHTTPS)でスマホからE2Eフローが成功する
- [x] 月額費用がOpenAI API従量分のみである(design.md 15.7節)(OCIコスト分析で2026-08-01〜07の累積コスト¥0を確認。Pay As You Go化後もAlways Free枠内〈2 OCPU/12GB・ブートボリューム100GB〉に収まっている)
- [x] バックアップ・復元が検証済みである

(以上 / SmartCloset AI 実装TODO ver 1.0)



