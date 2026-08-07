# SmartCloset AI 設計書最終版

**ver 2.0 / 2026-07**

---

# 1. ドキュメント情報

## 1.1 基本情報

| 項目 | 内容 |
|---|---|
| 文書名 | SmartCloset AI 設計書最終版(ver 2.0) |
| 対象システム | SmartCloset AI(クローゼット管理・コーディネート提案Webアプリ) |
| 作成目的 | Claude Code が本書と `docs/todo.md` のみを参照して、実装・テスト・commit・GitHubへのpushまで完遂できる粒度で全体を定義する |
| 想定読者 | Claude Code / 開発者本人 |
| 実装形態 | フルスタックWebアプリケーション(backend: FastAPI / frontend: Next.js) |
| 実行環境 | 開発: ローカルLinux / 本番: Oracle Cloud Always Free ARM VM(Docker Compose) |
| 関連文書 | `docs/todo.md`(作業指示書)、`docs/specification.md`、`docs/prompt_design.md`、`docs/evaluation.md` |

## 1.2 関連ドキュメントの役割分担

| 文書 | 役割 | 本書との関係 |
|---|---|---|
| `docs/design.md`(本書) | 実装のための唯一の正本。API・DB・処理順序・設定値・エラーコード・運用を定義 | **矛盾時は本書が最優先** |
| `docs/todo.md` | 本書を実装に落とすための作業指示書。タスクID・完了条件・検証コマンド・commit/push管理 | 本書の章番号を参照する |
| `docs/specification.md` | AI PoCの仕様・結果の記録(歴史的正本)。**変更しない** | PoC結果数値・9カテゴリ定義の出典。同文書14章の将来構成(PostgreSQL等)は本書が上書きする |
| `docs/prompt_design.md` | 属性抽出プロンプトの設計根拠・改善履歴 | enum候補値の出典。本書付録Aと同値。変更時は prompt_design.md を先に更新する |
| `docs/evaluation.md` | PoC評価基準(○△×)+モデル指標との対応考察 | テスト・モニタリング設計の参照元 |
| `docs/val_result_9class_30epoch_data_augmentation.md` | 学習時 `model.val()` の標準指標(mAP等、クラス別) | モデルレベルのベンチマーク記録。18.2節のモニタリングの基準値 |
| `docs/poc_history.md` | PoC開発の記録 — 技術的意思決定と知見(ドメインシフト発見・クラス設計の変遷) | 歴史的記録。設計判断の背景資料であり、実装の参照元にしない |
| `docs/archive/00_initial_concept.md` | 開発初期の構想メモ(目的・差別化・動機)の歴史的記録 | メンテナンスしない。実装の参照元にしない |
| `docs/archive/01_design_v1.0.md` | 詳細設計書 ver 1.0 の歴史的記録 | メンテナンスしない。本書2.3節の変更点一覧の比較元。実装の参照元にしない |

## 1.3 用語定義

| 用語 | 意味 |
|---|---|
| アイテム(item) | クローゼットに登録される衣服1点。DBの `clothing_items` 1行に対応 |
| 原画像(original) | アップロード画像に検証・EXIF Orientation補正・色空間正規化・不要EXIF除去を施して保存した画像(7.6節) |
| 透過画像(transparent) | YOLOセグメンテーションのマスクで背景を透過したRGBA PNG |
| AIパイプライン | YOLOセグメンテーション → 透過画像生成 → LLM属性抽出 → DB更新 の一連の処理 |
| stale processing | AI処理中にプロセス停止等が起き、`processing` のまま放置されたDBレコード(8.6節) |
| 補償処理 | ファイル保存とDB更新の間でトランザクションを張れないため、途中失敗時に逆操作で整合性を回復する処理(7.5節) |

## 1.4 設計変更時の運用ルール(厳守)

実装中に設計変更が必要になった場合、以下の順番を厳守する。**コードのみを先に変更し、設計書を後から合わせる運用は禁止。**

1. `docs/design.md` を更新
2. `docs/todo.md` を更新
3. 設計変更を commit(`docs(design): ...`)
4. コードを実装
5. テストを追加または修正
6. 実装を commit
7. Phase完了時に GitHub へ push

---

# 2. 実装方針・技術スタック

## 2.1 確定技術スタック

| レイヤー | 技術 | 備考 |
|---|---|---|
| バックエンド | Python 3.12 / FastAPI / uvicorn(単一ワーカー) | |
| 非同期AI処理 | FastAPI BackgroundTasks | 永続キューではない。制約と補償は 8.5〜8.6節 |
| DB | SQLite + SQLAlchemy 2.x | WAL・busy_timeout設定(9.4節)。PostgreSQL移行パスあり(18章) |
| 画像ストレージ | ローカルファイル(`backend/storage/`) | S3移行パスあり(18章) |
| セグメンテーション | YOLOv8n-seg ファインチューニング済み `models/fashionpedia_9class_with_data_augmentation.pt` | 9クラス、CONF_THRES=0.25 |
| 属性抽出LLM / コーデ提案LLM | OpenAI GPT-5.4-nano(`gpt-5.4-nano`) | strict JSON Schema(付録B) |
| 天気API | OpenWeatherMap Current Weather Data | タイムアウト5秒、失敗時フォールバック(11.3節) |
| フロントエンド | Next.js(App Router)/ React / TypeScript / Tailwind CSS | |
| デプロイ | Oracle Cloud Always Free ARM VM + Docker Compose + Caddy(自動HTTPS+Basic認証) | 15章 |
| テスト | pytest / TestClient(バックエンド)、tsc+手動E2E(フロントエンド) | 14章 |

## 2.2 ユーザー管理方針

- MVPは**シングルユーザー・ログインなし**。全データは `user_id=1` 固定で保存する
- DBスキーマには `user_id` 列を持たせ、将来のマルチユーザー化(18章)に備える
- 公開URLになるため、アプリ外側で Caddy の Basic認証を必須とする(15.3節)

## 2.3 旧設計書(ver1.0)からの変更点一覧

| 項目 | 旧(ver1.0) | 新(本書) | 理由 |
|---|---|---|---|
| LLM | Gemini API / GPT-4V 併記 | OpenAI GPT-5.4-nano に統一 | PoCで確定。`.env` も OPENAI_API_KEY のみ |
| 非同期処理 | Celery + Redis | FastAPI BackgroundTasks | 個人MVPでインフラ最小化。移行パスは18.1節 |
| DB | PostgreSQL | SQLite(WAL) | 追加インフラゼロ。SQLAlchemy経由で移行容易 |
| 画像ストレージ | AWS S3 / GCS | ローカルファイル | 同上。storage_service に隔離し差し替え可能に |
| status値 | `processing / complete / failed` | `processing / completed / failed` | **`complete` は使用禁止。`completed` に完全統一** |
| メタデータ | category/色2種/pattern/silhouette | + **material** を追加(計6属性) | PoCで有効性確認済み(成功率88.0%) |
| 認識クラス | COCOプリトレイン(person, tie等) | ファインチューニング済み9クラス | 7→13→9クラスの試行を経て確定 |
| 画像リサイズ | クライアントで640×640固定 | サーバー側で長辺1280のアスペクト比維持リサイズ(推論時)。クライアント縮小は任意最適化 | 正方形強制はアスペクト比を破壊。ultralyticsが推論時にレターボックス処理するため事前正方形化は不要 |
| 入力形式 | JPEG/PNG | JPEG/PNG(変更なし。specification.md の webp はMVP対象外) | 検証実装をシンプルに保つ。webpは将来拡張 |
| 天気API入力 | 緯度・経度(Geolocation API) | 都市名(`city`、既定値 `DEFAULT_CITY`) | MVP簡素化。Geolocation対応は将来拡張 |
| アップロードAPI | user_id をクライアントから受領 | user_id は受け取らずサーバー側で1固定 | シングルユーザーのため |
| 重複登録防止 | なし | **Idempotency-Key をMVPから実装**(7.7節) | 通信切断後の再送による二重登録防止 |
| ユーザー補正 | なし | `PATCH /api/items/{id}` による手動補正 | 最終登録成功率64.5%を運用でカバー |

## 2.4 実装の重要原則

1. **202 Accepted は、入力検証・原画像正式保存・DB仮登録・BackgroundTasks登録がすべて完了した後にのみ返す**(7章)
2. BackgroundTasks には **`item_id`(文字列)のみ**を渡す。DB Session・UploadFile・開いたファイルオブジェクト・YOLO推論結果・SQLAlchemyモデルオブジェクトを渡さない(8.4節)
3. ファイル削除は `storage_service.py` の共通関数に集約し、冪等に実装する(10.4節)
4. エラー応答は `{detail, error_code, retryable}` に統一する(13章)
5. 内部例外メッセージ・APIキー・絶対パス・スタックトレースをAPIレスポンスに含めない。詳細はログのみに記録する(13.4節)
6. SQLite固有処理(接続引数・PRAGMA)は `database.py` に隔離する(9.4節)
7. Celery移行時の差し替え点は `routers/upload.py` のディスパッチ1箇所に隔離する(8.7節)
8. モデル重み(`*.pt`)はGit管理外。起動時に存在チェックし、無ければ**バックエンドを起動失敗**させる(5.3節)

---

# 3. システム全体構成

## 3.1 構成図

```
                          [ユーザー(ブラウザ/スマホ)]
                                    │ HTTPS
                                    ▼
                    ┌────────────────────────────┐
                    │  Caddy(:443)  外部公開はここのみ   │
                    │  自動HTTPS / Basic認証 /          │
                    │  アップロードサイズ上限             │
                    └───────┬──────────┬─────────┘
              Docker内部ネットワーク │          │
             (外部非公開)        ▼          ▼
                 ┌──────────────┐  ┌──────────────┐
                 │ frontend      │  │ backend       │
                 │ Next.js(:3000)│  │ FastAPI(:8000)│
                 └──────────────┘  │  uvicorn 1worker│
                                   └──┬────┬────┬──┘
                                      │    │    │
                     BackgroundTasks   │    │    │ httpx
                    ┌──────────────┐   │    │    ▼
                    │ AIパイプライン  │◄──┘    │  [OpenWeatherMap]
                    │ YOLOv8n-seg   │        │  [OpenAI API]
                    │ → GPT-5.4-nano│        │
                    └──────┬───────┘        │
                           ▼                ▼
                 ┌──────────────┐  ┌──────────────┐
                 │ storage/      │  │ SQLite(WAL)  │
                 │ 画像ファイル    │  │ data/*.db     │
                 └──────────────┘  └──────────────┘
                 (両方ともVMディスクにボリュームマウントで永続化)
```

## 3.2 シーケンス①: 画像アップロード〜AI処理〜ポーリング

```
ブラウザ              FastAPI(upload router)        BackgroundTasks         DB / storage
  │ Idempotency-Key生成 │                              │                     │
  │─POST /api/upload──►│                              │                     │
  │  (multipart+Key)    │ 1. Content-Length事前確認      │                     │
  │                     │ 2. 空き容量事前確認             │                     │
  │                     │ 3. tmpへチャンク保存(+SHA-256)  │                     │
  │                     │ 4. 実サイズ・形式・実データ検証   │                     │
  │                     │ 5. EXIF補正・正規化             │                     │
  │                     │ 6. item_id生成                │                     │
  │                     │ 7. DB仮登録(processing)────────────────────────────►│
  │                     │ 8. 原画像を正式保存─────────────────────────────────►│
  │                     │ 9. 原画像パスをDBに反映─────────────────────────────►│
  │                     │ 10. add_task(run_pipeline_for_item, item_id)│       │
  │◄──202 {item_id}────│ 11. finallyでtmp削除            │                     │
  │                     │                              │(レスポンス返却後に実行) │
  │                     │                              │ ロック取得(並列度1)     │
  │─GET /items/{id}/status(2秒間隔)─►                   │ YOLO→透過PNG→LLM     │
  │◄──{status:processing}──                            │ 成功: completedへ更新──►│
  │        ...                                         │ 失敗: failedへ更新+     │
  │─GET /items/{id}/status─►                           │  不完全生成物削除────────►│
  │◄──{status:completed}──                             │ (原画像は保持)          │
  │─GET /api/items/{id}─► (メタデータ・画像URL取得)        │                     │
```

- 202を返す**前に**失敗した場合はDBレコード・ファイルを残さない(補償処理: 7.5節)
- 202を返した**後に**失敗した場合は `failed` レコード+原画像を残す(7.6節)
- ポーリングが60秒でタイムアウトしてもサーバー側statusは変更しない(12.5節)

## 3.3 シーケンス②: コーディネート提案

```
ブラウザ                FastAPI(suggest router)                  外部
  │─POST /api/suggest──►│                                        │
  │ {request_text, city} │ 1. completedアイテムをDBから取得          │
  │                      │    (0件なら400 no_completed_items で終了)│
  │                      │ 2. 天気取得(timeout 5s)────────────────►│ OpenWeatherMap
  │                      │    失敗時: weather=None で続行            │
  │                      │ 3. クローゼットJSON構築(completedのみ)     │
  │                      │ 4. LLM呼び出し(strict JSON Schema)─────►│ OpenAI
  │                      │    失敗時: 最大2回リトライ→503             │
  │                      │ 5. 返却item_idsをDB照合し無効IDを除外      │
  │                      │ 6. coordinate_logsに記録                 │
  │◄─200 {suggestion_text, items, weather_available}              │
```

## 3.4 FastAPI BackgroundTasks の性質(前提知識)

- BackgroundTasks は**レスポンス返却後に同一プロセス内で実行される**。永続的なタスクキューではない
- uvicornプロセス停止・VM再起動・Docker再起動が起きると、**登録済み・実行中のタスクは失われる**
- 同期関数(`def`)を渡した場合はスレッドプールで実行される。本設計ではAIパイプラインを同期関数とし、排他制御で同時実行数1に制限する(8.5節)
- **登録後の実行保証は行わない**。失われたタスクは「起動時のstale processing復旧」と「status取得時のlazy検出」で補償する(8.6節)

# 4. ディレクトリ構成・ファイル詳細設計

## 4.1 リポジトリ全体構成

