import asyncio
import errno
import io
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.services import storage_service
from app.services.image_validation_service import (
    InvalidImageError,
    UnsupportedMediaTypeError,
    validate_and_normalize,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class _FakeUploadFile:
    """テスト用の疑似UploadFile。実受信バイト数のみを基準に読み込む。"""

    def __init__(self, data: bytes, declared_size: int | None = None):
        self._buf = io.BytesIO(data)
        self.size = declared_size

    async def read(self, n: int) -> bytes:
        return self._buf.read(n)


def test_validation_accepts_tops_jpg():
    result = validate_and_normalize(FIXTURES_DIR / "tops.jpg", "image/jpeg", "tops.jpg")

    assert result.format == "jpeg"
    assert result.image.mode == "RGB"
    assert result.width > 0
    assert result.height > 0


def test_validation_accepts_shoes_jpg():
    result = validate_and_normalize(FIXTURES_DIR / "shoes.jpg", "image/jpeg", "shoes.jpg")

    assert result.format == "jpeg"
    assert result.image.mode == "RGB"


def test_validation_rejects_disallowed_extension():
    with pytest.raises(UnsupportedMediaTypeError):
        validate_and_normalize(FIXTURES_DIR / "tops.jpg", "image/jpeg", "photo.gif")


def test_validation_rejects_mime_type_mismatch():
    with pytest.raises(UnsupportedMediaTypeError):
        validate_and_normalize(FIXTURES_DIR / "tops.jpg", "text/plain", "tops.jpg")


def test_validation_rejects_fake_jpg_by_signature():
    with pytest.raises(UnsupportedMediaTypeError):
        validate_and_normalize(FIXTURES_DIR / "fake.jpg", "image/jpeg", "fake.jpg")


def test_validation_rejects_broken_png():
    with pytest.raises(InvalidImageError):
        validate_and_normalize(FIXTURES_DIR / "broken.png", "image/png", "broken.png")


def test_validation_rejects_huge_pixels_png():
    with pytest.raises(InvalidImageError):
        validate_and_normalize(FIXTURES_DIR / "huge_pixels.png", "image/png", "huge_pixels.png")


def test_validation_rejects_pixels_in_bomb_warning_band(tmp_path):
    # settings.MAX_IMAGE_PIXELS(4,000万px)の1〜2倍の範囲はPillowが
    # DecompressionBombWarning(エラー化済み)を出す帯域。DecompressionBombError
    # (2倍超)とは別の例外型のため、except節に含めていないと素通りしてしまう。
    src = tmp_path / "bomb_warning_band.png"
    img = Image.new("RGB", (7000, 7000), color=(100, 100, 100))  # 49,000,000px
    img.save(src, format="PNG")

    with pytest.raises(InvalidImageError):
        validate_and_normalize(src, "image/png", "bomb_warning_band.png")


def test_validation_error_message_excludes_absolute_path():
    with pytest.raises(InvalidImageError) as exc_info:
        validate_and_normalize(FIXTURES_DIR / "broken.png", "image/png", "broken.png")

    assert str(FIXTURES_DIR) not in str(exc_info.value)


def test_validation_unidentifiable_image_error_excludes_absolute_path(tmp_path):
    # PNGシグネチャは正しいが本体が壊れている場合、Pillowの
    # UnidentifiedImageErrorはメッセージにtmpの絶対パスを含める。
    # InvalidImageErrorに素通しすると絶対パスが漏れるため、固定メッセージにしていることを確認する。
    src = tmp_path / "unidentifiable.png"
    src.write_bytes(b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a" + b"\x00" * 2000)

    with pytest.raises(InvalidImageError) as exc_info:
        validate_and_normalize(src, "image/png", "unidentifiable.png")

    assert str(tmp_path) not in str(exc_info.value)


def test_validation_applies_exif_orientation(tmp_path):
    src = tmp_path / "exif_oriented.jpg"
    img = Image.new("RGB", (100, 50), (200, 50, 50))
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation: rotate 270 CW
    img.save(src, format="JPEG", exif=exif)

    result = validate_and_normalize(src, "image/jpeg", "exif_oriented.jpg")

    assert (result.width, result.height) == (50, 100)


def test_validation_converts_cmyk_jpeg_to_rgb(tmp_path):
    src = tmp_path / "cmyk.jpg"
    img = Image.new("CMYK", (60, 40))
    img.save(src, format="JPEG")

    result = validate_and_normalize(src, "image/jpeg", "cmyk.jpg")

    assert result.format == "jpeg"
    assert result.image.mode == "RGB"


@pytest.fixture
def storage_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(settings, "MIN_FREE_STORAGE_MB", 1)
    storage_service.init_storage()
    return tmp_path / "storage" / "tmp"


def _tmp_files(tmp_dir: Path) -> list[Path]:
    return list(tmp_dir.glob("*.upload"))


def test_chunk_upload_rejects_oversized_file_and_leaves_no_tmp(storage_env):
    data = b"x" * (2 * 1024 * 1024)  # MAX_UPLOAD_SIZE_MB=1MBを超過
    file = _FakeUploadFile(data)

    with pytest.raises(storage_service.FileTooLargeError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_uses_actual_received_size_over_declared_size(storage_env):
    # Content-Length偽装を模した状況: 申告サイズ(declared_size)は小さいが、
    # 実際に読み込まれるバイト数は上限を超える。実受信サイズを最終基準とする。
    data = b"x" * (2 * 1024 * 1024)
    file = _FakeUploadFile(data, declared_size=100)

    with pytest.raises(storage_service.FileTooLargeError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_rejects_when_free_space_insufficient(storage_env, monkeypatch):
    monkeypatch.setattr(storage_service, "check_free_space", lambda: 0.1)
    file = _FakeUploadFile(b"small file content")

    with pytest.raises(storage_service.InsufficientStorageError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_storage_error_on_write_failure_leaves_no_tmp(storage_env, monkeypatch):
    def _raise_write_error(f, chunk: bytes) -> None:
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(storage_service, "_write_chunk", _raise_write_error)
    file = _FakeUploadFile(b"small file content")

    with pytest.raises(storage_service.StorageError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_insufficient_storage_on_enospc_write_failure(storage_env, monkeypatch):
    def _raise_enospc(f, chunk: bytes) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(storage_service, "_write_chunk", _raise_enospc)
    file = _FakeUploadFile(b"small file content")

    with pytest.raises(storage_service.InsufficientStorageError):
        asyncio.run(storage_service.save_upload_to_tmp(file))

    assert _tmp_files(storage_env) == []


def test_chunk_upload_succeeds_and_computes_sha256(storage_env):
    data = b"hello smartcloset"
    file = _FakeUploadFile(data)

    result = asyncio.run(storage_service.save_upload_to_tmp(file))

    assert result.size == len(data)
    assert len(result.sha256) == 64
    assert result.tmp_path.read_bytes() == data
    assert _tmp_files(storage_env) == [result.tmp_path]


def test_no_bulk_file_read_in_storage_service():
    source = Path(storage_service.__file__).read_text()
    assert ".read()" not in source
