import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/health")
def health(request: Request, db: Session = Depends(get_db)):
    model_loaded = getattr(request.app.state, "yolo_model", None) is not None

    database_available = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_available = False
        logger.warning("database health check failed")

    storage_writable = True
    try:
        check_path = Path(settings.STORAGE_DIR) / "tmp" / ".health_check"
        check_path.write_bytes(b"ok")
        check_path.unlink()
    except OSError:
        storage_writable = False
        logger.warning("storage health check failed")

    storage_free_mb = round(storage_service.check_free_space())

    status = "ok" if (model_loaded and database_available and storage_writable) else "degraded"

    return {
        "status": status,
        "model_loaded": model_loaded,
        "database_available": database_available,
        "storage_writable": storage_writable,
        "storage_free_mb": storage_free_mb,
    }
