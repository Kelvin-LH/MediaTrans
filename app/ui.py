"""Main window for MediaTrans (PySide6, bilingual EN/中文, modern theme)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PySide6.QtCore import QLocale, QMutex, QMutexLocker, QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QMainWindow, QMessageBox,
                               QProgressBar, QPushButton, QRadioButton, QSlider,
                               QSplitter, QVBoxLayout, QWidget)

from . import __version__, APP_NAME, APP_REPO, converter
from .i18n import LANG_NAMES, current_language, set_language, tr

DROP_EXTS = converter.IMAGE_EXTS | converter.VIDEO_EXTS

IMAGE_CODES = list(converter.IMAGE_FORMATS)   # JPEG, PNG, WEBP, AVIF, TIFF, BMP, PDF, GIF
VIDEO_CODES = list(converter.VIDEO_FORMATS)   # MP4, MKV, WEBM, GIF, MP3

FMT_KEY = {"JPEG": "fmt_jpg"}  # i18n key overrides for format codes

QSS = """
* { outline: none; }
QMainWindow, QWidget { background: #eef1f6; color: #1f2430; font-size: 13px; }
QLabel { background: transparent; }

QGroupBox {
    background: #ffffff;
    border: 1px solid #e3e8f2;
    border-radius: 12px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px; top: 4px;
    padding: 0 6px;
    color: #6d5dfc;
}

QListWidget#fileList {
    background: #fbfcff;
    border: 2px dashed #c9d2e6;
    border-radius: 12px;
    padding: 8px;
    font-size: 13px;
}
QListWidget#fileList::item { padding: 6px 8px; border-radius: 6px; }
QListWidget#fileList::item:selected { background: #ece7ff; color: #1f2430; }
QListWidget#fileList::item:hover:!selected { background: #f1f0fb; }

QListWidget#logList {
    background: #ffffff;
    border: 1px solid #e3e8f2;
    border-radius: 12px;
    padding: 6px;
    font-size: 12px;
    color: #4b5563;
}

