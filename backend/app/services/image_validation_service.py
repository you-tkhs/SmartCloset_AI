"""design.md 7.2節・7.4節: アップロード画像の実データ検証と正規化。

7.3節の手順5〜10を実施する。失敗時は独自例外を送出し、
routerで捕捉して13章のエラーコードへマッピングする(415 / 400)。
"""

import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_PNG_SIGNATURE = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
_SIGNATURE_READ_BYTES = 8


class UnsupportedMediaTypeError(Exception):
    """拡張子・MIME・ファイルシグネチャがJPEG/PNGと一致しない場合(→415)。"""


class InvalidImageError(Exception):
    """デコード不可・サイズ超過など、画像データ自体が不正な場合(→400)。"""


@dataclass
class NormalizedImage:
    image: Image.Image  # 検証・補正・正規化済み
    format: str  # "jpeg" | "png"
    width: int
    height: int


def validate_and_normalize(
    tmp_path: Path,
    declared_content_type: str | None,
    original_filename: str | None,
) -> NormalizedImage:
    """7.3節の手順5〜10を実施する。失敗時はValidationError系の独自例外を送出。"""
    _check_extension(original_filename)
    _check_declared_mime(declared_content_type)
    detected_format = _check_signature(tmp_path)

    img = _open_and_decode(tmp_path)
    _check_dimensions(img.width, img.height)

    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)

    img = ImageOps.exif_transpose(img)
    img = _normalize_color_space(img, detected_format)
    img = _strip_metadata(img)

    return NormalizedImage(image=img, format=detected_format, width=img.width, height=img.height)


def _check_extension(original_filename: str | None) -> None:
    ext = Path(original_filename).suffix.lower().lstrip(".") if original_filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise UnsupportedMediaTypeError(f"unsupported file extension: .{ext or '(none)'}")


def _check_declared_mime(declared_content_type: str | None) -> None:
    if declared_content_type is not None and declared_content_type not in _ALLOWED_MIME_TYPES:
        raise UnsupportedMediaTypeError(f"unsupported content type: {declared_content_type}")


def _check_signature(tmp_path: Path) -> str:
    with open(tmp_path, "rb") as f:
        header = f.read(_SIGNATURE_READ_BYTES)
    if header.startswith(_JPEG_SIGNATURE):
        return "jpeg"
    if header.startswith(_PNG_SIGNATURE):
        return "png"
    raise UnsupportedMediaTypeError("unrecognized file signature")


def _open_and_decode(tmp_path: Path) -> Image.Image:
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS
        try:
            with Image.open(tmp_path) as img:
                img.verify()
            img = Image.open(tmp_path)
            img.load()
        except (
            UnidentifiedImageError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            OSError,
            ValueError,
        ) as e:
            raise InvalidImageError("invalid or corrupted image") from e
    return img


def _check_dimensions(width: int, height: int) -> None:
    if width > settings.MAX_IMAGE_WIDTH or height > settings.MAX_IMAGE_HEIGHT:
        raise InvalidImageError(f"image dimensions too large: {width}x{height}")
    if width * height > settings.MAX_IMAGE_PIXELS:
        raise InvalidImageError(f"image pixel count too large: {width * height}")


def _normalize_color_space(img: Image.Image, detected_format: str) -> Image.Image:
    if detected_format == "jpeg":
        if img.mode != "RGB":
            img = img.convert("RGB")
    else:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
    return img


def _strip_metadata(img: Image.Image) -> Image.Image:
    return Image.frombytes(img.mode, img.size, img.tobytes())
