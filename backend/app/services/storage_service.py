import logging
import shutil
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_KIND_DIRS = ("tmp", "originals", "transparent", "masks", "annotated")


def _storage_dir() -> Path:
    return Path(settings.STORAGE_DIR)


def init_storage() -> None:
    for name in _KIND_DIRS:
        (_storage_dir() / name).mkdir(parents=True, exist_ok=True)
    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)


def original_path(item_id: str, ext: str) -> Path:
    return _storage_dir() / "originals" / f"{item_id}_original.{ext}"


def transparent_path(item_id: str) -> Path:
    return _storage_dir() / "transparent" / f"{item_id}_transparent.png"


def mask_path(item_id: str) -> Path:
    return _storage_dir() / "masks" / f"{item_id}_mask.png"


def annotated_path(item_id: str) -> Path:
    return _storage_dir() / "annotated" / f"{item_id}_annotated.png"


def work_path(item_id: str) -> Path:
    return _storage_dir() / "tmp" / f"{item_id}_work.png"


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("failed to delete file: %s", path.name)


def delete_generated_files(item_id: str) -> None:
    for path in (transparent_path(item_id), mask_path(item_id), annotated_path(item_id), work_path(item_id)):
        _safe_unlink(path)


def delete_item_files(item_id: str) -> None:
    for path in _storage_dir().glob(f"originals/{item_id}_original.*"):
        _safe_unlink(path)
    delete_generated_files(item_id)


def delete_tmp(tmp_path: Path) -> None:
    _safe_unlink(Path(tmp_path))


def check_free_space() -> float:
    usage = shutil.disk_usage(_storage_dir())
    return usage.free / (1024 * 1024)


def to_public_url(path: str) -> str | None:
    p = Path(path)
    if p.parent.name == "originals":
        return f"/images/originals/{p.name}"
    if p.parent.name == "transparent":
        return f"/images/transparent/{p.name}"
    return None
