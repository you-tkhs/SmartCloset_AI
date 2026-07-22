"""design.md 10.3節・13.4節: 静的ファイル公開範囲の限定と機密情報非漏洩の検証(T1-9・T5-1)。

to_public_url()の変換ロジック自体のテストはtest_services.pyに既存のため、
本ファイルではマウント範囲(公開ディレクトリの限定)とエラー応答・ログの非漏洩監査を扱う。
"""

import logging
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from openai import AuthenticationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from starlette.routing import Mount

import app.database as database_module
import app.main as main_module
import app.routers.items as items_module
from app.config import settings
from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.services import llm_service, suggest_service
from app.services.llm_service import LlmServiceError, extract_metadata

FIXTURES_DIR = Path(__file__).parent / "fixtures"
_DUMMY_API_KEY = "sk-test-DUMMYSECRETVALUE1234567890abcdef"


def test_only_originals_and_transparent_are_mounted():
    mount_paths = {route.path for route in main_module.app.routes if isinstance(route, Mount)}
    assert mount_paths == {"/images/originals", "/images/transparent"}


def test_tmp_directory_is_not_publicly_served(client):
    storage_dir = Path(settings.STORAGE_DIR)
    (storage_dir / "tmp").mkdir(parents=True, exist_ok=True)
    (storage_dir / "tmp" / "leak.txt").write_bytes(b"secret")

    response = client.get("/images/tmp/leak.txt")

    assert response.status_code == 404


def test_masks_directory_is_not_publicly_served(client):
    storage_dir = Path(settings.STORAGE_DIR)
    (storage_dir / "masks").mkdir(parents=True, exist_ok=True)
    (storage_dir / "masks" / "leak.png").write_bytes(b"secret")

    response = client.get("/images/masks/leak.png")

    assert response.status_code == 404


def test_annotated_directory_is_not_publicly_served(client):
    storage_dir = Path(settings.STORAGE_DIR)
    (storage_dir / "annotated").mkdir(parents=True, exist_ok=True)
    (storage_dir / "annotated" / "leak.png").write_bytes(b"secret")

    response = client.get("/images/annotated/leak.png")

    assert response.status_code == 404


def test_static_mount_rejects_path_traversal_outside_its_directory(tmp_path):
    """design.md 10.3節のマウント方式(StaticFiles(directory=...))が、
    originals外(例: dataディレクトリのDBファイル)へのトラバーサルを拒否することを確認する。"""
    storage_dir = tmp_path / "storage"
    (storage_dir / "originals").mkdir(parents=True)
    (storage_dir / "data").mkdir(parents=True)
    (storage_dir / "data" / "smartcloset.db").write_bytes(b"sqlite-secret")
    (storage_dir / "originals" / "ok.jpg").write_bytes(b"fake-jpeg")

    test_app = FastAPI()
    test_app.mount(
        "/images/originals", StaticFiles(directory=storage_dir / "originals"), name="originals"
    )

    with TestClient(test_app) as test_client:
        ok_response = test_client.get("/images/originals/ok.jpg")
        assert ok_response.status_code == 200

        traversal_response = test_client.get("/images/originals/..%2Fdata%2Fsmartcloset.db")
        assert traversal_response.status_code == 404


