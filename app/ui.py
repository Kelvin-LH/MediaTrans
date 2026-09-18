"""Main window for MediaTrans (PySide6, bilingual EN/中文).

Layout: language / theme / log in the top bar, the file queue on the left, a
scrollable settings panel on the right (presets, formats, quality, resize,
metadata, performance, output), and actions + progress + log at the bottom.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QLocale, QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, APP_REPO, __version__, converter
from .i18n import LANG_NAMES, current_language, set_language, tr

DROP_EXTS = converter.ALL_EXTS

# Layout metrics in device-independent pixels. The window is capped to the
# screen at runtime, so these are preferences rather than requirements.
PREFERRED_SIZE = (1280, 980)
MINIMUM_SIZE = (780, 460)
# below this settings-viewport width the two columns stop fitting
COMPACT_BREAKPOINT = 660


def _scaled_font(base: QFont, factor: float) -> QFont:
    """A copy of `base` scaled by `factor`, honouring both pt and px fonts."""
    font = QFont(base)
    if font.pointSizeF() > 0:
        font.setPointSizeF(max(6.5, font.pointSizeF() * factor))
    elif font.pixelSize() > 0:
        font.setPixelSize(max(8, round(font.pixelSize() * factor)))
    return font

IMAGE_CODES = list(converter.IMAGE_FORMATS)
VIDEO_CODES = list(converter.VIDEO_FORMATS)
AUDIO_CODES = list(converter.AUDIO_FORMATS)
CONFLICT_CODES = list(converter.CONFLICT_POLICIES)

# i18n key overrides for format codes whose key is not fmt_<code>
FMT_KEY = {"JPEG": "fmt_jpg"}
FMT_PREFIX = {"image": "fmt_", "video": "vfmt_", "audio": "afmt_"}

# preset name -> (image, video, audio, quality, resize_long_edge)
PRESETS: dict[str, tuple[str, str, str, int, int]] = {
    "custom": ("", "", "", 0, 0),
    "web": ("WEBP", "MP4", "MP3", 85, 2560),
    "social": ("JPEG", "MP4", "M4A", 88, 1920),
    "archive": ("PNG", "MKV", "FLAC", 100, 0),
    "compat": ("JPEG", "MP4", "MP3", 95, 0),
    "small": ("WEBP", "MP4", "OGG", 75, 1280),
}


def theme_qss(dark: bool) -> str:
    p = {
        "bg": "#16181d" if dark else "#eef1f6",
        "card": "#1f2229" if dark else "#ffffff",
        "border": "#2c313a" if dark else "#e3e8f2",
        "field": "#262a33" if dark else "#ffffff",
        "field_border": "#3a404b" if dark else "#d5dbe8",
        "text": "#e6e9ef" if dark else "#1f2430",
        "muted": "#9aa3b2" if dark else "#6b7280",
        "accent": "#8b7cff" if dark else "#6d5dfc",
        "accent_hover": "#7a68ff" if dark else "#5b49f2",
        "accent_soft": "#2a2542" if dark else "#ece7ff",
        "hover_row": "#262b35" if dark else "#f1f0fb",
        "log_text": "#a8b1c1" if dark else "#4b5563",
        "disabled": "#6b7280" if dark else "#9aa3b2",
        "disabled_bg": "#20232a" if dark else "#f4f6fa",
    }
    return f"""
* {{ outline: none; }}
QMainWindow, QWidget {{ background: {p['bg']}; color: {p['text']}; }}
QLabel {{ background: transparent; }}

QGroupBox {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 12px;
    margin-top: 14px;
    padding: 14px 12px 10px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px; top: 4px; padding: 0 6px;
    color: {p['accent']};
}}

QListWidget#fileList {{
    background: {p['field']};
    border: 2px dashed {p['field_border']};
    border-radius: 12px;
    padding: 8px;
}}
QListWidget#fileList::item {{ padding: 5px 8px; border-radius: 6px; }}
QListWidget#fileList::item:selected {{ background: {p['accent_soft']}; color: {p['text']}; }}
QListWidget#fileList::item:hover:!selected {{ background: {p['hover_row']}; }}

QListWidget#logList {{
    background: {p['card']};
    border: 1px solid {p['border']};
    border-radius: 12px;
    padding: 6px;
    color: {p['log_text']};
}}

QPushButton {{
    background: {p['field']};
    border: 1px solid {p['field_border']};
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 500;
}}
QPushButton:hover {{ border-color: {p['accent']}; color: {p['accent']}; }}
QPushButton:pressed {{ background: {p['accent_soft']}; }}
QPushButton:disabled {{ color: {p['disabled']}; border-color: {p['border']}; background: {p['disabled_bg']}; }}

QPushButton#convertBtn {{
    background: {p['accent']}; color: #ffffff; border: none;
    font-weight: 600; padding: 8px 24px;
}}
QPushButton#convertBtn:hover {{ background: {p['accent_hover']}; }}
QPushButton#convertBtn:disabled {{ background: {p['accent_soft']}; color: {p['disabled']}; }}

QProgressBar {{
    background: {p['border']}; border: none; border-radius: 7px;
    height: 14px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {p['accent']}, stop:1 #00b4d8);
    border-radius: 7px;
}}