```
SmartCloset_AI/
├── backend/                     # ★新規(Phase 0〜3, 5)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── clothing_item.py
│   │   │   └── coordinate_log.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── error.py
│   │   │   ├── item.py
│   │   │   ├── suggest.py
│   │   │   └── weather.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── items.py
│   │   │   ├── suggest.py
│   │   │   ├── upload.py
│   │   │   └── weather.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── image_validation_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── pipeline_service.py
│   │   │   ├── storage_service.py
│   │   │   ├── suggest_service.py
│   │   │   ├── weather_service.py
│   │   │   └── yolo_service.py
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── metadata_prompt.py
│   │       └── suggest_prompt.py
│   ├── storage/                 # Git管理外(10章)
│   │   ├── tmp/
│   │   ├── originals/
│   │   ├── transparent/
│   │   ├── masks/
│   │   └── annotated/
│   ├── data/                    # Git管理外(smartcloset.db)
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── fixtures/            # テスト用実画像・不正ファイル(14.2節)
│   │   ├── test_health.py
│   │   ├── test_upload.py
│   │   ├── test_items.py
│   │   ├── test_suggest.py
│   │   └── test_services.py
│   ├── .env.example
│   ├── Dockerfile               # Phase 6
│   └── requirements.txt         # backend専用の最小構成(4.3節)
├── frontend/                    # ★新規(Phase 4, 6)。create-next-app で生成
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # クローゼット一覧
│   │   │   ├── upload/page.tsx      # 衣服登録
│   │   │   ├── items/[id]/page.tsx  # アイテム詳細・編集
│   │   │   └── suggest/page.tsx     # コーデ提案
│   │   ├── components/
│   │   └── lib/
│   │       ├── api.ts
│   │       └── types.ts
│   ├── Dockerfile               # Phase 6
│   └── (create-next-app 標準ファイル)
├── deploy/                      # ★新規(Phase 6)
│   ├── docker-compose.yml
│   ├── Caddyfile
│   └── .env.example             # デプロイ用環境変数の見本
├── scripts/                     # ★新規(Phase 6)
│   ├── backup.sh
│   └── restore.sh
├── models/                      # 既存。Git管理外。学習済み重み
├── ai_prototype/                # 既存。実装の参照元(変更しない)
├── training/                    # 既存(変更しない)
├── dataset/                     # 既存。Git管理外(変更しない)
└── docs/                        # 既存3ファイル+design.md+todo.md
```

## 4.2 backend/app 各ファイルの責務

| ファイル | 責務 | 公開関数・オブジェクト | 主な依存先 |
|---|---|---|---|
| `main.py` | FastAPIアプリ生成。lifespan(モデルロード・モデル存在チェック・stale復旧)。CORS。StaticFilesマウント。ルーター登録。グローバル例外ハンドラ登録 | `app` | config, database, yolo_service, pipeline_service, 全routers |
| `config.py` | pydantic-settings による設定一元管理(5章) | `Settings`, `settings`(シングルトン) | .env |
| `database.py` | SQLAlchemy engine/SessionLocal/Base。SQLite固有設定(WAL, busy_timeout, check_same_thread)。`get_db`(FastAPI依存性)、`create_session`(BackgroundTasks用) | `engine`, `SessionLocal`, `Base`, `get_db()`, `create_session()`, `init_db()` | config |
| `models/clothing_item.py` | `ClothingItem` SQLAlchemyモデル(9.2節) | `ClothingItem` | database |
| `models/coordinate_log.py` | `CoordinateLog` SQLAlchemyモデル(9.3節) | `CoordinateLog` | database |
| `schemas/error.py` | 統一エラー応答 `ErrorResponse {detail, error_code, retryable}` | `ErrorResponse` | - |
| `schemas/item.py` | `UploadAcceptedResponse`, `ItemStatusResponse`, `ItemResponse`, `ItemListResponse`, `ItemUpdateRequest` | 同左 | - |
| `schemas/suggest.py` | `SuggestRequest`, `SuggestResponse`, `SuggestedItem` | 同左 | schemas/weather |
| `schemas/weather.py` | `WeatherInfo` | 同左 | - |
| `routers/upload.py` | `POST /api/upload`。7章の処理順序の実施。**BackgroundTasksディスパッチ(Celery移行時の唯一の差し替え点)** | router | image_validation_service, storage_service, pipeline_service, database |
| `routers/items.py` | `GET /api/items`, `GET /api/items/{id}`, `GET /api/items/{id}/status`(lazy stale検出込み), `PATCH /api/items/{id}`, `DELETE /api/items/{id}` | router | database, storage_service, pipeline_service(stale判定共通関数) |
| `routers/suggest.py` | `POST /api/suggest` | router | suggest_service, weather_resolution_service, database |
| `routers/weather.py` | `GET /api/weather` | router | weather_service |
| `routers/health.py` | `GET /api/health` | router | database, storage_service, config |
| `services/image_validation_service.py` | 拡張子/MIME/シグネチャ検証、実デコード、ピクセル数検証、EXIF補正、正規化、EXIF除去(7.4節) | `validate_and_normalize(tmp_path, declared_content_type, original_filename) -> NormalizedImage` | config, Pillow |
| `services/storage_service.py` | ディレクトリ初期化、tmp/正式保存、パス解決、URL変換、**共通削除関数(冪等)**、空き容量確認(10章) | `init_storage()`, `save_original()`, `save_pipeline_outputs()`, `delete_item_files()`, `delete_generated_files()`, `delete_tmp()`, `check_free_space()`, `to_public_url()` | config |
| `services/yolo_service.py` | ノートブック `segment_item()` の移植(8.2節) | `segment_item(model, image_path, conf) -> SegmentResult` | ultralytics, cv2, numpy |
| `services/llm_service.py` | ノートブック `extract_metadata_with_openai()` / `parse_json_safely()` の移植+strictスキーマ+リトライ(8.3節) | `extract_metadata(client, image_path) -> dict` | openai, prompts/metadata_prompt |
| `services/pipeline_service.py` | `run_pipeline_for_item(item_id)`(8.4節)。**AI同時実行ロック**(8.5節)。stale復旧関数(8.6節) | `run_pipeline_for_item(item_id)`, `recover_stale_processing(db)`, `mark_item_failed(db, item, reason)` | yolo_service, llm_service, storage_service, database |
| `services/weather_service.py` | OpenWeatherMap呼び出し。現在天気+予報(11.3節) | `get_current_weather(city) -> WeatherInfo \| None`, `get_forecast_weather(city, days_offset) -> WeatherInfo \| None` | httpx, config |
| `services/location_extraction_service.py` | request_textから場所・日付を抽出する軽量LLM呼び出し(リトライなし・fail-soft。11.3節) | `extract_location_date(client, request_text, today=None) -> LocationDateExtraction` | openai, prompts/location_prompt |
| `services/weather_resolution_service.py` | 場所・日付抽出→現在天気/予報の呼び分けを合成(11.3節) | `resolve_weather(request_text, explicit_city) -> WeatherInfo \| None` | location_extraction_service, weather_service |
| `services/suggest_service.py` | クローゼットJSON構築→LLM→item_ids検証→ログ記録(11章) | `create_suggestion(db, request_text, weather) -> SuggestResult` | openai, prompts/suggest_prompt, database |
| `prompts/metadata_prompt.py` | 属性抽出プロンプト定数+strict JSON Schema(付録B.1) | `METADATA_PROMPT`, `METADATA_JSON_SCHEMA` | - |
| `prompts/suggest_prompt.py` | コーデ提案プロンプト定数+strict JSON Schema(付録B.2) | `SUGGEST_SYSTEM_PROMPT`, `build_suggest_user_prompt()`, `SUGGEST_JSON_SCHEMA` | - |
| `prompts/location_prompt.py` | 場所・日付抽出プロンプト定数+strict JSON Schema(付録B.3) | `LOCATION_SYSTEM_PROMPT`, `build_location_user_prompt()`, `LOCATION_JSON_SCHEMA` | - |

## 4.3 backend/requirements.txt

ルートの `requirements.txt` は研究環境の pip freeze であり、**backendでは使用しない**。以下の最小構成を新設する(バージョンは実装時の最新安定版を固定する)。

```
fastapi
uvicorn[standard]
python-multipart
sqlalchemy>=2.0
pydantic-settings
openai
httpx
python-dotenv
ultralytics
opencv-python-headless
pillow
numpy
pytest
```

注意:
- `torch` は ultralytics の依存で入る。Dockerビルド時(ARM64)はCPU版を明示インストールする(15.2節)
- `opencv-python` ではなく **`opencv-python-headless`**(サーバーにGUI不要)

## 4.4 .gitignore への追加

既存 `.gitignore` に以下を追加する(既存の `*.pt` `dataset/` 等の除外は維持):

```
backend/storage/
backend/data/
backend/.env
deploy/.env
```

frontend側は create-next-app が生成する `.gitignore`(node_modules/.next等)をそのまま使う。

---

# 5. 設定管理

## 5.1 環境変数(.env)

`backend/.env` に配置(Git管理外)。`backend/.env.example` に空値の見本を置く(Git管理)。

| キー | 必須 | 説明 |
|---|---|---|
| `OPENAI_API_KEY` | ○ | OpenAI APIキー |
| `OPENWEATHER_API_KEY` | ○ | OpenWeatherMap APIキー(無料プラン) |
| `DEFAULT_CITY` | - | 天気取得の既定都市。既定値 `Morioka` |
| `DATABASE_URL` | - | 既定値 `sqlite:///./data/smartcloset.db`。PostgreSQL移行時に差し替え |

デプロイ用(`deploy/.env`、Git管理外。15.3節):

| キー | 説明 |
|---|---|
| `CADDY_BASIC_AUTH_USER` | Basic認証ユーザー名 |
| `CADDY_BASIC_AUTH_HASH` | `caddy hash-password` で生成した bcrypt ハッシュ。**平文パスワードはGitにも.envにも書かない** |
| `CADDY_DOMAIN` | 公開ドメインまたは `:443`(IP直の場合の内部TLS設定は15.4節) |

## 5.2 config.py 設定値一覧(初期値を確定)

`pydantic-settings` の `Settings` クラスで定義。環境変数で上書き可能。

| 設定名 | 初期値 | 用途 |
|---|---|---|
| `MODEL_PATH` | `../models/fashionpedia_9class_with_data_augmentation.pt`(backend/から見た相対。絶対パス指定可) | YOLO重み |
| `CONF_THRES` | `0.25` | YOLO信頼度閾値(PoC確定値) |
| `OPENAI_MODEL` | `gpt-5.4-nano` | 属性抽出・コーデ提案共通 |
| `OPENAI_MAX_RETRIES` | `2` | OpenAI呼び出しの最大リトライ回数(初回+2回) |
| `MAX_UPLOAD_SIZE_MB` | `10` | アップロード上限 |
| `UPLOAD_CHUNK_SIZE_BYTES` | `1048576`(1MB) | チャンク保存の単位 |
| `MAX_IMAGE_WIDTH` | `8000` | 画像幅上限(px) |
| `MAX_IMAGE_HEIGHT` | `8000` | 画像高さ上限(px) |
| `MAX_IMAGE_PIXELS` | `40000000`(4000万px) | 幅×高さ上限。`PIL.Image.MAX_IMAGE_PIXELS` にも設定 |
| `MAX_IMAGE_LONG_SIDE` | `1280` | AI推論前リサイズの長辺上限(8.4節) |
| `SQLITE_BUSY_TIMEOUT_MS` | `5000` | SQLite busy_timeout |
| `PROCESSING_STALE_MINUTES` | `10` | stale processing判定閾値 |
| `AI_MAX_CONCURRENCY` | `1` | AIパイプライン同時実行数(MVPは1固定) |
| `MIN_FREE_STORAGE_MB` | `500` | アップロード受付に必要な最小空き容量 |
| `BACKUP_RETENTION_COUNT` | `7` | バックアップ保持世代数(16章) |
| `STORAGE_DIR` | `./storage` | ストレージルート |
| `DATA_DIR` | `./data` | SQLite配置先 |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | 開発時のフロントエンドオリジン。本番はCaddy同一オリジン配信のため不要(15.3節) |

## 5.3 起動時チェック(lifespan)

`main.py` の lifespan で起動時に以下を順に実行する。

1. `init_storage()`: storage配下の5ディレクトリ(tmp/originals/transparent/masks/annotated)と data/ を作成
2. `init_db()`: `Base.metadata.create_all`
3. **モデル存在チェック**: `MODEL_PATH` が存在しなければ `RuntimeError` を送出し**起動失敗**させる(モデル無しで起動してアップロードを受け付ける事故を防ぐ)
4. YOLOモデルを1回だけロードし `app.state.yolo_model` に保持(タスク内での再ロード禁止)
5. OpenAIクライアントを生成し `app.state.openai_client` に保持
6. **stale processing復旧**: `recover_stale_processing()` を実行(8.6節)
7. tmpディレクトリ内の残存ファイルを全削除(前回異常終了の掃除)

---

# 6. バックエンドAPI詳細

## 6.1 エンドポイント一覧

| Method | Path | 概要 | 成功応答 | 非同期 |
|---|---|---|---|---|
| POST | `/api/upload` | 画像アップロード+AI処理起動 | 202(既存キー再送時は200/202) | ○ |
| GET | `/api/items/{item_id}/status` | AI処理ステータス(ポーリング用) | 200 | - |
| GET | `/api/items` | アイテム一覧(フィルタ+ページング) | 200 | - |
| GET | `/api/items/{item_id}` | アイテム詳細 | 200 | - |
| PATCH | `/api/items/{item_id}` | メタデータ手動補正 | 200 | - |
| DELETE | `/api/items/{item_id}` | アイテム削除(物理削除) | 204 | - |
| POST | `/api/suggest` | コーディネート提案 | 200 | - |
| GET | `/api/weather` | 天気情報取得(表示用プロキシ) | 200 | - |
| GET | `/api/health` | ヘルスチェック | 200 | - |
| GET(static) | `/images/originals/{filename}`, `/images/transparent/{filename}` | 画像配信(公開はこの2種のみ。10.3節) | 200 | - |

エラー応答は全エンドポイント共通で `ErrorResponse {detail, error_code, retryable}`(13章)。

## 6.2 POST /api/upload

### リクエスト

| 項目 | 型 | 必須 | 説明 |
|---|---|---|---|
| `file` | multipart File | ○ | JPEG または PNG |
| ヘッダー `Idempotency-Key` | string(UUID形式) | ○ | フロントエンドが送信前に生成(7.7節)。欠落時は 422 `validation_error` |

### 成功応答 202 Accepted(`UploadAcceptedResponse`)

```json
{ "item_id": "550e8400-e29b-41d4-a716-446655440000", "status": "processing" }
```

**202を返す条件(厳密)**: 7.3節の手順1〜15(検証・原画像正式保存・DB仮登録・原画像パスのDBコミット・BackgroundTasks登録)がすべて成功した後にのみ返す。1つでも失敗した場合は該当エラーを返し、補償処理(7.5節)で痕跡を残さない。

### Idempotency-Key 再送時の応答(7.7節)

| 既存レコードのstatus | 応答 |
|---|---|
| processing | 202 `{item_id, status: "processing"}`(新規レコードは作らない) |
| completed | 200 `{item_id, status: "completed"}` |
| failed | 200 `{item_id, status: "failed", failure_reason: "..."}` |
| 同一キー+異なる画像(SHA-256不一致) | 409 `idempotency_key_conflict` |

### エラー応答

