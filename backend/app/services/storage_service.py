import errno
import hashlib
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

_KIND_DIRS = ("tmp", "originals", "transparent", "masks", "annotated")


class FileTooLargeError(Exception):
    """実受信サイズが MAX_UPLOAD_SIZE_MB を超過した場合(→413)。"""


class InsufficientStorageError(Exception):
    """ストレージの空き容量が不足している場合(事前確認またはENOSPC)(→503)。"""


class StorageError(Exception):
    """空き容量以外の理由でファイル書き込みに失敗した場合(→500)。"""


@dataclass
class TmpUploadResult:
    tmp_path: Path
    size: int
    sha256: str


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


def _write_chunk(f, chunk: bytes) -> None:
    f.write(chunk)


async def _write_chunks_to_tmp(file: UploadFile, tmp_path: Path, max_bytes: int, chunk_size: int) -> tuple[int, str]:
    hasher = hashlib.sha256()
    total_size = 0
    with open(tmp_path, "wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_bytes:
                raise FileTooLargeError(f"received size exceeds limit: {total_size} bytes")
            hasher.update(chunk)
            _write_chunk(f, chunk)
    return total_size, hasher.hexdigest()


async def save_upload_to_tmp(file: UploadFile) -> TmpUploadResult:
    """design.md 7.3節手順3〜4・7.8節。一括読み込みは行わずチャンク単位で書き込む。"""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    free_mb = check_free_space()
    if free_mb < settings.MIN_FREE_STORAGE_MB:
        logger.error("insufficient free storage before upload: %.1fMB free", free_mb)
        raise InsufficientStorageError("insufficient free storage")

    tmp_path = _storage_dir() / "tmp" / f"{uuid.uuid4().hex}.upload"
    try:
        total_size, sha256 = await _write_chunks_to_tmp(file, tmp_path, max_bytes, settings.UPLOAD_CHUNK_SIZE_BYTES)
    except FileTooLargeError:
        _safe_unlink(tmp_path)
        raise
    except OSError as e:
        _safe_unlink(tmp_path)
        if e.errno == errno.ENOSPC:
            logger.error("insufficient storage while writing tmp upload")
            raise InsufficientStorageError("no space left on device") from e
        logger.error("failed to write tmp upload (errno=%s)", e.errno)
        raise StorageError("failed to write upload to tmp storage") from e

    return TmpUploadResult(tmp_path=tmp_path, size=total_size, sha256=sha256)


def to_public_url(path: str) -> str | None:
    p = Path(path)
    if p.parent.name == "originals":
        return f"/images/originals/{p.name}"
    if p.parent.name == "transparent":
        return f"/images/transparent/{p.name}"
    return None