QSlider {{ min-height: 22px; }}
QSlider::groove:horizontal {{ height: 6px; background: {p['border']}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {p['accent_soft']}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    width: 16px; height: 16px; margin: -5px 0;
    border-radius: 8px; background: {p['accent']};
}}

QComboBox, QSpinBox, QLineEdit {{
    background: {p['field']}; color: {p['text']};
    border: 1px solid {p['field_border']};
    border-radius: 8px; padding: 5px 8px; min-height: 20px;
}}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{ border-color: {p['accent']}; }}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{ border-color: {p['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px; background: transparent; border: none;
}}
QComboBox QAbstractItemView {{
    background: {p['card']}; color: {p['text']};
    border: 1px solid {p['field_border']};
    selection-background-color: {p['accent_soft']}; selection-color: {p['text']};
}}
QLineEdit:disabled, QSpinBox:disabled {{ background: {p['disabled_bg']}; color: {p['disabled']}; }}

QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 1px solid {p['field_border']}; border-radius: 5px; background: {p['field']};
}}
QCheckBox::indicator:hover {{ border-color: {p['accent']}; }}
QCheckBox::indicator:checked {{ background: {p['accent']}; border-color: {p['accent']}; }}
QRadioButton::indicator {{
    width: 17px; height: 17px;
    border: 1px solid {p['field_border']}; border-radius: 9px; background: {p['field']};
}}
QRadioButton::indicator:hover {{ border-color: {p['accent']}; }}
QRadioButton::indicator:checked {{
    border: 5px solid {p['accent']}; background: {p['field']}; width: 7px; height: 7px;
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {p['field_border']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p['accent']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QSplitter::handle {{ background: transparent; width: 6px; }}
QPlainTextEdit {{
    background: {p['field']}; color: {p['text']};
    border: 1px solid {p['field_border']}; border-radius: 8px; padding: 6px;
    font-family: Consolas, "Cascadia Mono", monospace;
}}
"""


def app_icon() -> QIcon:
    pm = QPixmap(128, 128)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 128, 128)
    grad.setColorAt(0.0, QColor("#7c5cff"))
    grad.setColorAt(1.0, QColor("#00b4d8"))
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(8, 8, 112, 112, 28, 28)
    p.setPen(QColor("white"))
    f = QFont()
    f.setPixelSize(58)
    f.setBold(True)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, "M")
    p.end()
    return QIcon(pm)


class DropList(QListWidget):
    files_added = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setObjectName("fileList")

    def _paths(self, event) -> list[str]:
        out = []
        for u in event.mimeData().urls():
            if u.isLocalFile():
                out.append(u.toLocalFile())
        return out

    def dragEnterEvent(self, event):
        if any(Path(p).is_dir() or Path(p).suffix.lower() in DROP_EXTS
               for p in self._paths(event)):
            self.setStyleSheet("QListWidget#fileList { border-color: #6d5dfc; }")
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        self.setStyleSheet("")
        paths = [p for p in self._paths(event)
                 if Path(p).is_dir() or Path(p).suffix.lower() in DROP_EXTS]
        if paths:
            self.files_added.emit(paths)
            event.acceptProposedAction()


class ErrorDialog(QDialog):
    """Full error text with copy-to-clipboard."""

    def __init__(self, parent, title: str, body: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        screen = parent.screen() if parent else QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            self.resize(min(680, int(avail.width() * 0.85)),
                        min(420, int(avail.height() * 0.7)))
        else:
            self.resize(680, 420)
        self.setMinimumWidth(320)
        lay = QVBoxLayout(self)
        box = QPlainTextEdit(body)
        box.setReadOnly(True)
        lay.addWidget(box)
        row = QHBoxLayout()
        copy = QPushButton(tr("copy"))
        copy.clicked.connect(lambda: QApplication.clipboard().setText(body))
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        row.addWidget(copy)
        row.addStretch()
        row.addWidget(btns)
        lay.addLayout(row)


class ConvertWorker(QThread):
    progress = Signal(int, int, str)             # done, total, name
    file_done = Signal(str, str, bool, str, int, int, bool)
    all_done = Signal(object)                    # BatchStats

    def __init__(self, jobs: list[tuple[Path, Path]], opts: converter.ConvertOptions):
        super().__init__()
        self._jobs = jobs
        self._opts = opts
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if len({d for _, d in self._jobs}) == 1:
            stats = converter.convert_many(
                [s for s, _ in self._jobs], self._jobs[0][1], self._opts,
                on_progress=self._emit, should_cancel=lambda: self._cancelled)
        else:
            stats = converter.BatchStats()
            groups: dict[Path, list[Path]] = {}
            for src, d in self._jobs:
                groups.setdefault(d, []).append(src)
            offset = 0
            for d, group in groups.items():
                def cb(done, total, path, res, _off=offset):
                    self._emit(_off + done, len(self._jobs), path, res)
                s = converter.convert_many(
                    group, d, self._opts, on_progress=cb,
                    should_cancel=lambda: self._cancelled)
                stats.ok += s.ok
                stats.fail += s.fail
                stats.skipped += s.skipped
                stats.in_bytes += s.in_bytes
                stats.out_bytes += s.out_bytes
                stats.seconds += s.seconds
                stats.failures.extend(s.failures)
                offset += len(group)
        self.all_done.emit(stats)

    def _emit(self, done: int, total: int, path: Path, res: converter.ConvertResult):
        self.progress.emit(done, total, path.name)
        out = str(res.output) if res.output else ""
        self.file_done.emit(path.name, out, res.ok, res.message,
                            res.in_bytes, res.out_bytes, res.skipped)


class MainWindow(QMainWindow):
    def __init__(self, language: str | None = None, theme: str | None = None):
        super().__init__()
        self._settings = QSettings(APP_NAME, APP_NAME)
        lang = (language or self._settings.value("language", None)
                or self._detect_language())
        set_language(lang)
        self._theme = theme or self._settings.value("theme", "light")

        self._worker: ConvertWorker | None = None
        self._last_output: Path | None = None
        self._errors: dict[str, str] = {}

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self._build_ui()
        self._apply_fonts()
        self._load_settings()
        self.retranslate()
        self._apply_theme()
        self._apply_initial_geometry()

    # ------------------------------------------------- geometry & scaling --

    def _apply_initial_geometry(self) -> None:
        """Size, clamp and centre the window for the screen it opens on.

        Screen sizes and DPI scale factors vary wildly (a 1366x768 laptop at
        100% versus a 4K display at 200%), so the preferred size is capped to
        what is actually available, the minimum size stays small enough for a
        laptop with the taskbar showing, and a size restored from a previous
        session is re-clamped in case the display changed.
        """
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:                      # headless / offscreen
            self.resize(*PREFERRED_SIZE)
            return
        avail = screen.availableGeometry()

        self.setMinimumSize(
            min(MINIMUM_SIZE[0], int(avail.width() * 0.9)),
            min(MINIMUM_SIZE[1], int(avail.height() * 0.9)),
        )

        restored = self._settings.value("geometry")
        if restored is not None and self.restoreGeometry(restored):
            width, height = self.width(), self.height()
            # the display may be smaller than when the size was stored
            width = max(self.minimumWidth(), min(width, int(avail.width() * 0.96)))
            height = max(self.minimumHeight(), min(height, int(avail.height() * 0.96)))
            if (width, height) != (self.width(), self.height()):
                self.resize(width, height)
            if not avail.contains(self.frameGeometry()):
                self.move(avail.x() + max(0, (avail.width() - width) // 2),
                          avail.y() + max(0, (avail.height() - height) // 2))
            self._splitter.setSizes([int(width * 0.34), int(width * 0.66)])
            return

        width = max(self.minimumWidth(),
                    min(PREFERRED_SIZE[0], int(avail.width() * 0.96)))
        height = max(self.minimumHeight(),
                     min(PREFERRED_SIZE[1], int(avail.height() * 0.96)))
        self.resize(width, height)
        self.move(avail.x() + max(0, (avail.width() - width) // 2),
                  avail.y() + max(0, (avail.height() - height) // 2))
        self._splitter.setSizes([int(width * 0.34), int(width * 0.66)])

    def _apply_fonts(self) -> None:
        """Derive small sizes from the default font instead of hard-coding px,
        so 125% / 150% / 200% DPI and custom system fonts never clip text."""
        base = QApplication.font()
        self.log.setFont(_scaled_font(base, 0.94))
        fm = self.fontMetrics()
        # two lines of wrapped hint text, and a queue/log that can shrink
        self.video_note.setMinimumHeight(fm.lineSpacing() * 2 + 6)
        self.meta_note.setMinimumHeight(fm.lineSpacing() * 2)
        self.gpu_note.setMinimumHeight(fm.lineSpacing() * 2)
        self.file_list.setMinimumHeight(fm.lineSpacing() * 4)
        self.log.setMinimumHeight(fm.lineSpacing() * 4)

    def eventFilter(self, watched, event):
        # The settings viewport is the authoritative width for the breakpoint:
        # it is correct even while the window itself is still resizing.
        if watched is self.settings_scroll.viewport() and event.type() == QEvent.Resize:
            self._relayout_settings(compact=self._should_compact(event.size().width()))
        return super().eventFilter(watched, event)

    @staticmethod
    def _should_compact(viewport_width: int) -> bool:
        """Hysteresis stops the panel flip-flopping at the breakpoint when
        switching columns adds or removes the vertical scrollbar."""
        if viewport_width < COMPACT_BREAKPOINT:
            return True
        if viewport_width > COMPACT_BREAKPOINT + 60:
            return False
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_settings(
            compact=self._should_compact(self.settings_scroll.viewport().width()))
        self._relayout_top(compact=self._content_width() < self._top_bar_width_needed())
        self._relayout_queue(
            compact=self.file_list.width() < self._queue_buttons_width_needed())

    # --------------------------------------------------- adaptive sections --

    # a little slack so a row is never laid out exactly at its natural width
    LAYOUT_SAFETY = 8

    def _content_width(self) -> int:
        """Width actually available to rows inside the central widget."""
        central = self.centralWidget()
        if central is None:
            return self.width()
        margins = self._root_margins
        return central.width() - margins.left() - margins.right()

    def _widgets_total_width(self, *widgets: QWidget) -> int:
        """Natural width of a row: widget hints, spacing and a little slack."""
        return (sum(w.sizeHint().width() for w in widgets)
                + 8 * max(0, len(widgets) - 1) + self.LAYOUT_SAFETY)

    def _top_bar_width_needed(self) -> int:
        """Natural width of the single-row top bar for the current language,
        font and DPI — so the fold happens exactly when it has to."""
        return self._widgets_total_width(
            self.lang_label, self.lang_combo, self.theme_btn,
            self.log_file_btn, self.about_btn)

    def _queue_buttons_width_needed(self) -> int:
        return self._widgets_total_width(
            self.add_btn, self.add_dir_btn, self.remove_btn, self.clear_btn)

    def _relayout_top(self, compact: bool) -> None:
        """One row when it fits, language on top and actions below when not."""
        if compact == self._top_compact:
            return
        self._top_compact = compact
        widgets = (self.lang_label, self.lang_combo, self.theme_btn,
                   self.log_file_btn, self.about_btn)
        for row in (self._top_row1, self._top_row2):
            for widget in widgets:
                row.removeWidget(widget)
        for widget in (self.lang_label, self.lang_combo, self.theme_btn):
            self._top_row1.addWidget(widget)
        self._top_row1.addStretch()
        if compact:
            self._top_row2.addStretch()
        for widget in (self.log_file_btn, self.about_btn):
            (self._top_row2 if compact else self._top_row1).addWidget(widget)

    def _relayout_queue(self, compact: bool) -> None:
        """Four buttons in a row, or a 2x2 grid when the queue is narrow."""
        if compact == self._queue_compact:
            return
        self._queue_compact = compact
        buttons = (self.add_btn, self.add_dir_btn, self.remove_btn, self.clear_btn)
        grid = self._queue_btns
        for button in buttons:
            grid.removeWidget(button)
        if compact:
            grid.addWidget(self.add_btn, 0, 0)
            grid.addWidget(self.add_dir_btn, 0, 1)
            grid.addWidget(self.remove_btn, 1, 0)
            grid.addWidget(self.clear_btn, 1, 1)
            grid.setColumnStretch(2, 1)
        else:
            for column, button in enumerate(buttons):
                grid.addWidget(button, 0, column)
            grid.setColumnStretch(len(buttons), 1)

    def _relayout_settings(self, compact: bool) -> None:
        """Two settings columns when there is room, stacked when there is not."""
        if compact == self._compact_layout:
            return
        self._compact_layout = compact
        grid = self._settings_grid
        groups = (self.preset_group, self.format_group, self.meta_group,
                  self.perf_group, self.out_group)
        for widget in groups:
            grid.removeWidget(widget)
        for row in range(len(groups) + 2):   # clear stale stretch from the other mode
            grid.setRowStretch(row, 0)
        if compact:
            for row, widget in enumerate(groups):
                grid.addWidget(widget, row, 0)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 0)
            grid.setRowStretch(len(groups), 1)
        else:
            grid.addWidget(self.preset_group, 0, 0)
            grid.addWidget(self.format_group, 1, 0)
            grid.addWidget(self.meta_group, 0, 1)
            grid.addWidget(self.perf_group, 1, 1)
            grid.addWidget(self.out_group, 2, 1)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            grid.setRowStretch(3, 1)

    # ------------------------------------------------------- UI construction --

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 14)
        root.setSpacing(10)
        self._root_margins = root.contentsMargins()

        # The top bar folds onto a second row when the language and buttons no
        # longer fit side by side (narrow window or large fonts).
        self._top_rows = QVBoxLayout()
        self._top_rows.setSpacing(6)
        self._top_row1 = QHBoxLayout()
        self._top_row2 = QHBoxLayout()
        self._top_rows.addLayout(self._top_row1)
        self._top_rows.addLayout(self._top_row2)
        self.lang_label = QLabel()
        self.lang_combo = QComboBox()
        for code, name in LANG_NAMES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(list(LANG_NAMES).index(current_language()))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.log_file_btn = QPushButton()
        self.log_file_btn.clicked.connect(self._open_log)
        self.about_btn = QPushButton()
        self.about_btn.clicked.connect(self._show_about)
        self._top_compact: bool | None = None
        self._relayout_top(compact=False)
        root.addLayout(self._top_rows)

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(10)
        root.addWidget(split, 1)

        # ---- left: queue
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_label = QLabel()
        self.file_list = DropList()
        self.file_list.files_added.connect(self.add_paths)
        self.file_list.itemDoubleClicked.connect(self._show_file_info)
        self.file_list.setToolTip(tr("tooltip_list"))
        self._queue_btns = QGridLayout()
        self._queue_btns.setSpacing(6)
        self.add_btn = QPushButton()
        self.add_btn.clicked.connect(self._pick_files)
        self.add_dir_btn = QPushButton()
        self.add_dir_btn.clicked.connect(self._pick_folder)
        self.remove_btn = QPushButton()
        self.remove_btn.clicked.connect(self._remove_selected)
        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self._clear)
        self._queue_compact: bool | None = None
        self._relayout_queue(compact=False)
        lv.addWidget(self.list_label)
        lv.addWidget(self.file_list, 1)
        lv.addLayout(self._queue_btns)
        split.addWidget(left)

        # ---- right: settings in a scroll area; the arrangement adapts to the
        # available width (two columns when there is room, one when narrow)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.settings_scroll.setFrameShape(QFrame.NoFrame)
        panel = QWidget()
        self._settings_grid = QGridLayout(panel)
        self._settings_grid.setContentsMargins(0, 0, 6, 0)
        self._settings_grid.setHorizontalSpacing(12)
        self._settings_grid.setVerticalSpacing(8)
        self._compact_layout: bool | None = None

        self.preset_group = QGroupBox()
        pg = QVBoxLayout(self.preset_group)
        self.preset_combo = QComboBox()
        for code in PRESETS:
            self.preset_combo.addItem(code, code)
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        pg.addWidget(self.preset_combo)
        # placed by _relayout_settings()

        self.format_group = QGroupBox()
        grid = QGridLayout(self.format_group)
        grid.setVerticalSpacing(8)
        self.image_label = QLabel()
        self.image_combo = QComboBox()
        for code in IMAGE_CODES:
            self.image_combo.addItem(code, code)
        self.image_combo.currentIndexChanged.connect(self._on_manual_change)
        for _combo in (self.image_combo,):
            _combo.setSizeAdjustPolicy(
                QComboBox.AdjustToMinimumContentsLengthWithIcon)
            _combo.setMinimumContentsLength(10)
            _combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.video_label = QLabel()
        self.video_combo = QComboBox()
        for code in VIDEO_CODES:
            self.video_combo.addItem(code, code)
        self.video_combo.currentIndexChanged.connect(self._on_manual_change)
        self.audio_label = QLabel()
        self.audio_combo = QComboBox()
        for code in AUDIO_CODES:
            self.audio_combo.addItem(code, code)
        self.audio_combo.currentIndexChanged.connect(self._on_manual_change)
        grid.addWidget(self.image_label, 0, 0)
        grid.addWidget(self.image_combo, 0, 1)
        grid.addWidget(self.video_label, 1, 0)
        grid.addWidget(self.video_combo, 1, 1)
        grid.addWidget(self.audio_label, 2, 0)
        grid.addWidget(self.audio_combo, 2, 1)
        self.video_note = QLabel()
        self.video_note.setWordWrap(True)
        grid.addWidget(self.video_note, 3, 0, 1, 2)

        qrow = QHBoxLayout()
        self.quality_label = QLabel()
        self.quality_value = QLabel()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(50, 100)
        self.quality_slider.setValue(95)
        self.quality_value.setText(str(self.quality_slider.value()))
        self.quality_slider.valueChanged.connect(self._on_quality)
        qrow.addWidget(self.quality_label)
        qrow.addWidget(self.quality_slider, 1)
        qrow.addWidget(self.quality_value)
        grid.addLayout(qrow, 4, 0, 1, 2)

        rrow = QHBoxLayout()
        self.resize_label = QLabel()
        self.resize_check = QCheckBox()
        self.resize_spin = QSpinBox()
        self.resize_spin.setRange(64, 20000)
        self.resize_spin.setSingleStep(64)
        self.resize_spin.setValue(1920)
        self.resize_spin.setSuffix(" px")
        self.resize_spin.setEnabled(False)
        self.resize_check.toggled.connect(self.resize_spin.setEnabled)
        rrow.addWidget(self.resize_check)
        rrow.addWidget(self.resize_spin)
        rrow.addStretch()
        grid.addLayout(rrow, 5, 0, 1, 2)


        self.meta_group = QGroupBox()
        mv = QVBoxLayout(self.meta_group)
        self.meta_check = QCheckBox()
        self.meta_check.setChecked(True)
        self.timestamps_check = QCheckBox()
        self.timestamps_check.setChecked(True)
        self.date_check = QCheckBox()
        self.meta_note = QLabel()
        self.meta_note.setWordWrap(True)
        for w in (self.meta_check, self.timestamps_check, self.date_check,
                  self.meta_note):
            mv.addWidget(w)


        self.perf_group = QGroupBox()
        pv = QVBoxLayout(self.perf_group)
        self.parallel_check = QCheckBox()
        self.parallel_check.setChecked(True)
        self.gpu_check = QCheckBox()
        self.gpu_check.setChecked(True)
        self.gpu_note = QLabel()
        self.gpu_note.setWordWrap(True)
        self._gpu_encoder = converter.gpu_encoder()
        if not self._gpu_encoder:
            self.gpu_check.setChecked(False)
            self.gpu_check.setEnabled(False)
        for w in (self.parallel_check, self.gpu_check, self.gpu_note):
            pv.addWidget(w)


        self.out_group = QGroupBox()
        ov = QVBoxLayout(self.out_group)
        self.out_same = QRadioButton()
        self.out_same.setChecked(True)
        self.out_custom = QRadioButton()
        self.out_path = QLineEdit()
        self.out_path.setEnabled(False)
        self.out_browse = QPushButton()
        self.out_browse.setEnabled(False)
        self.out_same.toggled.connect(self._update_output_enabled)
        self.out_browse.clicked.connect(self._browse_output)
        self.conflict_label = QLabel()
        self.conflict_combo = QComboBox()
        for code in CONFLICT_CODES:
            self.conflict_combo.addItem(code, code)
        orow = QHBoxLayout()
        orow.addWidget(self.out_path, 1)
        orow.addWidget(self.out_browse)
        crow = QHBoxLayout()
        crow.addWidget(self.conflict_label)
        crow.addWidget(self.conflict_combo, 1)
        ov.addWidget(self.out_same)
        ov.addWidget(self.out_custom)
        ov.addLayout(orow)
        ov.addLayout(crow)
        self.settings_scroll.setWidget(panel)
        self.settings_scroll.viewport().installEventFilter(self)
        split.addWidget(self.settings_scroll)
        self._splitter = split
        self._relayout_settings(compact=False)

        # ---- bottom
        action_row = QHBoxLayout()
        self.convert_btn = QPushButton()
        self.convert_btn.setObjectName("convertBtn")
        self.convert_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        self.open_out_btn = QPushButton()
        self.open_out_btn.setEnabled(False)
        self.open_out_btn.clicked.connect(self._open_output)
        action_row.addWidget(self.convert_btn)
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.open_out_btn)
        action_row.addStretch()
        root.addLayout(action_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status = QLabel()
        self.log = QListWidget()
        self.log.setObjectName("logList")
        self.log.setToolTip(tr("tooltip_log"))
        self.log.itemDoubleClicked.connect(self._show_log_detail)
        root.addWidget(self.progress)
        root.addWidget(self.status)
        root.addWidget(self.log, 1)

        QShortcut(QKeySequence.Delete, self.file_list,
                  activated=self._remove_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._pick_files)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._start)

    # ---------------------------------------------------------------- i18n --

    @staticmethod
    def _detect_language() -> str:
        return "zh" if QLocale.system().name().lower().startswith("zh") else "en"

    def _on_language_changed(self, index: int):
        set_language(self.lang_combo.itemData(index))
        self._settings.setValue("language", current_language())
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(tr("window_title"))
        self.lang_label.setText(tr("language") + ":")
        self.theme_btn.setText(tr("theme_dark") if self._theme == "light"
                               else tr("theme_light"))
        self.log_file_btn.setText(tr("view_log"))
        self.about_btn.setText(tr("menu_about"))
        self._refresh_list_label()
        self.add_btn.setText(tr("add_files"))
        self.add_dir_btn.setText(tr("add_folder"))
        self.remove_btn.setText(tr("remove"))
        self.clear_btn.setText(tr("clear"))
        self.preset_group.setTitle(tr("group_preset"))
        for i in range(self.preset_combo.count()):
            code = self.preset_combo.itemData(i)
            self.preset_combo.setItemText(i, tr("preset_" + code))
        self.preset_combo.setToolTip(tr("preset_note"))
        self.format_group.setTitle(tr("group_format"))
        self.image_label.setText(tr("image_format"))
        self.video_label.setText(tr("video_format"))
        self.audio_label.setText(tr("audio_format"))
        for combo, prefix in ((self.image_combo, "image"),
                              (self.video_combo, "video"),
                              (self.audio_combo, "audio")):
            for i in range(combo.count()):
                code = combo.itemData(i)
                key = (FMT_KEY.get(code, FMT_PREFIX[prefix] + code.lower())
                       if prefix == "image"
                       else FMT_PREFIX[prefix] + code.lower())
                combo.setItemText(i, tr(key))
        self.video_note.setText(tr("video_note"))
        self.quality_label.setText(tr("quality"))
        self.resize_check.setText(tr("resize_enable"))
        self.resize_label.setText(tr("resize"))
        self.meta_group.setTitle(tr("group_metadata"))
        self.meta_check.setText(tr("keep_metadata"))
        self.timestamps_check.setText(tr("keep_timestamps"))
        self.date_check.setText(tr("organize_by_date"))
        self.meta_note.setText(tr("metadata_note"))
        self.perf_group.setTitle(tr("group_performance"))
        self.parallel_check.setText(tr("parallel_tip"))
        self.gpu_check.setText(tr("gpu_tip"))
        self.gpu_note.setText(tr("gpu_found", name=self._gpu_encoder)
                              if self._gpu_encoder else tr("gpu_none"))
        self.out_group.setTitle(tr("group_output"))
        self.out_same.setText(tr("out_same"))
        self.out_custom.setText(tr("out_custom"))
        self.out_browse.setText(tr("browse"))
        self.conflict_label.setText(tr("conflict"))
        for i in range(self.conflict_combo.count()):
            code = self.conflict_combo.itemData(i)
            self.conflict_combo.setItemText(i, tr("conflict_" + code))
        self.convert_btn.setText(tr("convert"))
        self.cancel_btn.setText(tr("cancel"))
        self.open_out_btn.setText(tr("open_output"))
        if self.progress.value() == 0:
            self.status.setText(tr("status_ready"))

    # -------------------------------------------------------------- theme --

    def _apply_theme(self):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(theme_qss(self._theme == "dark"))
        self.theme_btn.setText(tr("theme_dark") if self._theme == "light"
                               else tr("theme_light"))

    def _toggle_theme(self):
        self._theme = "dark" if self._theme == "light" else "light"
        self._settings.setValue("theme", self._theme)
        self._apply_theme()

    # ----------------------------------------------------------- settings --

    def _load_settings(self):
        s = self._settings
        def pick(combo, key, default):
            val = s.value(key, default)
            idx = combo.findData(val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        pick(self.image_combo, "image_format", "JPEG")
        pick(self.video_combo, "video_format", "MP4")
        pick(self.audio_combo, "audio_format", "MP3")
        pick(self.conflict_combo, "conflict", "rename")
        pick(self.preset_combo, "preset", "custom")
        self.quality_slider.setValue(int(s.value("quality", 95)))
        self.resize_check.setChecked(s.value("resize_enabled", False, type=bool))
        self.resize_spin.setValue(int(s.value("resize_px", 1920)))
        self.resize_spin.setEnabled(self.resize_check.isChecked())
        self.meta_check.setChecked(s.value("keep_metadata", True, type=bool))
        self.timestamps_check.setChecked(s.value("keep_ts", True, type=bool))
        self.date_check.setChecked(s.value("by_date", False, type=bool))
        self.parallel_check.setChecked(s.value("parallel", True, type=bool))
        if self._gpu_encoder:
            self.gpu_check.setChecked(s.value("gpu", True, type=bool))
        out_dir = s.value("output_dir", "")
        if out_dir:
            self.out_custom.setChecked(True)
            self.out_path.setText(str(out_dir))
        self._update_output_enabled()

    def _save_settings(self):
        s = self._settings
        s.setValue("image_format", self.image_combo.currentData())
        s.setValue("video_format", self.video_combo.currentData())
        s.setValue("audio_format", self.audio_combo.currentData())
        s.setValue("conflict", self.conflict_combo.currentData())
        s.setValue("preset", self.preset_combo.currentData())
        s.setValue("quality", self.quality_slider.value())
        s.setValue("resize_enabled", self.resize_check.isChecked())
        s.setValue("resize_px", self.resize_spin.value())
        s.setValue("keep_metadata", self.meta_check.isChecked())
        s.setValue("keep_ts", self.timestamps_check.isChecked())
        s.setValue("by_date", self.date_check.isChecked())
        s.setValue("parallel", self.parallel_check.isChecked())
        s.setValue("gpu", self.gpu_check.isChecked())
        s.setValue("output_dir", self.out_path.text() if self.out_custom.isChecked()
                   else "")
        s.setValue("geometry", self.saveGeometry())

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    # -------------------------------------------------------------- queue --

    def _refresh_list_label(self):
        n = self.file_list.count()
        self.list_label.setText(tr("list_header", n=n) if n
                                else tr("list_empty"))

    def add_paths(self, paths: list[str]):
        existing = {self.file_list.item(i).text()
                    for i in range(self.file_list.count())}
        added = 0
        for raw in paths:
            p = Path(raw)
            if p.is_dir():
                for f in converter.scan_folder(p, recursive=True):
                    if str(f) not in existing:
                        existing.add(str(f))
                        self.file_list.addItem(str(f))
                        added += 1
            elif p.suffix.lower() in DROP_EXTS and str(p) not in existing:
                existing.add(str(p))
                self.file_list.addItem(str(p))
                added += 1
        self._refresh_list_label()
        if added:
            self.status.setText(tr("status_added", n=added))

    def _pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("dialog_title"), "", tr("dialog_filter"))
        if files:
            self.add_paths(files)

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, tr("dialog_folder"))
        if d:
            self.add_paths([d])

    def _remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self._refresh_list_label()

    def _clear(self):
        self.file_list.clear()
        self.log.clear()
        self.progress.setValue(0)
        self._refresh_list_label()
        self.status.setText(tr("status_ready"))

    def _show_file_info(self, item: QListWidgetItem):
        from .cli import cmd_info
        QApplication.clipboard()  # no-op; keeps import local & lazy
        cmd_info([item.text()])

    # ------------------------------------------------------------ options --

    def _selected_format(self) -> str:
        return self.image_combo.currentData() or "JPEG"

    def _on_quality(self, value: int):
        self.quality_value.setText(str(value))
        self._mark_custom()

    def _on_manual_change(self):
        self._mark_custom()
        self._update_quality_enabled()

    def _mark_custom(self):
        idx = self.preset_combo.findData("custom")
        if idx >= 0 and self.preset_combo.currentIndex() != idx:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(idx)
            self.preset_combo.blockSignals(False)

    def _apply_preset(self):
        code = self.preset_combo.currentData()
        if code == "custom":
            self._save_settings()
            return
        img, vid, aud, quality, resize = PRESETS[code]
        for combo, val in ((self.image_combo, img), (self.video_combo, vid),
                           (self.audio_combo, aud)):
            idx = combo.findData(val)
            if idx >= 0:
                combo.blockSignals(True)
                combo.setCurrentIndex(idx)
                combo.blockSignals(False)
        self.quality_slider.blockSignals(True)
        self.quality_slider.setValue(quality)
        self.quality_slider.blockSignals(False)
        self.quality_value.setText(str(quality))
        self.resize_check.setChecked(resize > 0)
        if resize > 0:
            self.resize_spin.setValue(resize)
        self._update_quality_enabled()
        self._save_settings()

    def _update_quality_enabled(self):
        self.quality_slider.setEnabled(
            self._selected_format() in ("JPEG", "WEBP", "AVIF"))

    def _update_output_enabled(self):
        custom = self.out_custom.isChecked()
        self.out_path.setEnabled(custom)
        self.out_browse.setEnabled(custom)

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, tr("browse"))
        if d:
            self.out_path.setText(d)

    def _options(self) -> converter.ConvertOptions:
        return converter.ConvertOptions(
            image_format=self._selected_format(),
            video_format=self.video_combo.currentData() or "MP4",
            audio_format=self.audio_combo.currentData() or "MP3",
            quality=self.quality_slider.value(),
            keep_metadata=self.meta_check.isChecked(),
            keep_timestamps=self.timestamps_check.isChecked(),
            parallel=self.parallel_check.isChecked(),
            use_gpu=self.gpu_check.isChecked(),
            resize_long_edge=(self.resize_spin.value()
                              if self.resize_check.isChecked() else 0),
            conflict=self.conflict_combo.currentData() or "rename",
            organize_by_date=self.date_check.isChecked(),
        )

    # ------------------------------------------------------------- convert --

    def _start(self):
        if self.file_list.count() == 0:
            QMessageBox.information(self, APP_NAME, tr("err_no_files"))
            return
        opts = self._options()
        self._save_settings()

        if opts.organize_by_date and self.out_same.isChecked():
            self.out_custom.setChecked(True)
            if not self.out_path.text().strip():
                first = Path(self.file_list.item(0).text())
                self.out_path.setText(str(first.parent))
        default_dir = (Path(self.out_path.text().strip())
                       if self.out_custom.isChecked() and self.out_path.text().strip()
                       else None)

        jobs = []
        for i in range(self.file_list.count()):
            src = Path(self.file_list.item(i).text())
            jobs.append((src, default_dir or src.parent))

        needs_ffmpeg = any(converter.detect_kind(s) in ("video", "audio")
                           for s, _ in jobs)
        if needs_ffmpeg and not converter.ffmpeg_available():
            QMessageBox.warning(self, APP_NAME, tr("ffmpeg_missing"))

        self.log.clear()
        self._errors.clear()
        self.progress.setRange(0, len(jobs))
        self.progress.setValue(0)
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.file_list.setEnabled(False)
        self._worker = ConvertWorker(jobs, opts)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_progress(self, done: int, total: int, name: str):
        self.status.setText(tr("status_converting", i=done, n=total, name=name))

    def _on_file_done(self, name: str, out: str, ok: bool, msg: str,
                      in_b: int, out_b: int, skipped: bool):
        if skipped:
            self.log.addItem(f"⏭ {name} — {msg}")
        elif ok:
            delta = ""
            if in_b and out_b:
                delta = tr("size_delta",
                           pct=abs((1 - out_b / in_b) * 100),
                           arrow="↓" if out_b <= in_b else "↑")
            self.log.addItem(tr("log_ok", name=name, out=msg, detail=delta))
            if out:
                self._last_output = Path(out).parent
        else:
            self._errors[name] = msg
            self.log.addItem(tr("log_fail", name=name, reason=msg))
        self.progress.setValue(self.progress.value() + 1)

    def _on_all_done(self, stats):
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.file_list.setEnabled(True)
        self.open_out_btn.setEnabled(self._last_output is not None)
        processed = stats.ok + stats.fail + stats.skipped
        if processed < self.file_list.count():
            self.status.setText(tr("status_cancelled"))
            return
        elapsed = stats.seconds
        speed = (processed / elapsed) if elapsed > 0 else 0
        self.status.setText(tr("status_done", ok=stats.ok, fail=stats.fail,
                              skip=stats.skipped, secs=elapsed, speed=speed))
        if stats.in_bytes and stats.out_bytes:
            self.log.addItem(tr("log_summary",
                                inb=converter_human(stats.in_bytes),
                                outb=converter_human(stats.out_bytes),
                                pct=abs(stats.savings_pct)))

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
            self.status.setText(tr("status_cancelling"))

    def _open_output(self):
        if self._last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output)))

    def _open_log(self):
        lf = converter.log_file()
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(lf if lf.exists() else lf.parent)))

    def _show_log_detail(self, item: QListWidgetItem):
        text = item.text()
        for name, msg in self._errors.items():
            if name in text:
                body = (f"{name}\n\n{msg}\n\n"
                        f"{tr('log_detail_hint')}\n{converter.log_file()}")
                ErrorDialog(self, tr("error_detail"), body).exec()
                return

    def _show_about(self):
        QMessageBox.about(self, tr("menu_about"),
                          tr("about_text", version=__version__, repo=APP_REPO))


def converter_human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} GB"


def run_app(argv: list[str] | None = None) -> int:
    app = QApplication(argv or [])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()