QPushButton {
    background: #ffffff;
    border: 1px solid #d5dbe8;
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 500;
}
QPushButton:hover { border-color: #6d5dfc; color: #6d5dfc; }
QPushButton:pressed { background: #f1eeff; }
QPushButton:disabled { color: #9aa3b2; border-color: #e3e8f2; background: #f4f6fa; }

QPushButton#convertBtn {
    background: #6d5dfc; color: #ffffff; border: none;
    font-weight: 600; padding: 8px 26px; font-size: 14px;
}
QPushButton#convertBtn:hover { background: #5b49f2; }
QPushButton#convertBtn:disabled { background: #c7c2f5; color: #f4f3ff; }

QProgressBar {
    background: #e3e8f2; border: none; border-radius: 7px;
    height: 14px; text-align: center; color: transparent; font-size: 10px;
}
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6d5dfc, stop:1 #00b4d8); border-radius: 7px; }

QSlider { min-height: 22px; }
QSlider::groove:horizontal { height: 6px; background: #e3e8f2; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #b3a8ff; border-radius: 3px; }
QSlider::handle:horizontal {
    width: 16px; height: 16px; margin: -5px 0;
    border-radius: 8px; background: #6d5dfc;
}
QSlider::handle:horizontal:hover { background: #5b49f2; }

QComboBox {
    background: #ffffff; border: 1px solid #d5dbe8;
    border-radius: 8px; padding: 5px 30px 5px 10px;
    min-height: 20px;
}
QComboBox:hover { border-color: #6d5dfc; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: #ffffff; border: 1px solid #d5dbe8;
    selection-background-color: #ece7ff; selection-color: #1f2430;
}

QCheckBox, QRadioButton { spacing: 8px; background: transparent; }
QCheckBox::indicator {
    width: 17px; height: 17px;
    border: 1px solid #c9d2e6; border-radius: 5px; background: #ffffff;
}
QCheckBox::indicator:hover { border-color: #6d5dfc; }
QCheckBox::indicator:checked {
    background: #6d5dfc; border-color: #6d5dfc;
    image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png);
}
QRadioButton::indicator {
    width: 17px; height: 17px;
    border: 1px solid #c9d2e6; border-radius: 9px; background: #ffffff;
}
QRadioButton::indicator:hover { border-color: #6d5dfc; }
QRadioButton::indicator:checked {
    border: 5px solid #6d5dfc; background: #ffffff; width: 7px; height: 7px;
}

QLineEdit {
    background: #ffffff; border: 1px solid #d5dbe8;
    border-radius: 8px; padding: 6px 10px;
}
QLineEdit:focus { border-color: #6d5dfc; }
QLineEdit:disabled { background: #f4f6fa; color: #9aa3b2; }

QSplitter::handle { background: transparent; width: 6px; }
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
    from PySide6.QtGui import QFont
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
        self.setAlternatingRowColors(False)

    def _paths(self, event) -> list[str]:
        return [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]

    def dragEnterEvent(self, event):
        if any(Path(p).suffix.lower() in DROP_EXTS for p in self._paths(event)):
            self.setStyleSheet("QListWidget#fileList { border-color: #6d5dfc; background: #f3f0ff; }")
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
        paths = [p for p in self._paths(event) if Path(p).suffix.lower() in DROP_EXTS]
        if paths:
            self.files_added.emit(paths)
            event.acceptProposedAction()


class ConvertWorker(QThread):
    progress = Signal(int, int, str)          # started(1-based), total, filename
    file_done = Signal(str, str, bool, str)   # filename, output, ok, detail
    all_done = Signal(int, int, bool)         # ok, fail, cancelled

    def __init__(self, jobs: list[tuple[Path, Path]], opts: converter.ConvertOptions):
        super().__init__()
        self._jobs = jobs
        self._opts = opts
        self._cancelled = False
        self._total = len(jobs)
        self._started = 0
        self._ok = 0
        self._fail = 0
        self._lock = QMutex()

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self._opts.parallel and self._total > 1:
            workers = min(self._total, converter.cpu_workers())
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = [ex.submit(self._convert_one, src, d)
                           for src, d in self._jobs]
                for f in as_completed(futures):
                    f.result()
        else:
            for src, d in self._jobs:
                self._convert_one(src, d)
        self.all_done.emit(self._ok, self._fail, self._cancelled)

    def _convert_one(self, src: Path, dst_dir: Path):
        if self._cancelled:
            return
        with QMutexLocker(self._lock):
            self._started += 1
            self.progress.emit(self._started, self._total, src.name)
        result = converter.convert_file(src, dst_dir, self._opts)
        out = str(result.output) if result.output else ""
        with QMutexLocker(self._lock):
            self._ok += result.ok
            self._fail += not result.ok
        self.file_done.emit(src.name, out, result.ok, result.message)


class MainWindow(QMainWindow):
    def __init__(self, language: str | None = None):
        super().__init__()
        self._settings = QSettings(APP_NAME, APP_NAME)
        lang = language or self._settings.value("language", None) or self._detect_language()
        set_language(lang)

        self._worker: ConvertWorker | None = None
        self._last_output: Path | None = None

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self._build_ui()
        self.retranslate()
        self.resize(1000, 960)
        self.setMinimumSize(900, 920)

    # ---------- UI construction ----------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 14)
        root.setSpacing(10)

        # -- top bar: language + about
        top = QHBoxLayout()
        self.lang_label = QLabel()
        self.lang_combo = QComboBox()
        for code, name in LANG_NAMES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(list(LANG_NAMES).index(current_language()))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        top.addWidget(self.lang_label)
        top.addWidget(self.lang_combo)
        top.addStretch()
        self.log_file_btn = QPushButton()
        self.log_file_btn.clicked.connect(self._open_log)
        top.addWidget(self.log_file_btn)
        self.about_btn = QPushButton()
        self.about_btn.clicked.connect(self._show_about)
        top.addWidget(self.about_btn)
        root.addLayout(top)

        # -- middle: file list | settings
        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(10)
        root.addWidget(split, 1)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.list_label = QLabel()
        self.file_list = DropList()
        self.file_list.files_added.connect(self.add_files)
        btns = QHBoxLayout()
        self.add_btn = QPushButton()
        self.add_btn.clicked.connect(self._pick_files)
        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self.file_list.clear)
        btns.addWidget(self.add_btn)
        btns.addWidget(self.clear_btn)
        btns.addStretch()
        lv.addWidget(self.list_label)
        lv.addWidget(self.file_list, 1)
        lv.addLayout(btns)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)

        self.format_group = QGroupBox()
        grid = QGridLayout(self.format_group)
        grid.setVerticalSpacing(8)
        self.image_label = QLabel()
        self.image_combo = QComboBox()
        for code in IMAGE_CODES:
            self.image_combo.addItem(code, code)
        self.image_combo.currentIndexChanged.connect(self._update_quality_enabled)
        self.video_label = QLabel()
        self.video_combo = QComboBox()
        for code in VIDEO_CODES:
            self.video_combo.addItem(code, code)
        grid.addWidget(self.image_label, 0, 0)
        grid.addWidget(self.image_combo, 0, 1)
        grid.addWidget(self.video_label, 1, 0)
        grid.addWidget(self.video_combo, 1, 1)
        self.video_note = QLabel()
        self.video_note.setWordWrap(True)
        sp = self.video_note.sizePolicy()
        sp.setHeightForWidth(True)
        self.video_note.setSizePolicy(sp)
        self.video_note.setFixedHeight(48)
        grid.addWidget(self.video_note, 2, 0, 1, 2)

        qrow = QHBoxLayout()
        self.quality_label = QLabel()
        self.quality_value = QLabel()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(60, 100)
        self.quality_slider.setValue(95)
        self.quality_value.setText(str(self.quality_slider.value()))
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_value.setText(str(v)))
        qrow.addWidget(self.quality_label)
        qrow.addWidget(self.quality_slider, 1)
        qrow.addWidget(self.quality_value)
        grid.addLayout(qrow, 3, 0, 1, 2)
        rv.addWidget(self.format_group)

        self.meta_group = QGroupBox()
        mv = QVBoxLayout(self.meta_group)
        self.meta_check = QCheckBox()
        self.meta_check.setChecked(True)
        self.meta_note = QLabel()
        self.meta_note.setWordWrap(True)
        mv.addWidget(self.meta_check)
        mv.addWidget(self.meta_note)
        rv.addWidget(self.meta_group)

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
        pv.addWidget(self.parallel_check)
        pv.addWidget(self.gpu_check)
        pv.addWidget(self.gpu_note)
        rv.addWidget(self.perf_group)

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
        orow = QHBoxLayout()
        orow.addWidget(self.out_path, 1)
        orow.addWidget(self.out_browse)
        ov.addWidget(self.out_same)
        ov.addWidget(self.out_custom)
        ov.addLayout(orow)
        rv.addWidget(self.out_group)
        rv.addStretch()
        split.addWidget(right)
        split.setSizes([420, 470])

        # -- bottom: actions + progress + log
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
        self.status.setStyleSheet("color: #6b7280;")
        self.log = QListWidget()
        self.log.setObjectName("logList")
        self.log.setMinimumHeight(70)
        root.addWidget(self.progress)
        root.addWidget(self.status)
        root.addWidget(self.log, 1)

    # ---------- i18n ----------

    @staticmethod
    def _detect_language() -> str:
        return "zh" if QLocale.system().name().lower().startswith("zh") else "en"

    def _on_language_changed(self, index: int):
        code = self.lang_combo.itemData(index)
        set_language(code)
        self._settings.setValue("language", code)
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(tr("window_title"))
        self.lang_label.setText(tr("language") + ":")
        self.log_file_btn.setText(tr("view_log"))
        self.about_btn.setText(tr("menu_about"))
        self.list_label.setText(tr("list_header", n=self.file_list.count()))
        self.add_btn.setText(tr("add_files"))
        self.clear_btn.setText(tr("clear"))
        self.format_group.setTitle(tr("group_format"))
        self.image_label.setText(tr("image_format"))
        self.video_label.setText(tr("video_format"))
        for i in range(self.image_combo.count()):
            code = self.image_combo.itemData(i)
            self.image_combo.setItemText(i, tr(FMT_KEY.get(code, "fmt_" + code.lower())))
        for i in range(self.video_combo.count()):
            code = self.video_combo.itemData(i)
            self.video_combo.setItemText(i, tr("vfmt_" + code.lower()))
        self.video_note.setText(tr("video_note"))
        self.quality_label.setText(tr("quality"))
        self.meta_group.setTitle(tr("group_metadata"))
        self.meta_check.setText(tr("keep_metadata"))
        self.meta_note.setText(tr("metadata_note"))
        self.perf_group.setTitle(tr("group_performance"))
        self.parallel_check.setText(tr("parallel_tip"))
        self.gpu_check.setText(tr("gpu_tip"))
        if self._gpu_encoder:
            self.gpu_note.setText(tr("gpu_found", name=self._gpu_encoder))
        else:
            self.gpu_note.setText(tr("gpu_none"))
        self.out_group.setTitle(tr("group_output"))
        self.out_same.setText(tr("out_same"))
        self.out_custom.setText(tr("out_custom"))
        self.out_browse.setText(tr("browse"))
        self.convert_btn.setText(tr("convert"))
        self.cancel_btn.setText(tr("cancel"))
        self.open_out_btn.setText(tr("open_output"))
        if self.progress.value() == 0:
            self.status.setText(tr("status_ready"))

    # ---------- helpers ----------

    def _selected_format(self) -> str:
        return self.image_combo.currentData() or "JPEG"

    def _update_quality_enabled(self):
        fmt = self._selected_format()
        self.quality_slider.setEnabled(fmt in ("JPEG", "WEBP", "AVIF"))

    def _update_output_enabled(self):
        custom = self.out_custom.isChecked()
        self.out_path.setEnabled(custom)
        self.out_browse.setEnabled(custom)

    def add_files(self, paths: list[str]):
        existing = {self.file_list.item(i).text()
                    for i in range(self.file_list.count())}
        for p in paths:
            if p not in existing and Path(p).suffix.lower() in DROP_EXTS:
                self.file_list.addItem(p)
        self.list_label.setText(tr("list_header", n=self.file_list.count()))

    def _pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("dialog_title"), "", tr("dialog_filter"))
        if files:
            self.add_files(files)

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, tr("browse"))
        if d:
            self.out_path.setText(d)

    def _start(self):
        if self.file_list.count() == 0:
            QMessageBox.information(self, APP_NAME, tr("err_no_files"))
            return
        if self.out_custom.isChecked() and self.out_path.text().strip():
            default_dir = Path(self.out_path.text().strip())
        else:
            default_dir = None  # per-file: same directory as the source

        jobs = []
        for i in range(self.file_list.count()):
            src = Path(self.file_list.item(i).text())
            jobs.append((src, default_dir or src.parent))

        opts = converter.ConvertOptions(
            image_format=self._selected_format(),
            video_format=self.video_combo.currentData() or "MP4",
            quality=self.quality_slider.value(),
            keep_metadata=self.meta_check.isChecked(),
            parallel=self.parallel_check.isChecked(),
            use_gpu=self.gpu_check.isChecked(),
        )
        if not converter.ffmpeg_available():
            has_video = any(converter.detect_kind(s) == "video" for s, _ in jobs)
            if has_video:
                QMessageBox.warning(self, APP_NAME, tr("ffmpeg_missing"))

        self.log.clear()
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

    def _on_progress(self, i: int, total: int, name: str):
        self.status.setText(tr("status_converting", i=i, n=total, name=name))

    def _on_file_done(self, name: str, out: str, ok: bool, detail: str):
        if ok:
            self.log.addItem(tr("log_ok", name=name, out=out, detail=detail))
            if out:
                self._last_output = Path(out).parent
        else:
            self.log.addItem(tr("log_fail", name=name, reason=detail))
        self.progress.setValue(self.progress.value() + 1)

    def _on_all_done(self, ok: int, fail: int, cancelled: bool):
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.file_list.setEnabled(True)
        self.open_out_btn.setEnabled(self._last_output is not None)
        if cancelled:
            self.status.setText(tr("status_cancelled"))
        else:
            self.status.setText(tr("status_done", ok=ok, fail=fail))

    def _cancel(self):
        if self._worker:
            self._worker.cancel()

    def _open_output(self):
        if self._last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output)))

    def _open_log(self):
        lf = converter.log_file()
        if lf.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(lf)))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(lf.parent)))

    def _show_about(self):
        QMessageBox.about(
            self, tr("menu_about"),
            tr("about_text", version=__version__, repo=APP_REPO))


def run_app(argv: list[str] | None = None) -> int:
    app = QApplication(argv or [])
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    window = MainWindow()
    window.show()
    return app.exec()