def test_upload_error_response_excludes_absolute_path_and_stack_trace(client):
    response = client.post(
        "/api/upload",
        files={"file": ("broken.png", (FIXTURES_DIR / "broken.png").read_bytes(), "image/png")},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    assert response.status_code == 400
    body = response.text
    assert settings.STORAGE_DIR not in body
    assert "Traceback" not in body


def _create_item(**overrides) -> str:
    item_id = overrides.pop("id", str(uuid.uuid4()))
    defaults = {
        "id": item_id,
        "status": "completed",
        "idempotency_key": str(uuid.uuid4()),
        "upload_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
    }
    defaults.update(overrides)

    db = database_module.SessionLocal()
    db.add(ClothingItem(**defaults))
    db.commit()
    db.close()
    return item_id


def _override_get_db_failing_commit():
    def _override():
        db = database_module.SessionLocal()
        real_commit = db.commit

        def _commit():
            db.commit = real_commit
            raise SQLAlchemyError("simulated commit failure")

        db.commit = _commit
        try:
            yield db
        finally:
            db.close()

    return _override


def test_all_error_responses_exclude_absolute_path_and_stack_trace(client, monkeypatch):
    """design.md 13.2節・13.4節: 13.2節の全error_codeのうち、レスポンス本文が生成される
    異常系(internal_errorはtest_unhandled_exception_...で別途検証)を横断的に監査する。"""
    item_id = _create_item()

    responses: list[tuple[str, "httpx.Response"]] = []

    responses.append(
        (
            "unsupported_media_type",
            client.post(
                "/api/upload",
                files={"file": ("evil.exe", b"not an image", "application/octet-stream")},
                headers={"Idempotency-Key": str(uuid.uuid4())},
            ),
        )
    )
    responses.append(("validation_error(missing idempotency key)", client.post("/api/upload", files={"file": ("a.jpg", b"x", "image/jpeg")})))
    responses.append(("item_not_found(GET)", client.get(f"/api/items/{uuid.uuid4()}")))
    responses.append(("item_not_found(PATCH)", client.patch(f"/api/items/{uuid.uuid4()}", json={"category": "tops"})))
    responses.append(("item_not_found(DELETE)", client.delete(f"/api/items/{uuid.uuid4()}")))
    responses.append(("validation_error(enum)", client.patch(f"/api/items/{item_id}", json={"category": "コート"})))
    responses.append(("no_completed_items", client.post("/api/suggest", json={"request_text": "今日のコーデ"})))

    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", None)
    responses.append(("service_unavailable(weather)", client.get("/api/weather")))

    monkeypatch.setitem(main_module.app.dependency_overrides, get_db, _override_get_db_failing_commit())
    responses.append(("database_error(PATCH commit)", client.patch(f"/api/items/{item_id}", json={"category": "outer"})))
    monkeypatch.delitem(main_module.app.dependency_overrides, get_db)

    for label, response in responses:
        body = response.text
        assert settings.STORAGE_DIR not in body, f"{label}: absolute path leaked"
        assert "Traceback" not in body, f"{label}: traceback leaked"
        assert _DUMMY_API_KEY not in body, f"{label}: api key leaked"
        payload = response.json()
        assert set(payload.keys()) == {"detail", "error_code", "retryable"}, f"{label}: unexpected response shape"


def test_unhandled_exception_returns_generic_500_without_leaking_details(client, monkeypatch):
    """design.md 13.1節: ハンドルされない例外は500 internal_error(スタックトレースはログのみ)。

    StarletteのServerErrorMiddlewareはTestClient利用時、ハンドラ実行後も例外を
    再送出する(テストで例外を捕捉できるようにする仕様)ため、実応答本文を
    検証するにはraise_server_exceptions=Falseの別クライアントを使う。
    """
    item_id = _create_item()

    def _raise(*args, **kwargs):
        raise RuntimeError(f"unexpected failure touching {settings.STORAGE_DIR}")

    monkeypatch.setattr(items_module, "to_item_response", _raise)

    no_raise_client = TestClient(main_module.app, raise_server_exceptions=False)
    response = no_raise_client.get(f"/api/items/{item_id}")

    assert response.status_code == 500
    body = response.text
    assert response.json()["error_code"] == "internal_error"
    assert response.json()["retryable"] is True
    assert settings.STORAGE_DIR not in body
    assert "Traceback" not in body
    assert "RuntimeError" not in body


def test_openai_client_init_failure_logs_fixed_message_without_leaking_key(tmp_path, monkeypatch, caplog):
    """design.md 13.4節: 外部APIクライアント初期化エラーはメッセージを固定文字列に差し替えて記録する。"""
    storage_dir = tmp_path / "storage"
    data_dir = tmp_path / "data"
    db_path = data_dir / "smartcloset.db"
    dummy_model_path = tmp_path / "dummy_model.pt"
    dummy_model_path.write_bytes(b"")

    monkeypatch.setattr(settings, "STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "MODEL_PATH", str(dummy_model_path))
    monkeypatch.setattr(settings, "OPENAI_API_KEY", _DUMMY_API_KEY)

    test_engine = database_module.build_engine(settings.DATABASE_URL)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(database_module, "engine", test_engine)
    monkeypatch.setattr(database_module, "SessionLocal", test_session_local)

    monkeypatch.setattr(main_module, "YOLO", lambda path: object())

    def _raise_openai_init(api_key):
        raise RuntimeError(f"invalid client config for key={api_key}")

    monkeypatch.setattr(main_module, "OpenAI", _raise_openai_init)

    with caplog.at_level(logging.INFO):
        with TestClient(main_module.app) as test_client:
            assert main_module.app.state.openai_client is None
            response = test_client.get("/api/health")
            assert response.status_code == 200

    assert _DUMMY_API_KEY not in caplog.text


def test_llm_service_non_retryable_error_does_not_log_secret(tmp_path, monkeypatch, caplog):
    """design.md 13.4節: OpenAIの認証エラー等のメッセージにキーが混入してもログへ転記しない。"""
    monkeypatch.setattr(llm_service.time, "sleep", lambda seconds: None)
    image_path = tmp_path / "img.png"
    image_path.write_bytes(b"fake-image-bytes")

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    http_response = httpx.Response(401, request=request)
    client = MagicMock()
    client.chat.completions.create.side_effect = AuthenticationError(
        f"Incorrect API key provided: {_DUMMY_API_KEY}", response=http_response, body=None
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(LlmServiceError):
            extract_metadata(client, image_path)

    assert _DUMMY_API_KEY not in caplog.text


def test_suggest_service_non_retryable_error_does_not_log_secret(monkeypatch, caplog):
    """design.md 13.4節: コーデ提案のOpenAI呼び出しでも認証エラーメッセージをログへ転記しない。"""
    monkeypatch.setattr(suggest_service.time, "sleep", lambda seconds: None)

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    http_response = httpx.Response(401, request=request)
    client = MagicMock()
    client.chat.completions.create.side_effect = AuthenticationError(
        f"Incorrect API key provided: {_DUMMY_API_KEY}", response=http_response, body=None
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(LlmServiceError):
            suggest_service._call_llm(client, "test prompt")

    assert _DUMMY_API_KEY not in caplog.text