| HTTP | error_code | retryable | 条件 |
|---|---|---|---|
| 413 | `file_too_large` | false | Content-Length超過、または実受信サイズが `MAX_UPLOAD_SIZE_MB` 超過 |
| 415 | `unsupported_media_type` | false | 拡張子・申告MIME・ファイルシグネチャがJPEG/PNG以外 |
| 400 | `invalid_image` | false | デコード不能、破損、寸法・ピクセル数超過、DecompressionBomb |
| 422 | `validation_error` | false | Idempotency-Key欠落・形式不正、fileパート欠落 |
| 409 | `idempotency_key_conflict` | false | 同一キー+異なる画像内容 |
| 503 | `insufficient_storage` | true | 空き容量不足(事前確認またはENOSPC) |
| 500 | `storage_error` | true | tmp書き込み・正式保存の失敗(容量以外) |
| 503 | `database_error` | true | DB仮登録・コミット失敗(ロック含む) |

## 6.3 GET /api/items/{item_id}/status

ポーリング用の軽量エンドポイント。**lazy stale検出**を行う: 対象が `processing` かつ `updated_at` が `PROCESSING_STALE_MINUTES` より古い場合、その場で failed(`processing_interrupted`)に更新してから返す(8.6節)。

応答 200(`ItemStatusResponse`):

```json
{ "item_id": "...", "status": "processing", "failure_reason": null }
```

| フィールド | 型 | 説明 |
|---|---|---|
| `item_id` | string | アイテムID |
| `status` | string | `processing` / `completed` / `failed` |
| `failure_reason` | string \| null | failedのときのみ。付録A.4のenum |

404 `item_not_found`。

## 6.4 GET /api/items

### クエリパラメータ

| パラメータ | 型 | 既定値 | 説明 |
|---|---|---|---|
| `category` | string | なし | 付録A.1のenumで完全一致 |
| `color` | string | なし | `color_primary` または `color_secondary` に部分一致 |
| `pattern` | string | なし | 付録A.2のenumで完全一致 |
| `material` | string | なし | 付録A.3のenumで完全一致 |
| `status` | string | なし | `processing` / `completed` / `failed`。未指定なら全status |
| `sort` | string | `created_at_desc` | `created_at_desc` / `created_at_asc` |
| `page` | int(≥1) | `1` | ページ番号 |
| `page_size` | int(1〜100) | `20` | 1ページ件数 |

### 応答 200(`ItemListResponse`)

```json
{ "items": [ItemResponse, ...], "total": 42, "page": 1, "page_size": 20 }
```

## 6.5 ItemResponse(共通スキーマ)

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | string | UUID |
| `status` | string | processing / completed / failed |
| `failure_reason` | string \| null | 付録A.4 |
| `category` | string \| null | 付録A.1 |
| `color_primary` | string \| null | 主色 |
| `color_secondary` | string \| null | 副色 |
| `pattern` | string \| null | 付録A.2 |
| `material` | string \| null | 付録A.3 |
| `silhouette` | string \| null | 自由記述(20文字程度) |
| `yolo_pred_class` | string \| null | YOLO代表クラス |
| `yolo_confidence` | number \| null | 代表クラスの信頼度 |
| `num_instances` | int \| null | 合成したインスタンス数 |
| `is_user_corrected` | boolean | PATCHによる手動補正済みか |
| `original_image_url` | string \| null | `/images/originals/{item_id}_original.{jpg\|png}` |
| `transparent_image_url` | string \| null | `/images/transparent/{item_id}_transparent.png`(completedのみ非null) |
| `original_filename` | string \| null | クライアント申告の元ファイル名(表示用。保存名には使わない) |
| `created_at` / `updated_at` | string(ISO 8601) | 登録・更新日時 |

**注意**: APIは内部ファイルパス(`original_image_path` 等)を返さない。`storage_service.to_public_url()` でURLに変換して返す。mask/annotated画像は内部デバッグ用でありAPIに公開しない。

## 6.6 PATCH /api/items/{item_id}

メタデータの手動補正。PoCの最終登録成功率64.5%(許容84.9%)を運用でカバーする中核機能。

### リクエスト(`ItemUpdateRequest`。全フィールド任意、指定されたものだけ更新)

| フィールド | 型 | 検証 |
|---|---|---|
| `category` | string | 付録A.1のenumのみ許可 |
| `color_primary` | string | 1〜30文字 |
| `color_secondary` | string \| null | null許可(nullで副色を消せる)、1〜30文字 |
| `pattern` | string | 付録A.2のenumのみ許可 |
| `material` | string | 付録A.3のenumのみ許可 |
| `silhouette` | string | 1〜50文字 |

### 処理

1. 対象が存在しなければ 404 `item_not_found`
2. 対象が `completed` 以外なら 409 `item_is_processing`(processingの場合)/ 409 `item_not_editable`(failedの場合。failedは編集でなく削除→再アップロードで対処)
3. 指定フィールドを更新し、`is_user_corrected = true`、`updated_at` を更新
4. 更新後の `ItemResponse` を返す(200)

enum違反は 422 `validation_error`。

## 6.7 DELETE /api/items/{item_id}

1. 対象が存在しなければ 404 `item_not_found`
2. 対象が `processing` なら **409 `item_is_processing`**(AI処理と削除の競合を避ける。MVPではキャンセル機能を持たない)
3. `completed` / `failed` の場合: `storage_service.delete_item_files(item_id)` で**原画像を含む関連ファイル全種を物理削除**(冪等。存在しないファイルは無視)→ DBレコード削除 → 204
4. ファイル削除で一部失敗してもDBレコード削除は続行し、失敗をログに記録する(孤児ファイルは再削除可能なため。10.4節)

## 6.8 POST /api/suggest

### リクエスト(`SuggestRequest`)

| フィールド | 型 | 必須 | 検証 |
|---|---|---|---|
| `request_text` | string | ○ | 1〜500文字。空白のみは422 |
| `city` | string \| null | - | **明示指定時のみ優先使用**。未指定なら`request_text`から場所を抽出し(11.3節)、抽出できなければ`DEFAULT_CITY` |
| `use_weather` | boolean | - | 既定 `true`。falseなら天気取得(場所・日付抽出含む)をスキップ |

### 応答 200(`SuggestResponse`)

| フィールド | 型 | 説明 |
|---|---|---|
| `suggestion_text` | string | 提案文(200字以内を指示。天気情報がある場合は自然に触れる) |
| `styling_reason` | string | 選定理由 |
| `items` | ItemResponse[] | 推奨アイテム(DB照合で有効なもののみ。全滅時は空配列) |
| `weather` | WeatherInfo \| null | 取得成功時のみ。`request_text`から近未来の日付が読み取れた場合は予報(`forecast_date`が設定される) |
| `weather_available` | boolean | 天気を提案に使えたか |
| `log_id` | string | coordinate_logs のID |

### エラー応答

| HTTP | error_code | retryable | 条件 |
|---|---|---|---|
| 400 | `no_completed_items` | false | completedのアイテムが0件(**LLMを呼ばずに返す**) |
| 422 | `validation_error` | false | request_text不正 |
| 503 | `service_unavailable` | true | LLM呼び出しがリトライ後も失敗 |

天気API失敗は**エラーにせず** `weather_available: false` で200を返す(11.3節)。

## 6.9 GET /api/weather

クエリ: `city`(任意。既定 `DEFAULT_CITY`)。常に**現在**の天気を返す(場所・日付抽出は行わない。11.3節の抽出・予報機能は`POST /api/suggest`専用)。

応答 200(`WeatherInfo`):

```json
{ "city": "Morioka", "temp": 24.3, "feels_like": 25.1, "description": "晴れ", "humidity": 60, "wind_speed": 3.2, "forecast_date": null }
```

取得失敗時は 503 `service_unavailable`(retryable: true)。

**注記**: フロントエンドは現在このエンドポイントを使用していない(旧`WeatherBadge`は廃止し、天気は`POST /api/suggest`の応答に統合。11.3節)。バックエンドAPIとしては独立してテスト済み・保守コストが低いため、手動確認用に維持する。

## 6.10 GET /api/health

```json
{
  "status": "ok",
  "model_loaded": true,
  "database_available": true,
  "storage_writable": true,
  "storage_free_mb": 12345
}
```

- `model_loaded`: `app.state.yolo_model` が非None
- `database_available`: `SELECT 1` 成功
- `storage_writable`: `storage/tmp/` へのテストファイル書き込み・削除成功
- `storage_free_mb`: `shutil.disk_usage(STORAGE_DIR)` の空きMB
- いずれかfalseなら `status: "degraded"` とし、HTTPは200のまま返す(監視側が本文で判定)
- **絶対パス等の内部情報は含めない**

# 7. 画像アップロード詳細設計

アップロード処理は「**①受付前検証** → **②原画像保存・DB仮登録** → **③BackgroundTasksによるAI処理**」の3段階に分ける。不正なファイルはDBへ仮登録せず、AI処理も開始しない。

## 7.1 3段階の責務

| 段階 | 実施場所 | 失敗時の扱い |
|---|---|---|
| ①受付前検証 | `routers/upload.py` + `image_validation_service.py`(同期、リクエスト内) | 即時エラー応答。DBレコード・ファイルを残さない |
| ②原画像保存・DB仮登録 | `routers/upload.py` + `storage_service.py`(同期、リクエスト内) | 補償処理でロールバック(7.5節)し、エラー応答 |
| ③AI処理 | `pipeline_service.run_pipeline_for_item(item_id)`(BackgroundTasks) | `failed` レコード+原画像を残す(7.6節)。202は既に返却済み |

## 7.2 検証ポリシー

- **クライアント申告のファイル名とMIMEタイプは信頼しない**。実データで検証する
- 許可形式は **JPEG と PNG のみ**
- 検証項目: 拡張子 → 申告MIME → **ファイルシグネチャ**(JPEG: 先頭 `FF D8 FF` / PNG: 先頭 `89 50 4E 47 0D 0A 1A 0A`)→ Pillow `Image.verify()` → **再オープンして実デコード**(`verify()` 後のImageオブジェクトは使用不可のため必ず再オープン)
- `PIL.Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS` を設定し、`DecompressionBombWarning` は `warnings.simplefilter("error", Image.DecompressionBombWarning)` で**エラーとして扱う**
- Pillowの制限とは別に、幅・高さ・幅×高さを独自に検証する(`MAX_IMAGE_WIDTH` / `MAX_IMAGE_HEIGHT` / `MAX_IMAGE_PIXELS`)
- **複数フレーム画像**(アニメーションPNG等。`getattr(img, "n_frames", 1) > 1`)は**先頭フレームのみ利用**する(`img.seek(0)` した内容を採用)
- JPEGのCMYK等はRGBへ変換する。PNGのアルファチャンネルは保持可能とする(RGBA維持)
- EXIF Orientationを `ImageOps.exif_transpose()` で補正する
- GPS情報を含むEXIF等の不要メタデータは、正式保存前に除去する(補正後のピクセルデータからEXIFを引き継がず再保存することで実現)

## 7.3 処理順序(17段階・固定)

`POST /api/upload` の実装は以下の順序を厳守する。各段階の失敗時挙動は7.5節。

| # | 処理 | 実施関数 | 失敗時 |
|---|---|---|---|
| 1 | リクエスト受付。Idempotency-Keyの存在・UUID形式検証。既存キー照合(7.7節) | `routers/upload.py` | 422 / 既存レコード応答 |
| 2 | **Content-Length事前確認**: ヘッダーが存在し `MAX_UPLOAD_SIZE_MB` 超なら即拒否(受信しない)。あわせて空き容量事前確認(7.8節) | `routers/upload.py` | 413 / 503 |
| 3 | `storage/tmp/` へ**チャンク単位の一時保存**(`UPLOAD_CHUNK_SIZE_BYTES` ごとに `await file.read(n)` ループ。一括 `await file.read()` は**禁止**)。書き込みながら累積受信サイズを計測し、SHA-256を逐次計算 | `storage_service.save_upload_to_tmp()` | 500 storage_error / 503 insufficient_storage |
| 4 | **実受信サイズの確認**: Content-Lengthは信用せず、実際に受信した累積サイズを基準とする。上限超過の時点で受信を中断し、tmpを削除して413 | 同上(ループ内) | 413 |
| 5 | 拡張子・申告MIME・ファイルシグネチャの検証(7.2節) | `image_validation_service` | 415 |
| 6 | `Image.verify()` → 再オープンして**実デコード** | 同上 | 400 invalid_image |
| 7 | 幅・高さ・総ピクセル数の検証 | 同上 | 400 invalid_image |
| 8 | EXIF Orientation補正 | 同上 | 400 invalid_image |
| 9 | RGB(JPEG)/RGBA可(PNG)への色空間正規化。複数フレームは先頭フレームのみ採用 | 同上 | 400 invalid_image |
| 10 | 不要なEXIF情報の除去(再エンコード) | 同上 | 400 invalid_image |
| 11 | `item_id` 生成(UUID4文字列) | `routers/upload.py` | - |
| 12 | DBへ `status=processing` のレコードを**仮登録**(idempotency_key・upload_sha256・original_filename含む。画像パスはまだNULL) | `routers/upload.py` | 503 database_error(tmp削除) |
| 13 | `item_id` に基づく名前で原画像を**正式保存**: `storage/originals/{item_id}_original.{jpg|png}`。**クライアントの元ファイル名は保存名に使用しない**(DBの `original_filename` 列にのみ記録) | `storage_service.save_original()` | 500 storage_error(レコード+ファイルをロールバック) |
| 14 | DBへ `original_image_path` を反映して**コミット** | `routers/upload.py` | 503 database_error(レコード+ファイルをロールバック) |
| 15 | **BackgroundTasksへ `item_id` のみを渡してAI処理を登録**(`background_tasks.add_task(run_pipeline_for_item, item_id)`)。ここがCelery移行時の唯一の差し替え点(8.7節) | `routers/upload.py` | 500 internal_error(ロールバック) |
| 16 | `202 Accepted` を返却 | FastAPI | - |
| 17 | 一時ファイルを **finally で削除**(成功・失敗にかかわらず必ず実行) | `storage_service.delete_tmp()` | 失敗はログのみ(起動時掃除5.3節が回収) |

補足:
- 手順3〜10でtmpファイルを対象に検証・正規化を行い、手順13では**検証・Orientation補正・色空間正規化・不要EXIF除去後の画像**を原画像として保存する(受信バイト列そのままではない)。JPEGは quality=95 で再エンコード、PNGはそのまま再保存
- 手順15の登録後にプロセスが停止した場合の実行保証はない。stale復旧(8.6節)で補償する

## 7.4 image_validation_service の仕様

```python
@dataclass
class NormalizedImage:
    image: PIL.Image.Image   # 検証・補正・正規化済み
    format: str              # "jpeg" | "png"
    width: int
    height: int

def validate_and_normalize(
    tmp_path: Path,
    declared_content_type: str | None,
    original_filename: str | None,
) -> NormalizedImage:
    """7.3節の手順5〜10を実施する。失敗時はValidationError系の独自例外を送出。
    例外はrouterで捕捉して13章のエラーコードへマッピングする。"""
```

独自例外: `UnsupportedMediaTypeError`(→415)、`InvalidImageError`(→400)。例外メッセージにはtmpの絶対パスを含めない。

## 7.5 補償処理(段階別ロールバック)

