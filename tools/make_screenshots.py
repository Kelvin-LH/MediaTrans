"""Render bilingual UI screenshots: python tools/make_screenshots.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from app.i18n import set_language
from app.ui import MainWindow

SAMPLES = [
    "IMG_2049.HEIC",
    "IMG_2050.heic",
    "IMG_2051.HEIF",
    "VID_3052.mov",
]

OUT = Path(__file__).resolve().parents[1] / "docs"
OUT.mkdir(exist_ok=True)


def main():
    app = QApplication([])
    for lang in ("en", "zh"):
        set_language(lang)
        win = MainWindow(language=lang)
        win.resize(940, 660)
        for s in SAMPLES:
            win.file_list.addItem(s)
        win.retranslate()
        win.grab().save(str(OUT / f"screenshot_{lang}.png"))
        win.close()
    print("saved:", *sorted(p.name for p in OUT.glob("screenshot_*.png")))


if __name__ == "__main__":
    main()
