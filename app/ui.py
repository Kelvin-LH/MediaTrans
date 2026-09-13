"""Main window for MediaTrans (PySide6, bilingual EN/中文)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLocale, QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import (QAction, QDesktopServices, QIcon, QLinearGradient,
                           QPainter, QColor, QFont, QPixmap)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QMainWindow, QMessageBox,
                               QProgressBar, QPushButton, QRadioButton, QSlider,
                               QSplitter, QVBoxLayout, QWidget)

from . import __version__, APP_NAME, APP_REPO, converter
from .i18n import LANG_NAMES, current_language, set_language, tr

DROP_EXTS = converter.IMAGE_EXTS | converter.VIDEO_EXTS


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
    p.drawText(pm.rect(), Qt.AlignCenter, "M⇄")
    p.end()
    return QIcon(pm)


class DropList(QListWidget):
    files_added = Signal(list)

    def _paths(self, event) -> list[str]:
        return [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]

    def dragEnterEvent(self, event):
        if any(Path(p).suffix.lower() in DROP_EXTS for p in self._paths(event)):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [p for p in self._paths(event) if Path(p).suffix.lower() in DROP_EXTS]
        if paths:
            self.files_added.emit(paths)
            event.acceptProposedAction()


class ConvertWorker(QThread):
    progress = Signal(int, int, str)          # index(0-based), total, filename
    file_done = Signal(str, str, bool, str)   # filename, output, ok, detail
    all_done = Signal(int, int, bool)         # ok, fail, cancelled

    def __init__(self, jobs: list[tuple[Path, Path]], opts: converter.ConvertOptions):
        super().__init__()
        self._jobs = jobs
        self._opts = opts
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        ok = fail = 0
        total = len(self._jobs)
        for i, (src, dst_dir) in enumerate(self._jobs):
            if self._cancelled:
                break
            self.progress.emit(i, total, src.name)
            result = converter.convert_file(src, dst_dir, self._opts)
            out = str(result.output) if result.output else ""
            self.file_done.emit(src.name, out, result.ok, result.message)
            ok += result.ok
            fail += not result.ok
        self.all_done.emit(ok, fail, self._cancelled)


class MainWindow(QMainWindow):
    def __init__(self, language: str | None = None):
        super().__init__()
        self._settings = QSettings(APP_NAME, APP_NAME)
        lang = language or self._settings.value("language", None) or self._detect_language()
        set_language(lang)

        self._worker: ConvertWorker | None = None
        self._last_output: Path | None = None
        self._about: QMessageBox | None = None

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self._build_ui()
        self.retranslate()
        self.resize(900, 640)

    # ---------- UI construction ----------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # -- top bar: language + help
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
        self.about_btn = QPushButton()
        self.about_btn.clicked.connect(self._show_about)
        top.addWidget(self.about_btn)
        root.addLayout(top)

        # -- middle: file list | settings
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split, 1)

        left = QWidget()
        lv = QVBoxLayout(left)
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

        self.format_group = QGroupBox()
        fv = QVBoxLayout(self.format_group)
        self.rb_jpg = QRadioButton()
        self.rb_jpg.setChecked(True)
        self.rb_png = QRadioButton()
        self.rb_webp = QRadioButton()
        for rb in (self.rb_jpg, self.rb_png, self.rb_webp):
            rb.toggled.connect(self._update_quality_enabled)
            fv.addWidget(rb)
        self.video_note = QLabel()
        self.video_note.setWordWrap(True)
        self.video_note.setMinimumHeight(40)
        fv.addWidget(self.video_note)

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
        fv.addLayout(qrow)
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
        split.setSizes([430, 440])

        # -- bottom: actions + progress + log
        action_row = QHBoxLayout()
        self.convert_btn = QPushButton()
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
        self.about_btn.setText(tr("menu_about"))
        self.list_label.setText(tr("list_header", n=self.file_list.count()))
        self.add_btn.setText(tr("add_files"))
        self.clear_btn.setText(tr("clear"))
        self.format_group.setTitle(tr("group_format"))
        self.rb_jpg.setText(tr("fmt_jpg"))
        self.rb_png.setText(tr("fmt_png"))
        self.rb_webp.setText(tr("fmt_webp"))
        self.video_note.setText(tr("video_note"))
        self.quality_label.setText(tr("quality"))
        self.meta_group.setTitle(tr("group_metadata"))
        self.meta_check.setText(tr("keep_metadata"))
        self.meta_note.setText(tr("metadata_note"))
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
        if self.rb_png.isChecked():
            return "PNG"
        if self.rb_webp.isChecked():
            return "WEBP"
        return "JPEG"

    def _update_quality_enabled(self):
        fmt = self._selected_format()
        self.quality_slider.setEnabled(fmt in ("JPEG", "WEBP"))

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
            quality=self.quality_slider.value(),
            keep_metadata=self.meta_check.isChecked(),
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
        self.status.setText(tr("status_converting", i=i + 1, n=total, name=name))

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

    def _show_about(self):
        QMessageBox.about(
            self, tr("menu_about"),
            tr("about_text", version=__version__, repo=APP_REPO))


def run_app(argv: list[str] | None = None) -> int:
    app = QApplication(argv or [])
    window = MainWindow()
    window.show()
    return app.exec()
