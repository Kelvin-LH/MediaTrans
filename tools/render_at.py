"""Render the window at a given size for visual inspection:

    python tools/render_at.py WIDTH HEIGHT [suffix] [lang]
"""

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from PySide6.QtWidgets import QApplication

from app.i18n import set_language
from app.ui import MainWindow, theme_qss

OUT = Path(__file__).resolve().parents[1] / "docs"
SAMPLES = ["IMG_2049.HEIC", "IMG_2050.heic", "VID_3052.mov", "song.flac"]


class BI(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("bx", ctypes.c_int32),
                ("by", ctypes.c_int32), ("bc", ctypes.c_uint32), ("bd", ctypes.c_uint32)]


def grab(hwnd: int, path: Path):
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 2)
    bi = BI()
    bi.biSize = ctypes.sizeof(BI)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)


def main():
    width, height = int(sys.argv[1]), int(sys.argv[2])
    suffix = sys.argv[3] if len(sys.argv) > 3 else f"{width}x{height}"
    lang = sys.argv[4] if len(sys.argv) > 4 else "en"
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(theme_qss(False))
    set_language(lang)
    win = MainWindow(language=lang, theme="light")
    win.show()
    win.resize(width, height)
    for _ in range(15):
        app.processEvents()
        time.sleep(0.05)
    grab(int(win.winId()), OUT / f"probe_{suffix}.png")
    print(f"saved probe_{suffix}.png  window={win.width()}x{win.height()} "
          f"compact_settings={win._compact_layout} compact_top={win._top_compact} "
          f"compact_queue={win._queue_compact}")


if __name__ == "__main__":
    main()
