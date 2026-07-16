from pathlib import Path

import pytest
from PIL import Image

from app.services.image_validation_service import (
    InvalidImageError,
    UnsupportedMediaTypeError,
    validate_and_normalize,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
