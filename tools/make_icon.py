"""Generate MediaTrans.ico: python tools/make_icon.py"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "MediaTrans.ico"
SIZE = 256


def main():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # diagonal gradient
    grad = Image.new("RGBA", (SIZE, SIZE))
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / (2 * SIZE)
            r = int(0x7C + (0x00 - 0x7C) * t)
            g = int(0x5C + (0xB4 - 0x5C) * t)
            b = int(0xFF + (0xD8 - 0xFF) * t)
            grad.putpixel((x, y), (r, g, b, 255))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (8, 8, SIZE - 8, SIZE - 8), radius=56, fill=255)
    img.paste(grad, (0, 0), mask)
    # glyph
    try:
        font = ImageFont.truetype("arialbd.ttf", 150)
    except OSError:
        font = ImageFont.load_default()
    d.text((SIZE / 2, SIZE / 2), "M", font=font, anchor="mm", fill="white")
    img.save(OUT, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("saved", OUT)


if __name__ == "__main__":
    main()