ファイル保存とSQLiteの間では単一トランザクションを張れないため、途中失敗時は以下の補償処理で整合性を回復する。

| 失敗箇所(7.3節の#) | 補償処理 |
|---|---|
| 1〜10(受付前検証) | DBレコード作成なし・ファイルを残さない(tmpは手順17のfinallyで削除) |
| 12(DB仮登録失敗) | tmpファイルを削除(finally)。それ以外の痕跡なし |
| 13(正式保存失敗) | **DBレコードを削除**+作成済みファイル(部分書き込み含む)を削除 |
| 14(パス反映コミット失敗) | DBレコードを削除(rollback+delete)+正式保存済み原画像を削除 |
| 15(BackgroundTasks登録失敗) | DBレコード削除+原画像削除(202を返していないため痕跡を残さない) |
| 202返却後のAI処理失敗 | 7.6節(原画像は残す) |

補償処理自体が失敗した場合(削除できない等)はエラーログに記録し、ユーザーへのエラー応答は元の失敗のものを返す。

## 7.6 ファイル保持方針(固定)

| 状況 | DBレコード | 原画像 | 透過/マスク/annotated | tmp |
|---|---|---|---|---|
| 受付前検証で失敗 | 作らない | 残さない | - | finallyで削除 |
| 仮登録〜202返却前に失敗 | 削除 | 削除 | - | finallyで削除 |
| 202後にAI処理失敗 | `failed` で残す | **残す**(再処理・原因確認用) | **不完全な生成物を削除** | finallyで削除済み |
| stale processing復旧 | `failed`(processing_interrupted) | 残す | 不完全な生成物を削除 | 起動時掃除 |
| ユーザーがDELETE(completed/failed) | 削除 | **物理削除** | 物理削除 | - |

## 7.7 Idempotency-Key による二重登録防止(MVPから実装)

### フロントエンド側

- 画像送信**開始前**に `crypto.randomUUID()` でキーを生成し、HTTPヘッダー `Idempotency-Key` として送信する
- **同じ画像の送信を再試行する場合は同じキー**を使う(202受信前に通信が切れた場合の再送を含む)
- **新しい画像を選択した場合は新しいキー**を生成する
- 202受信後は `item_id` を保持し(12.4節)、再送はしない

### バックエンド側

- `clothing_items.idempotency_key` に **UNIQUE制約**。受信画像のSHA-256を `upload_sha256` に保存
- 手順1で既存キーを照合し、ヒットした場合:
  - 受信内容のSHA-256が一致 → 新規レコードを作らず、既存の `item_id` と現在のstatusを返す(6.2節の表)
  - SHA-256が不一致(同一キーで異なる画像)→ **409 `idempotency_key_conflict`**
- 照合のためのSHA-256計算はtmp受信(手順3)完了後に確定するため、実装上は「キーがDBに存在 → tmp受信・ハッシュ計算 → 一致判定」の順とする(受信前にstatusだけで応答しない)
- UNIQUE制約違反(同時リクエストの競合)が発生した場合も既存レコード応答にフォールバックする
- 画像ハッシュによる**内容ベースの重複判定**(異なるキーで同じ画像)は将来拡張(18章)

## 7.8 ストレージ空き容量の確認

- `storage_service.check_free_space()`: `shutil.disk_usage(STORAGE_DIR)` で空きMBを取得
- **アップロード開始前**(手順2)に確認: 空き容量が `MIN_FREE_STORAGE_MB` 未満なら 503 `insufficient_storage`(retryable: true)。必要容量はアップロードファイルだけでなく原画像+透過+マスク+annotatedの生成を考慮した値として `MIN_FREE_STORAGE_MB=500` を設定している
- tmp保存中・正式保存時の `OSError`(`errno.ENOSPC`)を個別に捕捉 → 503 `insufficient_storage`。それ以外の書き込み失敗(権限エラー等)→ 500 `storage_error`。いずれも種別をログに記録する
- MVPでは507(Insufficient Storage)は使用せず**503に統一**する
- ヘルスチェックは `storage_writable` と `storage_free_mb` を返す(6.10節)

---

# 8. AIパイプライン サービス層設計

## 8.1 ノートブックからの移植対応表

移植元の正本: `ai_prototype/pipe-line/smartcloset_pipeline_functioned.ipynb`(参照は任意。本章のみで実装可能)。

| Notebook関数 | 移植先 | 変更点 |
|---|---|---|
| `segment_item()` | `services/yolo_service.py` | モデルをグローバルでなく引数で受ける(app.stateから渡す)。返り値をdataclass化 |
| `save_yolo_outputs()` | `services/storage_service.py` の `save_pipeline_outputs()` | 保存先を `storage/{masks,transparent,annotated}/`、命名を `{item_id}_{kind}.png` に変更。true_classプレフィックス廃止 |
| `extract_metadata_with_openai()` | `services/llm_service.py` の `extract_metadata()` | **strict JSON Schemaを正式指定**(8.3節)、リトライ追加、clientを引数で受ける |
| `parse_json_safely()` | `services/llm_service.py`(フォールバックとして残す) | 変更なし |
| `build_metadata_prompt()` | `prompts/metadata_prompt.py` の `METADATA_PROMPT` 定数 | 文言は付録B.1(ノートブック確定版と同一) |
| `process_one_image()` | `services/pipeline_service.py` の `run_pipeline_for_item()` | CSV保存廃止→DB保存。true_class引数廃止。事前リサイズ・ロック・Session管理追加(8.4節) |
| `run_pipeline()` / `collect_images_*()` / `show_pipeline_result()` | 移植しない(PoC/バッチ用) | - |

## 8.2 yolo_service.segment_item()

```python
@dataclass
class SegmentResult:
    rgba: np.ndarray | None      # 背景透過RGBA画像。失敗時None
    mask: np.ndarray | None      # 0-255マスク。失敗時None
    yolo_result: Any | None      # ultralyticsのResult。annotated生成に使用
    info: dict | None            # pred_class / confidence / num_instances / all_pred_classes / all_confidences
    status: str                  # "success" | "image_read_error" | "no_mask"

def segment_item(model: YOLO, image_path: Path, conf: float) -> SegmentResult:
```

処理ロジック(ノートブックと同一。変更禁止):

1. `cv2.imread()` で読み込み。失敗なら `status="image_read_error"`
2. BGR→RGB変換
3. `model.predict(source=str(image_path), conf=conf, save=False, verbose=False)`
4. `result.masks` がNoneまたは空なら `status="no_mask"`
5. **最も信頼度の高い検出を代表クラス**とする(`np.argmax(confs)`)
6. **代表クラスと同一クラスの全インスタンスのマスクを `np.maximum` で合成**(靴の左右が別インスタンスになる問題への対策)
7. 合成マスクを255階調化し、元画像サイズへ `cv2.resize`
8. RGBA化してアルファチャンネルにマスクを適用
9. `info` に `pred_class`(クラス名)/ `confidence`(float)/ `num_instances`(合成数)/ `all_pred_classes` / `all_confidences` を格納

クラス名はモデル内蔵の `model.names` を使用する(9クラス: 付録A.1と同一の英語名)。

## 8.3 llm_service.extract_metadata()

```python
def extract_metadata(client: OpenAI, image_path: Path) -> dict:
    """透過PNGをbase64で送り、6属性のdictを返す。
    OpenAI呼び出しはOPENAI_MAX_RETRIES回まで指数バックオフでリトライ。
    リトライ後も失敗した場合は LlmServiceError を送出。"""
```

- 画像をbase64化し、`chat.completions.create` に `messages=[{role:"user", content:[{type:"text",...},{type:"image_url", image_url:{url:"data:image/png;base64,..."}}]}]` で送信
- **response_format は必ず次の完全形式で指定する**(ノートブックの `{"type": "json_schema"}` はスキーマ本体が欠落しており不完全。本設計で修正する):

```python
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "clothing_metadata",
        "strict": True,
        "schema": METADATA_JSON_SCHEMA,   # 付録B.1の全文
    },
}
```

- スキーマで category / pattern / material をenum制約、color_secondary を `["string","null"]` にする(付録B.1)
- 応答テキストは `parse_json_safely()` を**フォールバック**として通す(strict指定が機能していれば素通り。コードブロック除去とキー補完)
- パース後もキー欠落・enum違反が残る場合は `LlmServiceError("json_parse_error")` として扱う
- **リトライ方針**: 接続エラー・5xx・レートリミット・JSON不正時に、1秒→2秒の指数バックオフで最大 `OPENAI_MAX_RETRIES`(=2)回リトライ。それでも失敗なら例外送出(呼び出し元で `failure_reason=llm_error` に変換)

## 8.4 pipeline_service.run_pipeline_for_item()

```python
def run_pipeline_for_item(item_id: str) -> None:
    """BackgroundTasksから呼ばれるAIパイプライン本体。同期関数(def)。
    引数はitem_id(str)のみ。例外はすべて内部で処理し、送出しない。"""
```

処理手順:

1. **ロック取得**(8.5節)。取得待ち開始・取得完了・待機時間をログに記録
2. `database.create_session()` で**新しいDB Sessionを生成**(APIリクエストのSessionと共有しない)
3. `item_id` でレコードをロード。存在しない、または `processing` でない場合は警告ログのみで終了(削除やstale復旧との競合)
4. **事前リサイズ**: 原画像の長辺が `MAX_IMAGE_LONG_SIDE`(1280)を超える場合、アスペクト比を維持して縮小した**推論用の一時コピー**を `storage/tmp/{item_id}_work.png` に作成(原画像は変更しない)。超えない場合は原画像をそのまま入力にする
5. `segment_item(model, work_path, settings.CONF_THRES)` を実行
   - `status != "success"` → 手順9の失敗処理へ(`failure_reason = image_read_error | no_mask`)。**no_maskは同じ入力で再実行しても改善しないため自動リトライしない**
6. `storage_service.save_pipeline_outputs(item_id, rgba, mask, yolo_result)` で保存:
   - `storage/masks/{item_id}_mask.png`
   - `storage/transparent/{item_id}_transparent.png`
   - `storage/annotated/{item_id}_annotated.png`(`yolo_result.plot()` をBGR→RGB変換して保存)
7. `extract_metadata(client, transparent_path)` を実行(リトライは8.3節)
   - 失敗 → 手順9へ(`failure_reason = llm_error`)
8. **成功時のDB更新**: category / color_primary / color_secondary / pattern / material / silhouette / yolo_pred_class / yolo_confidence / num_instances / 3つの生成画像パス / `status="completed"` / `updated_at` を更新してcommit
9. **失敗時の処理**(`mark_item_failed()`): `status="failed"`、`failure_reason` 設定、`updated_at` 更新、commit。**不完全な透過・マスク・annotated画像を削除**(`delete_generated_files(item_id)`)。**原画像は残す**。予期しない例外は `failure_reason="internal_error"` とし、スタックトレースをログに記録(DBには入れない)
10. **finally**: 推論用一時コピーを削除 → Sessionを必ずclose → ロックを必ず解放(with文で保証)

各段階(リサイズ/YOLO/保存/LLM/DB更新)の所要時間をINFOログに記録する。

## 8.5 AI推論の同時実行制御

uvicorn単一ワーカーでも、複数のBackgroundTasksはスレッドプールで並行実行されうる。YOLO推論の並行実行はメモリ・スレッド安全性の問題があるため、MVPでは**同時実行数を1に制限**する。

- `pipeline_service.py` のモジュールレベルに `_ai_semaphore = threading.BoundedSemaphore(settings.AI_MAX_CONCURRENCY)` を配置(管理場所はここに固定)
- `run_pipeline_for_item()` の先頭で `with _ai_semaphore:` により取得し、**例外発生時にも必ず解放**される構造にする
- ロック待機中のアイテムも `status=processing` のまま(ユーザーからは処理中に見える)
- ログ: 取得待ち開始 / 取得完了(待機時間) / 処理開始 / 処理終了を `item_id` 付きで記録
- YOLOモデル自体は lifespan で1回だけロードし(5.3節)、各タスクで再ロードしない
- Celery移行後はこのSemaphoreを廃止し、ワーカーの concurrency 設定に置き換える(責務を `pipeline_service` に閉じているため差し替えは局所的)

## 8.6 stale processing の検出と復旧

BackgroundTasksはプロセス停止(uvicorn停止・VM再起動・Docker再起動)でタスクが失われる。放置された `processing` レコードを以下の2経路で `failed` に補償する。

### (a) 起動時復旧(lifespan)

`recover_stale_processing(db)`:

1. `status="processing"` かつ `updated_at < now - PROCESSING_STALE_MINUTES` のレコードを検出
2. 各レコードについて: `status="failed"`、**`failure_reason="processing_interrupted"`**、`updated_at` 更新
3. 不完全な生成画像を削除(`delete_generated_files`)。**原画像は保持**
4. 対象の `item_id` と経過時間をWARNINGログに記録

### (b) lazy検出(status取得時)

`GET /api/items/{id}/status` で、対象が `processing` かつ閾値超過なら同じ復旧処理をその場で実行してから応答する(6.3節)。起動直後に閾値未満だったレコードもポーリング継続中にここで回収される。

### failure_reason の使い分け(厳守)

| failure_reason | 用途 |
|---|---|
| `processing_interrupted` | プロセス停止・VM再起動・Docker再起動・BackgroundTasks消失による**処理の中断**(stale復旧専用) |
| `internal_error` | アプリケーションコード内の**予期しない例外**に限定 |

ユーザー向け表示: `processing_interrupted` は「サーバーの再起動などにより処理が中断されました。もう一度アップロードしてください。」(12.6節)

## 8.7 Celery + Redis への移行パス

- 差し替え点は `routers/upload.py` の手順15(`background_tasks.add_task(run_pipeline_for_item, item_id)`)の**1箇所のみ**。ここを `run_pipeline_for_item.delay(item_id)` に変えるだけで移行できるよう、他の場所からBackgroundTasksを参照しない
- `run_pipeline_for_item(item_id)` は「文字列を1つ受け取り、内部でSessionを作り、例外を送出しない」設計のため、そのままCeleryタスク化できる
- 移行時に追加するもの: `celery_app.py`、Redisコンテナ、リトライ/タイムアウト設定、Semaphore廃止(8.5節)

# 9. データベース詳細設計

## 9.1 テーブル一覧

| テーブル | 役割 |
|---|---|
| `clothing_items` | 登録衣服のメタデータ・状態・画像パス |
| `coordinate_logs` | コーディネート提案の履歴(将来のパーソナライズに利用) |

マイグレーションは当面 `Base.metadata.create_all`(lifespanで実行)。PostgreSQL移行時にAlembicを導入する。SQLite方言依存のカラム型は使わない(JSONは TEXT に統一)。

## 9.2 clothing_items

DDL(SQLAlchemyモデルから生成される想定の等価定義):

```sql
CREATE TABLE clothing_items (
    id                      VARCHAR(36) PRIMARY KEY,          -- UUID4文字列
    user_id                 INTEGER     NOT NULL DEFAULT 1,
    status                  VARCHAR(20) NOT NULL DEFAULT 'processing',
                            -- 'processing' | 'completed' | 'failed'('complete'は使用禁止)
    failure_reason          VARCHAR(40),                      -- 付録A.4のenum。詳細例外はログへ(DBに入れない)
    category                VARCHAR(20),                      -- 付録A.1
    color_primary           VARCHAR(30),
    color_secondary         VARCHAR(30),                      -- 副色なしはNULL
    pattern                 VARCHAR(20),                      -- 付録A.2
    material                VARCHAR(20),                      -- 付録A.3
    silhouette              VARCHAR(50),
    yolo_pred_class         VARCHAR(20),
    yolo_confidence         REAL,
    num_instances           INTEGER,
    is_user_corrected       BOOLEAN     NOT NULL DEFAULT 0,
    idempotency_key         VARCHAR(36) NOT NULL UNIQUE,
    upload_sha256           VARCHAR(64) NOT NULL,
    original_image_path     TEXT,                             -- カラム名固定(4種)
    transparent_image_path  TEXT,
    mask_image_path         TEXT,
    annotated_image_path    TEXT,
    original_filename       TEXT,                             -- 表示用。保存名には使わない
    created_at              DATETIME    NOT NULL,             -- UTC
    updated_at              DATETIME    NOT NULL              -- UTC
);
CREATE INDEX ix_clothing_items_user_category ON clothing_items (user_id, category);
CREATE INDEX ix_clothing_items_user_status   ON clothing_items (user_id, status);
```

SQLAlchemyモデルの要点:

- `id = Column(String(36), primary_key=True)`(値はアプリ側で `str(uuid.uuid4())` を生成。DB側の自動採番・連番IDは使わない)
- `created_at` / `updated_at` は `datetime.now(timezone.utc)` をアプリ側で設定。更新時に `updated_at` を必ず更新する(stale判定の基準になるため、パイプライン処理の各コミットでも更新する)
- 画像パスカラムには **backend/ からの相対パス**(例 `storage/originals/xxx_original.jpg`)を保存する。絶対パスを保存しない(コンテナ/ホスト間の可搬性のため)

## 9.3 coordinate_logs

```sql
CREATE TABLE coordinate_logs (
    id                    VARCHAR(36) PRIMARY KEY,     -- UUID4
    user_id               INTEGER     NOT NULL DEFAULT 1,
    request_text          TEXT        NOT NULL,
    weather_json          TEXT,                        -- WeatherInfoのJSON文字列。取得失敗時NULL
    suggestion_text       TEXT        NOT NULL,
    styling_reason        TEXT,
    recommended_item_ids  TEXT        NOT NULL,        -- 検証後の有効IDのJSON配列文字列
    model_name            VARCHAR(50) NOT NULL,        -- 使用LLM名(OPENAI_MODEL)
    created_at            DATETIME    NOT NULL
);
```

## 9.4 SQLite固有設定(database.py に隔離)

APIリクエストとBackgroundTasksの両方からSQLiteを利用するため、以下を `database.py` に実装する。**SQLite固有処理はこのファイルの外に書かない**(PostgreSQL移行時の変更をここに閉じる)。

```python
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLiteのみ
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute(f"PRAGMA busy_timeout={settings.SQLITE_BUSY_TIMEOUT_MS}")  # 初期値5000ms
    cursor.close()
```

- `DATABASE_URL` が `sqlite` で始まる場合のみ `connect_args` / PRAGMA を適用する分岐を入れる

## 9.5 Session管理ルール(厳守)

1. **APIリクエスト**: FastAPI依存性 `get_db()`(yield方式)でリクエスト単位にSessionを生成・closeする
2. **BackgroundTasks**: `create_session()` でタスク内に新規Sessionを生成する。**APIリクエストのSessionと共有しない**
3. Sessionは処理単位で新規作成し、正常終了時は `commit`、例外時は `rollback`、**finallyで必ず `close`**
4. SQLAlchemyのモデルオブジェクト・SessionをBackgroundTasksへ直接渡さない(渡すのは `item_id` のみ)
5. **DBロックエラー**(`OperationalError: database is locked`。busy_timeout超過時に発生): APIでは 503 `database_error`(retryable: true)を返す。BackgroundTasks内では `failure_reason=internal_error` とし、いずれもWARNINGログに記録する

## 9.6 APIレスポンス・DB・ログの情報役割分担

| 保持場所 | 保持する情報 | 保持しない情報 |
|---|---|---|
| APIレスポンス | ユーザー向けメッセージ(`detail`)、機械可読コード(`error_code`, `failure_reason`)、公開URL | 内部例外メッセージ、絶対パス、APIキー、スタックトレース |
| DB | 構造化された状態(status / failure_reason の固定enum)、相対パス、メタデータ | 例外詳細、スタックトレース、生のLLM応答 |
| ログ | 例外詳細・スタックトレース・処理時間・ロック待機・削除記録(item_id付き) | APIキー等のシークレット(出力禁止) |

---

# 10. 画像ストレージ設計

## 10.1 ディレクトリ規約

| ディレクトリ | 内容 | 公開 |
|---|---|---|
| `backend/storage/tmp/` | アップロード一時ファイル(`{uuid}.upload`)、推論用一時コピー(`{item_id}_work.png`) | **非公開** |
| `backend/storage/originals/` | 原画像 `{item_id}_original.{jpg\|png}` | 公開(`/images/originals/`) |
| `backend/storage/transparent/` | 透過画像 `{item_id}_transparent.png` | 公開(`/images/transparent/`) |
| `backend/storage/masks/` | マスク `{item_id}_mask.png`(デバッグ用) | **非公開** |
| `backend/storage/annotated/` | YOLO可視化 `{item_id}_annotated.png`(デバッグ用) | **非公開** |
| `backend/data/` | `smartcloset.db`(SQLite) | **非公開** |

## 10.2 命名規則

- すべて `{item_id}_{kind}.{ext}` 形式。**クライアントの元ファイル名は使用しない**(パストラバーサル・文字化け・衝突の防止)
- kind: `original` / `transparent` / `mask` / `annotated` / `work`(tmp内のみ)

## 10.3 StaticFiles マウント(公開範囲の限定)

`main.py` で以下の**2ディレクトリのみ**をマウントする。`backend/storage/` 全体を公開してはならない。

```python
app.mount("/images/originals", StaticFiles(directory=settings.STORAGE_DIR / "originals"), name="originals")
app.mount("/images/transparent", StaticFiles(directory=settings.STORAGE_DIR / "transparent"), name="transparent")
```

`tmp/`・`masks/`・`annotated/`・SQLite DB・ログ・`.env` は公開対象外。

`storage_service.to_public_url(path)`: DBの相対パスを `/images/...` URLへ変換する(originals/transparent以外のパスを渡された場合はNoneを返す)。

## 10.4 ファイル削除の共通関数(冪等)

削除処理は複数箇所に重複実装せず、`storage_service.py` に集約する。

```python
def delete_item_files(item_id: str) -> None:
    """original / transparent / mask / annotated / work の全候補パスを削除する。
    存在しないファイルは無視(冪等)。個別の削除失敗はWARNINGログに記録し、例外を送出しない。"""

def delete_generated_files(item_id: str) -> None:
    """transparent / mask / annotated / work のみ削除(原画像は残す)。AI処理失敗・stale復旧用。冪等。"""

def delete_tmp(tmp_path: Path) -> None:
    """tmpファイル1件を削除。存在しなければ無視。"""
```

呼び出し元: DELETE API(delete_item_files)、パイプライン失敗(delete_generated_files)、stale復旧(delete_generated_files)、アップロードfinally(delete_tmp)、補償処理(7.5節)。

---

# 11. コーディネート提案機能詳細

## 11.1 処理フロー(routers/suggest.py + suggest_service.create_suggestion)

1. `status="completed"` のアイテムをDBから全件取得(processing / failed は**LLMに送らない**)。0件なら**LLM を呼ばずに** 400 `no_completed_items` を返す(routerで判定)
2. `use_weather=true` なら **`weather_resolution_service.resolve_weather(request_text, city)`** を呼ぶ(routerが呼ぶ。11.3節: 内部で場所・日付抽出→現在天気/予報の呼び分けを行う)。失敗時は `weather=None` として続行(**提案全体を失敗させない**)。`create_suggestion`自体はこの解決ロジックを知らず、解決済みの`weather`のみを受け取る(シグネチャ不変)
3. `suggest_service.create_suggestion(db, request_text, weather)` を呼ぶ。クローゼットJSONを構築: `[{"id", "category", "color_primary", "color_secondary", "pattern", "material", "silhouette"}, ...]`(**画像は送らない**。トークン量削減)
4. プロンプト(付録B.2)を組み立て、strict JSON Schema指定でLLM呼び出し。リトライは8.3節と同方針(最大2回・指数バックオフ)。それでも失敗なら 503 `service_unavailable`
5. **返却 `item_ids` をサーバー側で検証**: 手順1の取得結果に存在するIDのみ残し、存在しないIDは除外してWARNINGログに記録。**全IDが無効だった場合**は `items: []` のまま `suggestion_text` を返し(200)、WARNINGログに記録
6. `coordinate_logs` に記録(検証後の有効IDを保存。`weather_json`には`forecast_date`を含む`WeatherInfo`全体を保存)
7. `SuggestResponse` を返す

## 11.2 コーディネート構成ルール(プロンプトに明記。付録B.2)

- `item_ids` にはクローゼットJSONに存在するidのみを含める
- **dressを選ぶ場合はtopsとbottomsを同時に選ばない**
- **同一カテゴリからは原則最大1点**(bag / glasses / hat / watch等の小物は状況に応じて任意)
- 基本構成は「tops + bottoms」または「dress」。outer / shoes / 小物は天候・状況に応じて追加
- カテゴリが不足している場合(例: bottomsが1点もない)も、**不足を suggestion_text で伝えつつ最善の組み合わせを提案**する(エラーにしない)
- suggestion_text は200字以内、styling_reason は選定理由を簡潔に。日本語で出力

## 11.3 天気解決の仕様(weather_service / location_extraction_service / weather_resolution_service)

コーデ提案は「ユーザーの自由記述から場所・日付を読み取り、該当する天気を使う」ことを目的とする(例:「明日沖縄で」→翌日の沖縄の予報)。この解決は3つのモジュールに分割する。

### 11.3.1 weather_service(OpenWeatherMap呼び出し)

```python
def get_current_weather(city: str) -> WeatherInfo | None:
    """OpenWeatherMap Current Weather Data APIを呼ぶ。失敗時はNoneを返す(例外を送出しない)。"""

def get_forecast_weather(city: str, days_offset: int) -> WeatherInfo | None:
    """OpenWeatherMap 5 Day / 3 Hour Forecast APIを呼ぶ。失敗時はNoneを返す(例外を送出しない)。
    days_offsetは1〜5(0は呼び出し元がget_current_weatherを使うため対象外)。"""
```

- 現在天気エンドポイント: `https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&lang=ja&appid={OPENWEATHER_API_KEY}`
- 予報エンドポイント: `https://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&lang=ja&appid={OPENWEATHER_API_KEY}`(無料枠: 3時間刻み×5日分、最大40件のlistを返す)
- httpx同期クライアント、**タイムアウト5秒**、リトライなし
- 現在天気の抽出フィールド: `city`(name)、`temp`(main.temp)、`feels_like`(main.feels_like)、`description`(weather[0].description)、`humidity`(main.humidity)、`wind_speed`(wind.speed)。`forecast_date`は`None`
- 予報の対象日エントリ選定: レスポンス直下の`city.timezone`(UTC秒オフセット)で各エントリの`dt`(UTC unixtime)をローカル時刻に変換し、`(現在UTC時刻 + timezoneオフセット + days_offset日)`の日付と一致するエントリの中から**正午(12:00)に最も近いもの**を採用する(サーバーコンテナのTZ設定に依存させないため、必ずAPIレスポンスの`timezone`を基準にする)。該当日のエントリが1件もない場合は代用せず`None`を返す。採用エントリの日付を`forecast_date`(ISO 8601、例: `"2026-08-08"`)に設定する
- 失敗条件(タイムアウト・非200・パース失敗・キー未設定・対象日エントリなし)ではWARNINGログを記録してNoneを返す
- `GET /api/weather` ではNone時に 503 `service_unavailable` を返す(6.9節、現在天気のみ使用)。`POST /api/suggest` ではNone時に `weather_available: false` で続行する

### 11.3.2 location_extraction_service(場所・日付抽出)

```python
def extract_location_date(client, request_text: str, today: date | None = None) -> LocationDateExtraction:
    """request_textから場所(city)・日付(days_offset)をLLMで抽出する。
    リトライは行わない(1回勝負)。失敗時は例外を送出せずLocationDateExtraction(None, None)を返す。"""
```

- 付録B.3のプロンプト・strict JSON Schemaを使用。`city`はOpenWeatherMap互換の英語都市名(例:「沖縄」→`"Naha,JP"`)、`days_offset`は`0`(今日/未指定)〜`5`(5日後)、または`6`(**6日以上先・過去日・不明瞭な日付を表す明示的センチネル**)
- 「本日の日付」はサーバーコンテナのTZ設定に依存させないよう、`zoneinfo.ZoneInfo("Asia/Tokyo")`で計算する
- **リトライを行わない**(`llm_service.extract_metadata`や`suggest_service`の指数バックオフとは異なる方針)。理由: 天気解決のためのベストエフォートなヒント抽出であり、失敗しても「地名なし」として扱われるだけで提案全体の品質に致命的影響を与えないため、リトライの数秒コストに見合わない
- 失敗条件(clientがNone・OpenAI API呼び出し失敗・JSON parse失敗・スキーマ不一致)ではINFOログを記録し`LocationDateExtraction(city=None, days_offset=None)`を返す

### 11.3.3 weather_resolution_service(合成・呼び分け)

```python
def resolve_weather(request_text: str, explicit_city: str | None) -> WeatherInfo | None:
    """extract_location_date → get_current_weather/get_forecast_weather の呼び分けを合成する。"""
```

- `city = explicit_city or extraction.city or settings.DEFAULT_CITY`(SuggestRequest.cityで明示指定があれば最優先)
- `days_offset = extraction.days_offset or 0`
- `days_offset == 0` → `get_current_weather(city)`
- `1 <= days_offset <= 5` → `get_forecast_weather(city, days_offset)`
- `days_offset == 6`(センチネル) → 天気取得自体を行わず`None`を返す(不正確な情報を出すより誠実)
- `routers/suggest.py`はこの関数のみを呼び、`create_suggestion`には解決済みの`WeatherInfo | None`を渡す(`create_suggestion`のシグネチャ・内部ロジックは本節の変更による影響を受けない)

## 11.4 異常系一覧

| 状況 | 挙動 |
|---|---|
| completedアイテム0件 | LLMを呼ばず 400 `no_completed_items` |
| processing / failed のアイテム | クローゼットJSONに含めない |
| カテゴリ不足 | エラーにせずLLMが不足を明示した提案を返す(11.2節) |
| 天気API失敗 | `weather_available: false` で続行。weather_jsonはNULLでログ記録 |
| 場所・日付抽出の失敗 | `DEFAULT_CITY`+現在天気にフォールバック(抽出失敗≒地名なしとして扱う) |
| 抽出された日付が6日以上先・不明瞭 | 天気取得自体をスキップし`weather_available: false` |
| LLMが存在しないitem_idを返す | サーバー側で除外(WARNINGログ) |
| LLMの全item_idが無効 | `items: []` で `suggestion_text` のみ返す(200) |
| LLM呼び出し失敗(リトライ後) | 503 `service_unavailable`(retryable: true)。coordinate_logsには記録しない |
| request_text が空・501文字以上 | 422 `validation_error` |

---

# 12. フロントエンド詳細設計

## 12.1 画面一覧(App Router)

| 画面 | パス | 主な機能 |
|---|---|---|
| クローゼット一覧 | `/` | アイテムグリッド(透過PNG)、フィルタ(category/color/pattern/material)、ページング、failed/processingバッジ、詳細への導線 |
| 衣服登録 | `/upload` | 画像選択(ファイル選択+ドラッグ&ドロップ)、プレビュー、アップロード、処理中ポーリング、結果表示 |
| アイテム詳細 | `/items/[id]` | 原画像/透過画像の切替表示、メタデータ表示・編集(PATCH)、削除 |
| コーデ提案 | `/suggest` | 要望入力、提案結果を吹き出しチャット風に表示(天気は提案文に自然に統合)+推奨アイテムカード |

## 12.2 コンポーネント一覧

| コンポーネント | 配置画面 | 役割 |
|---|---|---|
| `Header` | 全画面(`app/layout.tsx`) | アプリ名+クローゼット/衣服を登録/コーデ提案への導線(4画面はこれ以外に相互リンクを持たないため必須) |
| `UploadDropzone` | /upload | ファイル選択・ドラッグ&ドロップ・形式/サイズのクライアント事前チェック |
| `ImagePreview` | /upload | 選択画像のプレビュー(任意でCanvas縮小。12.7節) |
| `ProcessingStatus` | /upload | 状態機械(12.3節)に応じたスピナー・メッセージ・再試行ボタン |
| `ItemCard` | /(一覧), /suggest | 透過PNGサムネイル+category/colorタグ。status≠completedはバッジ表示 |
| `ItemGrid` | / | ItemCardの一覧+ページング |
| `FilterBar` | / | category/color/pattern/materialフィルタ |
| `MetadataEditForm` | /items/[id] | 6属性の編集フォーム(enumはセレクトボックス)→PATCH |
| `SuggestForm` | /suggest | 要望テキスト入力+送信(送信中は無効化) |
| `SuggestionResult` | /suggest | suggestion_text / styling_reasonを吹き出しチャット風(アバターアイコン+吹き出し)に表示。天気が使えなかった場合のみ「※天気情報は考慮されていません」を吹き出し内に表示。推奨アイテムは吹き出し下にグリッド表示 |

共通モジュール:

- `lib/api.ts`: fetchラッパー。ベースURLはクライアント側(ブラウザ)とサーバー側(Next.js Server Component/Route Handler)で別々に決定する。**サーバー側の`fetch`は相対URLを解決できない**ため、`typeof window === "undefined"`でサーバー実行を判定し、サーバー側は`INTERNAL_API_BASE_URL`(Docker内部ネットワーク。本番: `http://backend:8000`、`NEXT_PUBLIC_`を付けずクライアントバンドルに含めない)、クライアント側は`NEXT_PUBLIC_API_BASE_URL`(開発: `http://localhost:8000`、本番: 空文字=同一オリジン、Caddy経由)を使う。エラー時は `ErrorResponse` をパースして型付きで返す
- `lib/types.ts`: `ItemResponse` / `ItemListResponse` / `SuggestResponse` / `WeatherInfo` / `ErrorResponse` 等をバックエンドスキーマ(6章)と1:1で定義

## 12.3 アップロード状態機械(9状態)

| 状態 | 意味 | 表示・可能操作 |
|---|---|---|
| `idle` | 初期状態 | Dropzoneのみ表示 |
| `validating` | クライアント事前チェック中(形式・サイズ) | - |
| `uploading` | POST /api/upload 送信中 | プログレス表示。**送信ボタン無効化(二重送信防止)** |
| `accepted` | 202受信。item_id保存済み | 「アップロード完了。AIが解析中...」 |
| `processing` | ポーリング中(status=processing) | スピナー+「AIが解析中...」 |
| `completed` | status=completed | 抽出結果プレビュー+「クローゼットを見る」「続けて登録」導線 |
| `upload_failed` | 202受信**前**の失敗(4xx/5xx/ネットワークエラー) | エラーメッセージ+「再試行」(**同じIdempotency-Keyで再送**) |
| `processing_failed` | 202受信**後**のAI処理失敗(status=failed) | failure_reason別メッセージ(12.6節)+「別の写真でやり直す」(**新しいキーで新規アップロード**) |
| `polling_timeout` | ポーリングが60秒経過 | 「処理に時間がかかっています。処理は継続中の可能性があります」+「クローゼットで確認」導線 |

遷移:

```
idle → validating → uploading → accepted → processing → completed
         │(不正)        │(失敗)                │(status=failed)   
         ▼              ▼                     ▼               
     upload_failed  upload_failed      processing_failed      
                                        │(60秒経過)            
                    processing ────────► polling_timeout       
```

- `validating` での不正(JPEG/PNG以外、10MB超)はサーバーに送信せず `upload_failed` にする(サーバー側検証の先取り。最終防衛はサーバー)
- 再試行方法は失敗段階で分ける: **受付前失敗=同一キーで再送 / AI処理失敗=新しい画像・新しいキーで新規アップロード**(no_maskは同じ画像を再送しても改善しないため)

## 12.4 通信切断への対応

| 切断タイミング | フロントエンドの挙動 |
|---|---|
| **202受信前**に切断 | `upload_failed` にし、「再試行」で**同じIdempotency-Keyのまま再送**する。サーバー側で受信済みなら既存item_idが返る(7.7節)ため二重登録されない |
| **202受信後**に切断 | 202受信時点で `localStorage` のキー `smartcloset_pending_upload` に `{item_id, idempotency_key, saved_at}` を保存しておく。再接続・再訪問時にこの値があれば**ポーリングを再開**する(completed/failed確認後にキーを削除) |

## 12.5 ポーリング仕様

- `GET /api/items/{item_id}/status` を **2秒間隔**、**最大60秒**(30回)
- 60秒経過で `polling_timeout` へ遷移する。これは**UI上の監視終了であり、AI処理失敗ではない**。サーバー側のアイテムstatusは変更しない(サーバー側の保険はstale復旧8.6節)
- タブ非アクティブ時の重複タイマーを避けるため、ポーリングは単一の `setInterval` で管理し、遷移時に必ず `clearInterval` する

## 12.6 failure_reason別のユーザー向けメッセージ

| failure_reason | 表示文言 |
|---|---|
| `image_read_error` | 「画像を読み込めませんでした。別の写真をお試しください。」 |
| `no_mask` | 「衣服を検出できませんでした。衣服がはっきり写った写真をお試しください。」 |
| `llm_error` | 「AI解析に失敗しました。しばらく待ってから再度アップロードしてください。」 |
| `processing_interrupted` | 「サーバーの再起動などにより処理が中断されました。もう一度アップロードしてください。」 |
| `internal_error` | 「処理に失敗しました。もう一度アップロードしてください。」 |

## 12.7 クライアント側画像縮小(任意最適化)

- 旧設計の「640×640固定リサイズ」は**廃止**(2.3節)
- 転送量削減のための任意最適化として、長辺が1280pxを超える場合のみCanvas APIでアスペクト比を維持して縮小し、JPEG品質0.85で再エンコードして送信**してよい**(PNGで透過が必要なケースは考えにくいがPNG入力はそのまま送ってもよい)
- この最適化の有無にかかわらず、サーバー側の検証・リサイズ(7章・8.4節)が正であり、クライアント処理はスキップ可能

# 13. エラーハンドリング・ロギング詳細設計

## 13.1 統一エラー応答

すべてのエラーは以下の形式で返す(`schemas/error.py`)。

```json
{ "detail": "ユーザー向けメッセージ(日本語)", "error_code": "invalid_image", "retryable": false }
```

- `detail`: ユーザーにそのまま表示できる日本語文
- `error_code`: 機械可読な固定enum(13.2節)
- `retryable`: 同じ操作を時間をおいて再試行する価値があるか

FastAPIの `HTTPException` はグローバル例外ハンドラでこの形式に変換する。Pydanticの422バリデーションエラーも `error_code=validation_error` に統一する。ハンドルされない例外は 500 `internal_error`(retryable: true)とし、スタックトレースはログのみに記録する。

## 13.2 エラーコード一覧(全体)

| error_code | HTTP | retryable | 発生箇所 | detail(表示文言) |
|---|---|---|---|---|
| `file_too_large` | 413 | false | upload | 10MB以下の画像をご利用ください。 |
| `unsupported_media_type` | 415 | false | upload | JPEG/PNG形式のみ対応しています。 |
| `invalid_image` | 400 | false | upload | 画像を読み込めませんでした。別のファイルをお試しください。 |
| `validation_error` | 422 | false | 全API | 入力内容を確認してください。 |
| `idempotency_key_conflict` | 409 | false | upload | 別の画像が同じリクエストキーで送信されました。ページを更新して再度お試しください。 |
| `item_not_found` | 404 | false | items系 | アイテムが見つかりません。 |
| `item_is_processing` | 409 | true | items(DELETE/PATCH) | AI処理中のため操作できません。処理完了後にお試しください。 |
| `item_not_editable` | 409 | false | items(PATCH) | 処理に失敗したアイテムは編集できません。削除して再登録してください。 |
| `no_completed_items` | 400 | false | suggest | クローゼットに登録済みの衣服がありません。先に衣服を登録してください。 |
| `insufficient_storage` | 503 | true | upload | サーバーの空き容量が不足しています。しばらく待ってから再度お試しください。 |
| `storage_error` | 500 | true | upload | 画像の保存に失敗しました。再度お試しください。 |
| `database_error` | 503 | true | 全API | サーバーが混み合っています。しばらく待ってから再度お試しください。 |
| `service_unavailable` | 503 | true | suggest / weather | 提案の生成に失敗しました。しばらく待ってから再度お試しください。 |
| `internal_error` | 500 | true | 全API | サーバーエラーが発生しました。再度お試しください。 |

## 13.3 リトライ方針一覧

| 対象 | リトライ | 備考 |
|---|---|---|
| OpenAI API(属性抽出・コーデ提案) | **最大2回、指数バックオフ(1秒→2秒)** | 接続エラー・5xx・レートリミット・JSON不正が対象(8.3節) |
| YOLO `no_mask` | **自動リトライしない** | 同じ入力で再実行しても改善しないため。ユーザーに別写真を促す |
| 天気API | リトライなし | 失敗即フォールバック(11.3節) |
| SQLiteロック | busy_timeout(5000ms)内の自動待機のみ | 超過時は503 |
| AI処理失敗アイテムの再実行 | MVPではなし | `POST /api/items/{id}/retry` は将来拡張(18章) |

## 13.4 機密情報の取り扱い(厳守)

- **APIレスポンスに含めない**: 内部の例外メッセージ、APIキー、絶対パス、ファイルシステム構造、スタックトレース、SQLエラー詳細
- **ログに含めない**: `OPENAI_API_KEY` / `OPENWEATHER_API_KEY` 等のシークレット(誤って例外メッセージに混入しないよう、外部APIクライアント初期化エラーはメッセージを固定文字列に差し替えて記録する)
- `.env` はGit管理外。`.env.example` に実値を書かない

## 13.5 ロギング設計

- 標準 `logging` を使用。フォーマット: `%(asctime)s %(levelname)s %(name)s %(message)s`。ロガー名はモジュール単位(`app.services.pipeline` 等)
- 出力先: stdout(Docker運用でそのまま `docker logs` に乗る)
- 必須ログ項目:

| タイミング | レベル | 内容 |
|---|---|---|
| アップロード受付/完了 | INFO | item_id, 受信サイズ, 所要時間 |
| 検証失敗 | INFO | error_code(ファイル名・パスは記録しない。item_id未発番のためリクエストIDは不要・MVP) |
| パイプライン各段階 | INFO | item_id, 段階名(resize/yolo/save/llm/db), 所要時間 |
| ロック取得 | INFO | item_id, 待機時間 |
| LLMリトライ | WARNING | item_id, 試行回数, 失敗種別 |
| AI処理失敗 | ERROR | item_id, failure_reason, スタックトレース |
| stale復旧 | WARNING | item_id, 経過時間 |
| ファイル削除失敗 | WARNING | item_id, 種別 |
| DBロック | WARNING | 発生箇所 |
| 無効なLLM item_id除外 | WARNING | 除外したID |

---

# 14. テスト計画

## 14.1 バックエンド(pytest)

### 構成

- `tests/conftest.py`: 一時ディレクトリのSQLite+storageを使う `TestClient` フィクスチャ(設定を環境変数で上書き)。OpenAI・天気は `monkeypatch` でモック。**TestClientはBackgroundTasksをレスポンス返却後に同期実行するため、アップロード→即status確認でパイプライン完了まで検証できる**
- YOLO実推論を伴うテストは `@pytest.mark.yolo` を付け、通常実行では `-m "not yolo"` で除外可能にする(CI/高速実行用)。モデル重みが無い環境では自動スキップ
- `tests/fixtures/` に配置するもの:
  - 実画像3枚: `tops.jpg`(衣服単品)、`shoes.jpg`(左右2インスタンス)、`no_clothing.jpg`(風景等。no_mask誘発用)
  - 不正ファイル: `fake.jpg`(中身がテキスト)、`broken.png`(途中で切れたPNG)、`huge_pixels.png`(小容量・超高解像度。Pillowで生成スクリプト化してもよい)

### テスト観点一覧(todo.mdのタスクと1:1対応)

| 分類 | 観点 |
|---|---|
| upload正常系 | JPEG/PNGアップロード→202→(モックLLM)→completed→6属性・透過PNG生成・URL返却 |
| upload異常系 | 不正拡張子(415)/ MIME不一致・偽装jpg(415)/ 壊れた画像(400)/ 10MB超過(413)/ ピクセル数超過(400)/ Idempotency-Key欠落(422) |
| 補償処理 | tmp保存失敗(500+痕跡なし)/ DB仮登録失敗(tmp削除)/ 正式保存失敗(レコード・ファイルなし)/ tmpのfinally削除 |
| 容量 | 空き容量不足時503(check_free_spaceをモック)/ ENOSPC捕捉 |
| Idempotency | 同一キー再送(processing/completed/failed各status)/ 同一キー異内容409 / UNIQUE競合フォールバック |
| パイプライン | no_mask→failed(リトライなし)/ LLM失敗→2回リトライ→llm_error / LLM JSON不正→parse_json_safelyフォールバック / 失敗時の生成物削除+原画像保持 |
| stale復旧 | 起動時復旧(古いprocessing→processing_interrupted+生成物削除)/ lazy検出(status取得時) |
| items | 一覧フィルタ・ページング / 詳細 / PATCH(enum違反422、is_user_corrected、processing409、failed409)/ DELETE(processing409、completed/failedの物理削除確認) |
| suggest | 正常系(モックLLM)/ completed0件で400・LLM未呼び出し / 無効item_id除外 / 全ID無効で items:[] / 天気失敗フォールバック / LLM失敗503 |
| weather | 正常系(モック)/ タイムアウト・非200でNone |
| health | 正常 / モデル未ロード時のdegraded |
| セキュリティ | エラーレスポンスに絶対パス・スタックトレースが含まれない / StaticFilesでtmp・masks・DBにアクセスできない(404) |

## 14.2 フロントエンド

- `tsc --noEmit` の通過を必須とする
- 主要ロジック(状態機械の遷移、api.tsのエラーパース)は可能な範囲でVitest等の単体テスト(MVPでは必須としない。手動E2Eで代替可)

## 14.3 手動E2Eチェックリスト(Phase 5・6で実施)

1. 衣服写真をアップロード→処理中表示→完了→クローゼットに透過画像が表示される
2. 衣服が写っていない写真→「衣服を検出できませんでした」表示
3. 詳細画面でcategoryを修正→一覧に反映・is_user_corrected確認
4. アイテム削除→一覧から消え、storageのファイルも消える
5. 要望を入力してコーデ提案→提案文+推奨アイテムのハイライト表示
6. 機内モード等で通信を切断して再送→二重登録されない
7. アップロード直後にbackendを再起動→アイテムがfailed(中断)表示になる
8. スマホブラウザで1〜5を確認(本番URL・Basic認証経由)

---

# 15. デプロイ設計(Oracle Cloud・¥0運用)

## 15.1 構成

- **Oracle Cloud Always Free** の `VM.Standard.A1.Flex`(Ampere ARM、推奨: 4 OCPU / 24GB RAM / ブートボリューム100GB程度)1台に全コンポーネントを同居
- Docker Compose でサービス3つ: `caddy` / `frontend` / `backend`
- **外部公開はCaddyのみ**(80/443)。`frontend:3000` / `backend:8000` はDocker内部ネットワーク限定とし、ホストへのポートpublishをしない
- SQLite(`backend/data/`)・画像(`backend/storage/`)・モデル重み(`models/`)はホストのディスクにボリュームマウントして永続化
- 全サービス `restart: unless-stopped` + `systemctl enable docker` により **VM再起動後に自動復旧**
- **ネットワーク(VCN/サブネット/セキュリティリスト)とコンピュートインスタンスはTerraformでコード管理**(`deploy/terraform/`)。OCIコンソールでの手動クリック操作による設定ミス・再現性の欠如を避ける(15.6節)

## 15.2 Dockerfile 方針

### backend/Dockerfile

- ベース: `python:3.12-slim`(ARM64対応)
- **torchはCPU版を明示インストール**(ARM64): `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` を requirements より先に実行(ultralyticsが重いCUDA版を引かないようにする)
- `opencv-python-headless` 前提のため追加のシステムライブラリは最小(`libgl1` 不要。`libglib2.0-0` が必要になった場合のみ追加)
- 起動: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1`(**単一ワーカー厳守**。8.5節の排他制御の前提)
- モデル重みはイメージに含めず、`/app/../models` 相当へ read-only ボリュームマウント(起動時チェックで欠落を検出して起動失敗: 5.3節)

### frontend/Dockerfile

- `next.config.js` で `output: "standalone"` を設定し、multi-stageビルド(`node:20-slim`)で `node server.js` を起動
- `NEXT_PUBLIC_API_BASE_URL` は空文字(同一オリジン。Caddyが `/api` と `/images` をbackendへルーティング)。ビルド時にDockerfileで固定
- `INTERNAL_API_BASE_URL`(`http://backend:8000`)は実行時にdocker-compose経由で注入(12.2節)。Server ComponentのSSR fetchはCaddyを経由しないため必須

## 15.3 Caddy 設定

`deploy/Caddyfile`(環境変数は `deploy/.env` から compose 経由で注入):

```
{$CADDY_DOMAIN} {
    basic_auth {
        {$CADDY_BASIC_AUTH_USER} {$CADDY_BASIC_AUTH_HASH}
    }
    request_body {
        max_size 12MB
    }
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle /images/* {
        reverse_proxy backend:8000
    }
    handle {
        reverse_proxy frontend:3000
    }
}
```

- **Basic認証を全パスに適用**(シングルユーザーの公開URLのため必須)。ハッシュは `docker run --rm caddy caddy hash-password --plaintext '<パスワード>'` で生成し、`deploy/.env`(Git管理外)に保存。**平文パスワードはGitにもファイルにも残さない**
- `request_body max_size 12MB`: Caddy側のサイズ上限。**FastAPI側の上限(7.3節)と二重に設ける**(Caddyの制限だけに依存しない)
- 同一オリジン配信のため本番ではCORS設定は不要(開発時のみ `CORS_ORIGINS` を使用)

## 15.4 ドメインとHTTPS

- 推奨: 無料のDuckDNS等でサブドメインを取得し `CADDY_DOMAIN` に設定 → Caddyが Let's Encrypt で自動HTTPS
- ドメインを用意しない場合: `CADDY_DOMAIN=:443` + `tls internal`(自己署名)で暫定運用できるが、スマホでの証明書警告を許容する必要がある。**推奨は無料DNS利用**

## 15.5 docker-compose.yml 要点

```yaml
services:
  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    env_file: .env
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
    restart: unless-stopped
  backend:
    build: ../backend
    env_file: ../backend/.env
    volumes:
      - ../backend/data:/app/data
      - ../backend/storage:/app/storage
      - ../models:/models:ro        # MODEL_PATH=/models/fashionpedia_9class_with_data_augmentation.pt
    restart: unless-stopped
    # ports: 記述しない(内部ネットワークのみ)
  frontend:
    build: ../frontend
    environment:
      INTERNAL_API_BASE_URL: http://backend:8000
    restart: unless-stopped
volumes:
  caddy_data:
```

**注意(bcryptハッシュと`.env`)**: `CADDY_BASIC_AUTH_HASH`はbcryptハッシュ(`$2a$14$...`)で`$`を含むため、docker composeの`.env`自動読み込みが`$X`を変数参照として展開しようとし値が壊れる。`deploy/.env`では`$`を`$$`にエスケープして記述する(`caddy hash-password`の出力をそのまま貼らない)

## 15.6 VMセットアップ手順

Oracle Cloudアカウント作成(クレカ登録必要・Always Free枠内は課金なし)のみ手動で行い、**それ以降のインフラ(VCN・パブリックサブネット・インターネットゲートウェイ・ルートテーブル・セキュリティリスト・A1.Flexコンピュートインスタンス)はTerraformで作成する**。

### 15.6.1 事前準備(手動・アカウントにつき一度だけ)

1. Oracle Cloudアカウント作成
2. OCIコンソール右上のプロフィールアイコン → **My Profile → API keys → Add API key** で「Generate API Key Pair」を選び、公開鍵をアップロード。表示される秘密鍵をダウンロードしてローカルの安全な場所(例: `~/.oci/oci_api_key.pem`。**Git管理外**)に保存する(コンピュートインスタンスへのSSHログイン用鍵とは別物)
3. 同画面に表示される「Configuration file preview」から `tenancy` OCID・`user` OCID・`fingerprint`・`region` を控える
4. VMへのSSHログイン用鍵(`ssh-keygen -t ed25519`等で新規作成、または既存の公開鍵)を用意し、公開鍵のパスを控える

### 15.6.2 Terraform構成(`deploy/terraform/`)

- **管理対象**: VCN、パブリックサブネット、インターネットゲートウェイ、ルートテーブル、セキュリティリスト(ingress: 22は`var.ssh_allowed_cidr`限定・80/443は全公開、egress: 全許可)、`VM.Standard.A1.Flex`コンピュートインスタンス(Ubuntu、cloud-initで`docker.io`・`docker-compose-v2`・`sqlite3`(16章のバックアップスクリプトが使用)を自動インストールし`docker`グループに追加)
- **VM内ファイアウォール(iptables)の注意**: OracleのUbuntuイメージは`netfilter-persistent`が起動時に`/etc/iptables/rules.v4`を読み込み、**デフォルトでSSH(22)以外の新規接続を`REJECT`する**(OCIセキュリティリストで80/443を許可していてもVM内で二重に塞がれる)。cloud-initの`runcmd`で80/443のACCEPTルールを追加し`netfilter-persistent save`で永続化する
- **ファイル構成**: `versions.tf`(OCI providerバージョン固定)、`main.tf`(プロバイダ・各リソース定義)、`variables.tf`、`outputs.tf`(`instance_public_ip`)、`cloud-init.yaml`、`terraform.tfvars.example`(キー名のみ)
- **state管理**: ローカルstate(`terraform.tfstate`)。シングルユーザー運用のためリモートバックエンドは導入しない。`terraform.tfvars`・`terraform.tfstate*`・`.terraform/`は**Git管理外**(OCIDそのものは秘密情報ではないが、実運用値・stateをリポジトリで追跡しない方針に統一する)

### 15.6.3 適用手順

1. `cd deploy/terraform && cp terraform.tfvars.example terraform.tfvars` → 15.6.1で控えた値・SSH公開鍵パス・ホームリージョン(`ap-osaka-1`)を記入
2. `terraform init`
3. `terraform plan` でVCN・サブネット・セキュリティリスト・インスタンスの作成計画を確認
4. `terraform apply`(**A1.Flexの確保に失敗する場合**=Out of Capacity: `instance_ocpus`/`instance_memory_gbs`変数を減らす、または時間を変えて再度`terraform apply`。作成済みのVCN等はそのまま再利用される)
5. `terraform output instance_public_ip` でパブリックIPを取得 → `ssh -i <SSH秘密鍵> ubuntu@<IP>` で疎通確認(cloud-init完了後は`docker --version`・`docker compose version`が通る。完了まで数分かかる場合がある)

### 15.6.4 アプリのデプロイ(Terraform適用後、VM上で実施)

1. `git clone`(HTTPS)+ **モデル重みをscp転送**(`models/fashionpedia_9class_with_data_augmentation.pt`。Git管理外のため)
2. `backend/.env`・`deploy/.env` を作成(APIキー・Basic認証ハッシュ)
3. `cd deploy && docker compose up -d --build`
4. `GET /api/health` で `model_loaded: true` を確認 → スマホからE2E確認(14.3節)
5. DNS(DuckDNS等)で`CADDY_DOMAIN`のサブドメインを`terraform output instance_public_ip`のIPへ向ける

## 15.7 コスト内訳

| 項目 | 費用 |
|---|---|
| Oracle Cloud A1.Flex(Always Free枠内) | ¥0 |
| Caddy / Let's Encrypt / DuckDNS | ¥0 |
| OpenWeatherMap(無料プラン: 60calls/min) | ¥0 |
| OpenAI API(gpt-5.4-nano) | **従量課金のみ**(登録1件+提案1回あたり数円未満想定) |

---

# 16. バックアップ・復元設計

SQLite DBと画像ストレージは対応関係を持つため、**同一時点のスナップショット**として取得する。

## 16.1 バックアップ手順(MVP: 手動。scripts/backup.sh)

1. **書き込み停止**: `docker compose stop backend`(アップロード・編集・削除を止め、DBとファイルの整合時点を作る)
2. DBバックアップ: `sudo sqlite3 backend/data/smartcloset.db ".backup '{BACKUP_DIR}/smartcloset_backup_{TS}.db'"`(SQLiteのバックアップAPIを使用。単純な `cp` はWALと不整合の恐れがあるため使わない。`backend/data`はbackendコンテナ=root実行が作成するためroot所有であり、書き込みに`sudo`が必要)
3. 画像アーカイブ: `tar czf {BACKUP_DIR}/smartcloset_backup_{TS}.tar.gz --exclude=storage/tmp -C backend storage`(`--exclude`はGNU tarでは位置引数より前に置く必要がある)
4. `docker compose start backend`
5. 世代整理: `BACKUP_RETENTION_COUNT`(=7)世代を超える古いバックアップを削除

- `{TS}` は `date +%Y%m%d_%H%M%S`。**DBと画像アーカイブに同一の日時識別子を付ける**(命名規則: `smartcloset_backup_{YYYYMMDD_HHMMSS}.db` / `.tar.gz`)
- `BACKUP_DIR` は `~/smartcloset_backups/`(VMホスト上)

## 16.2 復元手順(scripts/restore.sh)

1. `docker compose stop backend`
2. 現行の `backend/data/smartcloset.db` と `backend/storage/` を退避(上書き前にrename)
3. バックアップDBを `backend/data/smartcloset.db` に配置、tarを `backend/storage/` に展開
4. `docker compose start backend`
5. **整合性検証**: DB内の全 `original_image_path` / `transparent_image_path` について実ファイルの存在を確認するスクリプトを実行し、欠損があれば一覧表示する(restore.sh内のPythonワンライナーまたは検証関数)

## 16.3 制約と将来方針

- **Known Limitation: 同一VM内のバックアップはVM消失(リージョン障害・アカウント問題)に対応できない**。将来は Oracle Object Storage(Always Free: 20GB)への外部退避を検討する
- 将来の自動化: `scripts/backup.sh` をそのままVMのcron(例: 毎日4時)に登録する。スクリプト配置場所は `scripts/` に固定し、cron化時も同スクリプトを呼ぶ

# 17. 実装フェーズ計画・Git運用

## 17.1 フェーズ一覧

タスクの詳細(タスクID・変更対象・検証コマンド・完了条件)は `docs/todo.md` が正本。ここでは全体像のみ定義する。

| Phase | ブランチ | 実装範囲 | Phase完了条件(要約) |
|---|---|---|---|
| 0 | `phase/0-backend-foundation` | backend雛形・config・database・storage_service基盤・lifespan・health | `uvicorn app.main:app` 起動、`curl /api/health` が `model_loaded:true`、pytest green |
| 1 | `phase/1-upload-pipeline` | アップロード17段階・検証・補償・Idempotency・容量確認・パイプライン移植・stale復旧・status API・画像配信。**異常系タスク込みで完了** | fixture画像upload→completed→6属性+透過PNG。異常系テスト全通過 |
| 2 | `phase/2-items-crud` | items一覧/詳細/PATCH/DELETE | pytest全通過(409・物理削除含む) |
| 3 | `phase/3-suggest` | weather_service・suggest・coordinate_logs | 天気あり/フォールバック両系で提案が返る。異常系テスト全通過 |
| 4 | `phase/4-frontend` | Next.js 4画面・状態機械・ポーリング・二重送信防止・切断対応 | ブラウザE2E(登録→閲覧→編集→提案)成功、tsc通過 |
| 5 | `phase/5-hardening` | グローバル例外ハンドラ最終化・ログ・機密非漏洩監査・README | 手動E2Eチェックリスト(14.3節1〜7)全消化 |
| 6 | `phase/6-deploy` | Dockerfile×2・compose・Caddy・VMセットアップ・バックアップスクリプト | 公開URLでスマホからE2E成功(14.3節8) |

## 17.2 Git運用ルール(厳守)

- **mainブランチへの直接実装は行わない**。Phaseごとに `phase/N-...` ブランチを作成する
- 小さな論理単位ごとにcommitする。1タスク=1commitに固定しなくてよい(相互依存する小タスクは1つの論理commitにまとめてよい)が、**Phaseをまたぐ変更を同一commitに含めない**
- 各commit前: 対象テストを実行 → `git diff` / `git diff --cached` を確認
- 各Phase完了時: 全テスト実行 → セルフレビュータスク(todo.md)消化 → GitHubへpush → mainへmerge
- **force push禁止。`--force-with-lease` も使用しない**
- push前確認: `.env`・APIキー・認証情報・SQLite DB・画像・ログ・モデル重み・大容量ファイルが含まれていないこと(`git status` と `git diff --stat origin/main` で確認)
- コミットメッセージは **Conventional Commits** 形式:

```text
feat(upload): add validated image upload flow
fix(storage): clean files after persistence failure
feat(pipeline): recover interrupted processing records
test(upload): cover invalid image and storage failures
docs(design): define upload compensation workflow
```

- **commit・push・mergeはユーザーの明示的な指示があった場合のみ実行する**(Claude Codeが自動で行わない)

---

# 18. 将来拡張・実装上の注意

## 18.1 将来拡張と移行パス

| 拡張 | 移行パス | 優先度 |
|---|---|---|
| Celery + Redis | `routers/upload.py` のディスパッチ1箇所を差し替え(8.7節)。Semaphore廃止 | 中 |
| PostgreSQL | `DATABASE_URL` 差し替え+Alembic導入。SQLite固有処理は database.py に隔離済み(9.4節) | 中 |
| S3/Object Storage | storage_service にStorageBackend抽象を導入して差し替え(10章) | 中 |
| マルチユーザー化 | user_id列は全テーブルに存在。認証(セッション/JWT)とuser_idフィルタの追加のみ | 低 |
| `POST /api/items/{id}/retry` | failedアイテムの原画像(保持済み: 7.6節)から再パイプライン実行 | 中 |
| 画像ハッシュによる内容ベース重複判定 | upload_sha256列は保存済み。同一ユーザー内の同一ハッシュ検出を追加 | 低 |
| Geolocationによる天気取得 | `/api/weather` にlat/lonパラメータ追加 | 低 |
| webp入力対応 | image_validation_serviceのシグネチャ・デコード対応追加 | 低 |
| MLOpsモニタリング | 下記18.2 | 高 |

## 18.2 MLOpsモニタリング構想

デプロイ後もドメイン変化により推論精度は低下しうる。以下をSQLで定点観測し、`docs/evaluation.md` の基準で定期再評価する。

- `yolo_confidence` の分布(低下傾向=ドメインずれの兆候)
- `no_mask` 率(`failure_reason='no_mask'` の割合)
- `llm_error` 率
- `is_user_corrected` 率(高い=LLM抽出の実運用精度が低い)
- ユーザー補正データ(PATCH前後の差分)を再学習用データとして蓄積 → YOLO/プロンプトの改善サイクルへ

## 18.3 実装上の注意(既知の落とし穴)

1. ノートブックの `response_format={"type": "json_schema"}` は**スキーマ本体が欠落した不完全な指定**。必ず付録Bの完全形式で実装する(8.3節)
2. ルート `requirements.txt` は研究環境のfreezeで `google-generativeai` 等が残存。**backendでは backend/requirements.txt のみ使用**
3. `.gitignore` に `backend/storage/` `backend/data/` `backend/.env` `deploy/.env` を追加(4.4節)。既存の `Claude.md` 表記は実ファイル `CLAUDE.md` と大文字小文字が不一致(必要なら修正)
4. status値は `completed`。旧設計・PoC CSVの `complete` と混同しない
5. YOLOのKnown Issues(watchベルト欠損・shoesマスク欠損・bagショルダー混入)はMVPでは**PATCHによる手動補正**で運用カバーする。モデル改善は18.2のサイクルで対応
6. uvicornは必ず `--workers 1`。複数ワーカーにするとモデル多重ロード・Semaphoreが機能しない(8.5節)
7. テストで実YOLOを使う場合はモデル重みが必要。重みが無い環境では `@pytest.mark.yolo` を自動スキップ(14.1節)

---

# 付録A. enum定義一覧(正本)

`docs/prompt_design.md` と同値。変更時は prompt_design.md を先に更新し、本付録・`prompts/*.py`・フロントエンドのセレクトボックスを同期させる。

## A.1 category(9種)

`outer` / `tops` / `bottoms` / `dress` / `shoes` / `bag` / `hat` / `watch` / `glasses`

| category | 対象 |
|---|---|
| outer | コート、ジャケット、ブルゾン、カーディガンなど羽織る衣服 |
| tops | Tシャツ、シャツ、ブラウス、パーカー、ニットなど上半身のみの衣服 |
| bottoms | パンツ、スカート、ショートパンツなど下半身のみの衣服 |
| dress | ワンピース、ドレス、つなぎ、ジャンプスーツ、オールインワン、オーバーオールなど上下が一体となった衣服 |
| shoes | スニーカー、革靴、ブーツ、サンダル |
| bag | ハンドバッグ、ショルダーバッグ、リュック |
| hat | キャップ、ハット、ニット帽 |
| watch | 腕時計 |
| glasses | メガネ、サングラス |

YOLOモデルのクラス名(`model.names`)もこの9種と同一。

## A.2 pattern(10種)

`無地` / `ストライプ` / `ボーダー` / `チェック` / `ドット` / `花柄` / `ロゴ` / `プリント` / `カモフラ` / `その他`

## A.3 material(13種)

`コットン` / `デニム` / `ニット` / `レザー` / `ナイロン` / `フリース` / `ウール` / `スウェット` / `ファー` / `ボア` / `金属` / `樹脂` / `その他`

※ materialは実素材ではなく「画像から推定される最も代表的な素材」。

## A.4 status / failure_reason / error_code

- **status**: `processing` / `completed` / `failed`(`complete` は使用禁止)
- **failure_reason**: `image_read_error` / `no_mask` / `llm_error` / `internal_error` / `processing_interrupted`(使い分けは8.6節)
- **error_code**: 13.2節の表が正本
- **フロントエンド状態**: `idle` / `validating` / `uploading` / `accepted` / `processing` / `completed` / `upload_failed` / `processing_failed` / `polling_timeout`(12.3節)

---

# 付録B. プロンプト全文・JSON Schema(正本)

プロンプトのコード上の正本は `backend/app/prompts/` に置く。本付録と一致させる。

## B.1 属性抽出(metadata_prompt.py)

### METADATA_PROMPT(ノートブック確定版と同一。dress定義の明確化済み)

```text
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
```

### METADATA_JSON_SCHEMA(strict。response_formatに完全形式で渡す)

```python
METADATA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["outer", "tops", "bottoms", "dress", "shoes",
                     "bag", "hat", "watch", "glasses"],
        },
        "color_primary": {"type": "string"},
        "color_secondary": {"type": ["string", "null"]},
        "pattern": {
            "type": "string",
            "enum": ["無地", "ストライプ", "ボーダー", "チェック", "ドット",
                     "花柄", "ロゴ", "プリント", "カモフラ", "その他"],
        },
        "material": {
            "type": "string",
            "enum": ["コットン", "デニム", "ニット", "レザー", "ナイロン",
                     "フリース", "ウール", "スウェット", "ファー", "ボア",
                     "金属", "樹脂", "その他"],
        },
        "silhouette": {"type": "string"},
    },
    "required": ["category", "color_primary", "color_secondary",
                 "pattern", "material", "silhouette"],
    "additionalProperties": False,
}
```

### API呼び出し形式

```python
response = client.chat.completions.create(
    model=settings.OPENAI_MODEL,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": METADATA_PROMPT},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
        ],
    }],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "clothing_metadata",
            "strict": True,
            "schema": METADATA_JSON_SCHEMA,
        },
    },
)
```

## B.2 コーディネート提案(suggest_prompt.py)

### SUGGEST_SYSTEM_PROMPT

```text
あなたはプロのファッションスタイリストです。
ユーザーのクローゼットに実際にある衣服の中から、天気とユーザーの要望に最適な
コーディネートを提案してください。クローゼットにない衣服を提案してはいけません。
```

### ユーザープロンプトテンプレート(build_suggest_user_prompt)

```text
# 天気情報
{weather_block}

# ユーザーの要望
{request_text}

# クローゼット(JSON)
{closet_json}

# ルール
- item_ids には上記クローゼットJSONに存在する id のみを含める
- dress を選ぶ場合は tops と bottoms を同時に選ばない
- 同一カテゴリからは原則1点まで(bag, hat, watch, glasses などの小物は状況に応じて任意)
- 基本構成は「tops + bottoms」または「dress」。outer や shoes、小物は天候・状況に応じて加える
- 該当するアイテムが乏しい場合も、その旨を suggestion_text で伝えつつ最善の組み合わせを提案する
- 天気情報がある場合は、天気に触れながら提案理由を自然に述べる(例:「明日は28℃予想なので涼しい素材を選びました」)
- suggestion_text は200字以内の提案文、styling_reason は選定理由を簡潔に書く
- 日本語で出力する
```

- `{weather_block}` 取得成功時(現在天気。`forecast_date`なし):

```text
都市: {city} / 気温: {temp}°C / 体感: {feels_like}°C / 天候: {description} / 湿度: {humidity}%
```

- `{weather_block}` 取得成功時(予報。`forecast_date`あり。日付は日本語表現に変換して付加):

```text
都市: {city} / 気温: {temp}°C / 体感: {feels_like}°C / 天候: {description} / 湿度: {humidity}% / 日付: {forecast_dateを"8月8日"形式に変換}
```

- `{weather_block}` 取得失敗時(または use_weather=false):

```text
天気情報なし(天気を考慮せずに提案してください)
```

- `{closet_json}`: completedアイテムの `[{"id","category","color_primary","color_secondary","pattern","material","silhouette"}, ...]` を `json.dumps(..., ensure_ascii=False)` した文字列

### SUGGEST_JSON_SCHEMA(strict)

```python
SUGGEST_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "item_ids": {"type": "array", "items": {"type": "string"}},
        "suggestion_text": {"type": "string"},
        "styling_reason": {"type": "string"},
    },
    "required": ["item_ids", "suggestion_text", "styling_reason"],
    "additionalProperties": False,
}
```

response_format は B.1 と同じ完全形式(`name: "coordinate_suggestion"`)で渡す。

## B.3 場所・日付抽出(location_prompt.py)

11.3.2節: コーデ提案の`request_text`から天気取得用の場所・日付を抽出する軽量LLM呼び出し。**リトライを行わない**(11.3.2節参照)。

### LOCATION_SYSTEM_PROMPT

```text
あなたはユーザーの文章から、天気を調べるために必要な「場所」と「日付」だけを
抽出するアシスタントです。コーディネートの提案は行わず、場所と日付の抽出のみを行ってください。
```

### ユーザープロンプトテンプレート(build_location_user_prompt)

```text
# 本日の日付
{today}({weekday})

# ユーザーの文章
{request_text}

# 指示
- 文章中に具体的な地名(市区町村・都道府県・国等)があれば city に設定する
- city は OpenWeatherMap で検索可能な英語表記にする
  (例: 沖縄/那覇→"Naha,JP"、東京→"Tokyo,JP"、大阪→"Osaka,JP"、北海道/札幌→"Sapporo,JP")
- 地名が明示されていなければ city は null にする
- 文章中の日付表現(今日、明日、明後日、○月○日、来週の月曜日 等)を本日の日付を基準に判断し、
  本日からの経過日数を days_offset に設定する(今日または日付指定なしは0、明日は1、明後日は2、
  というように最大5まで)
- 6日以上先の日付、または過去の日付・不明瞭な日付の場合は days_offset を6にする
```

- `{today}`: `zoneinfo.ZoneInfo("Asia/Tokyo")`基準の本日の日付(ISO 8601)。`{weekday}`: 日本語の曜日1文字(月〜日)

### LOCATION_JSON_SCHEMA(strict)

```python
LOCATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": ["string", "null"]},
        "days_offset": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5, 6]},
    },
    "required": ["city", "days_offset"],
    "additionalProperties": False,
}
```

response_format は B.1/B.2 と同じ完全形式(`name: "location_date_extraction"`)で渡す。`days_offset`は`minimum`/`maximum`ではなく`enum`で範囲を表現する(strict構造化出力は数値範囲キーワードを保証しないため。METADATA_JSON_SCHEMAと同じ方針)。

---

# 付録C. 状態遷移リファレンス

## C.1 アイテムstatus遷移(サーバー側)

```
                     (アップロード手順12)
                            │
                            ▼
                       processing ──────────────► completed
                            │        AI処理成功        │
                            │                         │ PATCH(手動補正)
              ┌─────────────┼──────────────┐          ▼
   AI処理失敗  │   stale復旧(起動時/lazy)   │      completed(is_user_corrected=true)
              ▼             ▼              │
        failed          failed             │
   (image_read_error/ (processing_         │
    no_mask/llm_error/  interrupted)       │
    internal_error)                        │
              │             │              │
              └──────► DELETE(物理削除) ◄───┘
                     ※processing中のDELETEは409
```

- `failed → processing` の再実行(retry)はMVPには無い(将来拡張18.1節)
- 202返却前の失敗はレコード自体が存在しない(7.5節)

## C.2 アップロードUI状態遷移(フロントエンド9状態)

12.3節の表・遷移図が正本。

## C.3 本書内の相互参照マップ

| 知りたいこと | 参照 |
|---|---|
| 設定値の初期値 | 5.2節 |
| アップロードの処理順序 | 7.3節 |
| 補償処理・ファイル保持 | 7.5〜7.6節 |
| Idempotency-Key | 7.7節 |
| パイプライン処理手順 | 8.4節 |
| stale復旧 | 8.6節 |
| DDL | 9.2〜9.3節 |
| エラーコード全表 | 13.2節 |
| テスト観点一覧 | 14.1節 |
| デプロイ手順 | 15.6節 |
| バックアップ手順 | 16.1節 |
| コーデ提案の天気解決(場所・日付抽出) | 11.3節 |
| enum正本 | 付録A |
| プロンプト正本 | 付録B |

---

(以上 / SmartCloset AI 設計書最終版 ver 2.0)





