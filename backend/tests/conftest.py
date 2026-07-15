import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import app.database as database_module
import app.main as main_module
from app.config import settings


class _DummyYOLOModel:
    """テスト用ダミーモデル。実推論は行わない。"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    data_dir = tmp_path / "data"
    db_path = data_dir / "smartcloset.db"
    dummy_model_path = tmp_path / "dummy_model.pt"
    dummy_model_path.write_bytes(b"")

    monkeypatch.setattr(settings, "STORAGE_DIR", str(storage_dir))
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(settings, "MODEL_PATH", str(dummy_model_path))
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)

    test_engine = database_module.build_engine(settings.DATABASE_URL)
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(database_module, "engine", test_engine)
    monkeypatch.setattr(database_module, "SessionLocal", test_session_local)

    monkeypatch.setattr(main_module, "YOLO", lambda path: _DummyYOLOModel())

    with TestClient(main_module.app) as test_client:
        yield test_client
