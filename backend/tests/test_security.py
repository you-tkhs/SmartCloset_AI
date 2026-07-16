"""design.md 10.3節・13.4節: 静的ファイル公開範囲の限定と機密情報非漏洩の検証(T1-9)。

to_public_url()の変換ロジック自体のテストはtest_services.pyに既存のため、
本ファイルではマウント範囲(公開ディレクトリの限定)とエラー応答の非漏洩のみを扱う。
"""

import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from starlette.routing import Mount

import app.main as main_module
from app.config import settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
