"""T1-1 image_validation_service 用のテストfixtureを生成するスクリプト。

再生成する場合: `python backend/tests/fixtures/generate_fixtures.py`
"""

import shutil
from pathlib import Path

from PIL import Image

FIXTURES_DIR = Path(__file__).parent
REPO_ROOT = FIXTURES_DIR.parent.parent.parent

SOURCE_TOPS = REPO_ROOT / "ai_prototype/Poc/test_images/tops/tops001.jpeg"
SOURCE_SHOES = REPO_ROOT / "ai_prototype/Poc/test_images/shoes/shoes001.jpeg"


def make_tops_and_shoes() -> None:
    shutil.copyfile(SOURCE_TOPS, FIXTURES_DIR / "tops.jpg")
    shutil.copyfile(SOURCE_SHOES, FIXTURES_DIR / "shoes.jpg")


def make_no_clothing() -> None:
    """衣服を含まない風景風の合成画像(YOLOのno_mask誘発用)。"""
    width, height = 640, 480
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    horizon = int(height * 0.6)
    for y in range(height):
        if y < horizon:
            t = y / max(horizon - 1, 1)
            color = (
                int(135 + (200 - 135) * t),
                int(206 + (220 - 206) * t),
                int(235 + (235 - 235) * t),
            )
        else:
            t = (y - horizon) / max(height - horizon - 1, 1)
            color = (
                int(90 - 30 * t),
                int(140 - 40 * t),
                int(60 - 20 * t),
            )
        for x in range(width):
            pixels[x, y] = color
    img.save(FIXTURES_DIR / "no_clothing.jpg", format="JPEG", quality=90)


def make_fake_jpg() -> None:
    (FIXTURES_DIR / "fake.jpg").write_bytes(
        b"this is not an image, just plain text pretending to be a jpg\n" * 10
    )


def make_broken_png() -> None:
    tmp = FIXTURES_DIR / "_broken_source.png"
    img = Image.new("RGB", (200, 200), color=(10, 20, 30))
    img.save(tmp, format="PNG")
    data = tmp.read_bytes()
    truncated = data[: len(data) // 2]
    (FIXTURES_DIR / "broken.png").write_bytes(truncated)
    tmp.unlink()


def make_huge_pixels_png() -> None:
    # settings.MAX_IMAGE_PIXELS(4,000万px)の2倍超を確保し、
    # PillowのDecompressionBombErrorが確実に発生する解像度にする。
    width, height = 9000, 9500  # 85,500,000 px
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    img.save(FIXTURES_DIR / "huge_pixels.png", format="PNG", optimize=True)


def main() -> None:
    make_tops_and_shoes()
    make_no_clothing()
    make_fake_jpg()
    make_broken_png()
    make_huge_pixels_png()
    print("fixtures generated in", FIXTURES_DIR)


if __name__ == "__main__":
    main()
