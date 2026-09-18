"""Integration test for the GUI conversion worker.

Runs a real batch through ConvertWorker with the offscreen Qt platform, so the
exact code path the desktop app uses (signal wiring, parallelism, batch stats,
cancellation) is exercised without opening a window.

    python tests/test_worker.py
"""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QCoreApplication, QTimer

from app import converter
from app.ui import ConvertWorker
from tests.test_converter import make_test_heic, make_test_mov

# legacy Windows code pages cannot print every message verbatim
for _stream in (sys.stdout, sys.stderr):
    with contextlib.suppress(AttributeError, ValueError, OSError):
        _stream.reconfigure(errors="replace")

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def run_batch(app, jobs, opts, cancel_after: int | None = None):
    """Drive ConvertWorker to completion, returning collected signals."""
    seen = {"progress": [], "files": [], "stats": None}
    worker = ConvertWorker(jobs, opts)
    worker.progress.connect(lambda d, t, n: seen["progress"].append((d, t, n)))
    worker.file_done.connect(
        lambda n, out, ok, msg, ib, ob, sk: seen["files"].append((n, out, ok, sk)))
    worker.all_done.connect(lambda s: seen.__setitem__("stats", s))

    if cancel_after is not None:
        timer = QTimer()
        timer.timeout.connect(lambda: (worker.cancel(), timer.stop()))
        timer.start(1)

    worker.start()
    while not worker.isFinished():
        app.processEvents()
    worker.wait(30000)
    # all_done is emitted from the worker thread as the run ends; drain the
    # queued signal delivery so the final callback is observed reliably.
    for _ in range(50):
        app.processEvents()
        if seen["stats"] is not None:
            break
        time.sleep(0.01)
    return seen, worker


def main():
    app = QCoreApplication([])
    with tempfile.TemporaryDirectory(prefix="mediatrans_worker_") as d:
        tmp = Path(d)
        src_dir = tmp / "src"
        src_dir.mkdir()
        for i in range(3):
            make_test_heic(src_dir / f"IMG_{i:04d}.heic")
        make_test_mov(src_dir / "VID_0000.mov")

        paths = sorted(src_dir.iterdir())
        jobs = [(p, tmp / "out") for p in paths]

        # -- parallel batch
        opts = converter.ConvertOptions(image_format="WEBP", video_format="MP4")
        seen, worker = run_batch(app, jobs, opts)
        check("worker: finished", worker.isFinished())
        check("worker: every file reported",
              len(seen["files"]) == len(jobs), str(len(seen["files"])))
        check("worker: all conversions succeeded",
              all(f[2] for f in seen["files"]),
              str([f for f in seen["files"] if not f[2]]))
        check("worker: outputs written",
              all(Path(f[1]).exists() for f in seen["files"]),
              " ".join(f[1] for f in seen["files"]))
        check("worker: progress reached the total",
              seen["progress"] and seen["progress"][-1][0] == len(jobs),
              str(seen["progress"]))
        stats = seen["stats"]
        check("worker: stats aggregated",
              stats is not None and stats.ok == len(jobs) and stats.fail == 0,
              str(stats))
        check("worker: byte totals tracked",
              stats.in_bytes > 0 and stats.out_bytes > 0)

        # -- serial batch, different destination per file
        opts_serial = converter.ConvertOptions(image_format="PNG", parallel=False)
        jobs2 = [(p, tmp / "out" / p.stem) for p in paths]
        seen2, _ = run_batch(app, jobs2, opts_serial)
        check("worker serial: all succeeded",
              all(f[2] for f in seen2["files"]) and len(seen2["files"]) == len(jobs),
              str(len(seen2["files"])))
        check("worker serial: per-file folders used",
              all((tmp / "out" / p.stem).exists() for p in paths))

        # -- cancellation stops the run early
        seen3, _ = run_batch(app, [(p, tmp / "out3") for p in paths],
                             converter.ConvertOptions(image_format="JPEG"),
                             cancel_after=0)
        stats3 = seen3["stats"]
        processed = stats3.ok + stats3.fail + stats3.skipped
        check("worker cancel: batch stopped before finishing",
              processed <= len(jobs), f"processed={processed}")

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
