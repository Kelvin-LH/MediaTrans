"""Render bilingual UI screenshots: python tools/make_screenshots.py

Renders each language to a real native window kept off-screen
(WA_DontShowOnScreen) and captures it via PrintWindow — QWidget.grab() is
avoided because it mis-renders QComboBox under styled Fusion.
"""

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.i18n import set_language
from app.ui import QSS, MainWindow

SAMPLES = ["IMG_2049.HEIC", "IMG_2050.heic", "IMG_2051.HEIF", "VID_3052.mov"]

OUT = Path(__file__).resolve().parents[1] / "docs"
OUT.mkdir(exist_ok=True)


class BI(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("bx", ctypes.c_int32),
                ("by", ctypes.c_int32), ("bc", ctypes.c_uint32), ("bd", ctypes.c_uint32)]


def printwindow_to_png(hwnd: int, path: Path):
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 2)  # PW_RENDERFULLCONTENT
    bi = BI()
    bi.biSize = ctypes.sizeof(BI)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(path)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    for lang in ("en", "zh"):
        set_language(lang)
        win = MainWindow(language=lang)
        win.resize(980, 780)
        for s in SAMPLES:
            win.file_list.addItem(s)
        win.retranslate()
        win.show()
        for _ in range(8):  # let the layout settle completely
            app.processEvents()
            time.sleep(0.1)
        hwnd = int(win.winId())
        printwindow_to_png(hwnd, OUT / f"screenshot_{lang}.png")
        win.close()
        print(f"saved screenshot_{lang}.png")


if __name__ == "__main__":
    main()
