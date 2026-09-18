"""Adaptive layout test: the window must render correctly at every window size
and font scale — no text clipped, nothing pushed outside the settings panel.

Simulated font point sizes stand in for DPI scale factors (100%, 125%, 150%,
200%), which is what actually makes text overflow a fixed-width layout.

    python tests/test_layout.py
"""

from __future__ import annotations

import contextlib
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QPushButton, QRadioButton, QWidget

from app import APP_NAME
from app.i18n import set_language
from app.ui import MainWindow, theme_qss

# legacy Windows code pages cannot print every message verbatim
for _stream in (sys.stdout, sys.stderr):
    with contextlib.suppress(AttributeError, ValueError, OSError):
        _stream.reconfigure(errors="replace")

PASS = 0
FAIL = 0

# common screen widths and the smallest laptop sizes still in use
WINDOW_SIZES = [
    (780, 460),    # absolute minimum
    (820, 560),    # 1280x720 at 150% scaling
    (1024, 600),   # small window on a small laptop
    (1280, 720),   # 1366x768 with the taskbar showing
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
]
FONT_POINTS = [7.5, 9.0, 11.0, 14.0]     # ~100% to ~200% text growth
TEXT_WIDGETS = (QLabel, QCheckBox, QRadioButton, QPushButton)


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def settle(app, rounds: int = 10):
    for _ in range(rounds):
        app.processEvents()
        time.sleep(0.01)


def overflowing(panel: QWidget) -> list[str]:
    """Widgets whose right edge is past the panel — content cut off."""
    bad = []
    for widget in panel.findChildren(QWidget):
        if widget.isWindow() or not widget.isVisible():
            continue
        if widget.geometry().right() > panel.width() + 2:
            bad.append(f"{type(widget).__name__}({widget.objectName() or '-'})"
                       f" right={widget.geometry().right()} > {panel.width()}")
    return bad


def clipped(root: QWidget) -> list[str]:
    """Widgets whose own text does not fit in their allocated width."""
    bad = []
    for cls in TEXT_WIDGETS:
        for widget in root.findChildren(cls):
            if not widget.isVisible():
                continue
            if isinstance(widget, QLabel) and (widget.wordWrap() or not widget.text()):
                continue          # wrapped labels shrink legitimately
            width = widget.width()
            needed = widget.sizeHint().width()
            if width and width < needed - 1:
                text = getattr(widget, "text", lambda: "")()
                bad.append(f"{type(widget).__name__}({text[:24]!r}) {width} < {needed}")
    return bad


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    default_font = QFont(app.font())
    # a stored window geometry from an earlier run must not skew the checks
    QSettings(APP_NAME, APP_NAME).remove("geometry")

    # -- the window must always fit the screen it opens on
    window = MainWindow()
    window.show()
    settle(app)
    screen = window.screen() or QApplication.primaryScreen()
    if screen is not None:
        avail = screen.availableGeometry()
        check("fit: window fits the available screen area",
              window.width() <= avail.width() and window.height() <= avail.height(),
              f"{window.size()} vs {avail.size()}")
        check("fit: minimum size fits the screen",
              window.minimumWidth() <= avail.width()
              and window.minimumHeight() <= avail.height(),
              f"{window.minimumSize()} vs {avail.size()}")
        check("fit: window is centred on the screen",
              avail.x() <= window.x() and window.x() + window.width() <= avail.right() + 1,
              f"x={window.x()} w={window.width()} avail={avail}")
    window.close()

    panel_overflow: list[str] = []
    text_clipped: list[str] = []
    log_too_small: list[str] = []
    compact_states: dict[int, bool] = {}

    for lang in ("en", "zh"):
        for theme in ("light", "dark"):
            app.setStyleSheet(theme_qss(theme == "dark"))
            for points in FONT_POINTS:
                font = QFont(default_font)
                font.setPointSizeF(points)
                app.setFont(font)
                set_language(lang)
                win = MainWindow(language=lang, theme=theme)
                win.show()
                settle(app)
                for width, height in WINDOW_SIZES:
                    win.resize(width, height)
                    settle(app)
                    ctx = f"{lang}/{theme}/{points}pt/{width}x{height}"
                    panel = win.settings_scroll.widget()
                    overflow = overflowing(panel)
                    if overflow:
                        panel_overflow.append(f"{ctx}: {overflow[0]}")
                    clip = clipped(win)
                    if clip:
                        text_clipped.append(f"{ctx}: {clip[0]}")
                    if win.log.height() < win.fontMetrics().lineSpacing() * 3:
                        log_too_small.append(
                            f"{ctx}: log={win.log.height()}")
                    compact_states[win.settings_scroll.viewport().width()] = \
                        win._compact_layout
                win.close()

    check("layout: no widget overflows the settings panel",
          not panel_overflow,
          "; ".join(panel_overflow[:3]))
    check("layout: no text is clipped at any size or font scale",
          not text_clipped,
          "; ".join(text_clipped[:3]))
    check("layout: the log stays readable when the window is short",
          not log_too_small, "; ".join(log_too_small[:2]))
    check("layout: narrow viewports use the single-column arrangement",
          any(compact_states.values()))
    check("layout: wide viewports use the two-column arrangement",
          any(not v for v in compact_states.values()))

    # -- the breakpoint must be stable (no flip-flopping) once settled
    set_language("en")
    app.setFont(default_font)
    win = MainWindow(language="en")
    win.show()
    settle(app)
    history = []
    for width, height in WINDOW_SIZES + list(reversed(WINDOW_SIZES)):
        win.resize(width, height)
        settle(app)
        history.append(win._compact_layout)
    check("layout: breakpoint is stable across repeated resizes",
          len(set(history)) <= 2, str(history))
    win.close()

    # -- window geometry survives a restart and is re-clamped to the screen
    settings = QSettings(APP_NAME, APP_NAME)
    settings.remove("geometry")
    probe = MainWindow()
    probe.show()
    settle(app)
    avail = (probe.screen() or QApplication.primaryScreen())
    avail = avail.availableGeometry() if avail is not None else None
    probe.close()

    target_w = 760 if avail is None else min(760, int(avail.width() * 0.9))
    target_h = 560 if avail is None else min(560, int(avail.height() * 0.9))
    first = MainWindow()
    first.show()
    settle(app)
    if first.minimumWidth() <= target_w and first.minimumHeight() <= target_h:
        first.resize(target_w, target_h)
        settle(app)
        chosen = (first.width(), first.height())
        first.close()                      # stores the geometry
        second = MainWindow()
        second.show()
        settle(app)
        check("geometry: window size is restored on the next launch",
              (second.width(), second.height()) == chosen,
              f"{second.size()} vs {chosen}")
        if avail is not None:
            check("geometry: restored window still fits the screen",
                  second.width() <= max(second.minimumWidth(), int(avail.width() * 0.96))
                  and second.height() <= max(second.minimumHeight(), int(avail.height() * 0.96)),
                  f"{second.size()} on {avail.size()}")
        second.close()
    else:
        first.close()
    settings.remove("geometry")

    # -- the error dialog must also fit a small screen
    from app.ui import ErrorDialog
    dialog = ErrorDialog(None, "Error", "x" * 5000)
    dialog.show()
    settle(app, 4)
    if screen is not None:
        check("dialog: error dialog fits the screen",
              dialog.width() <= screen.availableGeometry().width(),
              str(dialog.size()))
    dialog.close()

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
