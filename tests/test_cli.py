"""CLI end-to-end tests: python tests/test_cli.py"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import cli, converter
from tests.test_converter import make_test_heic, make_test_mov

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


def run(args: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(args)
    return code, buf.getvalue()


def test_cli(tmp: Path):
    print("== CLI ==")
    heic = tmp / "IMG_0001.heic"
    make_test_heic(heic)
    mov = tmp / "VID_0001.mov"
    make_test_mov(mov)

    # format resolution
    opts, err = cli._resolve_formats(cli.build_parser().parse_args(
        ["-f", "webp"]))
    check("resolve: -f webp sets image format",
          err is None and opts.image_format == "WEBP", err or "")
    opts, err = cli._resolve_formats(cli.build_parser().parse_args(["-f", "mp3"]))
    check("resolve: -f mp3 applies to video and audio",
          err is None and opts.video_format == "MP3" and opts.audio_format == "MP3")
    opts, err = cli._resolve_formats(cli.build_parser().parse_args(["-f", "nope"]))
    check("resolve: unknown format is rejected", err is not None)

    # basic conversion
    code, out = run([str(heic), "-f", "webp", "-o", str(tmp / "out")])
    check("convert: exit code 0", code == 0, out[-200:])
    check("convert: output file exists", (tmp / "out" / "IMG_0001.webp").exists())
    check("convert: summary printed", "converted" in out)

    # JSON summary
    code, out = run([str(heic), "-f", "png", "-o", str(tmp / "out"), "--json"])
    data = json.loads(out)
    check("json: parses and reports success",
          data["converted"] == 1 and data["failed"] == 0, out[:200])
    check("json: byte totals present", data["input_bytes"] > 0)

    # dry run writes nothing
    code, out = run([str(heic), "-f", "avif", "-o", str(tmp / "dry"), "-n"])
    check("dry-run: exit 0 and nothing written",
          code == 0 and not (tmp / "dry").exists(), out[-200:])
    check("dry-run: plan printed", "PLAN" in out or "dry run" in out)

    # skip-existing exit code and behaviour
    code, out = run([str(heic), "-f", "webp", "-o", str(tmp / "out"),
                     "--skip-existing", "-v"])
    check("skip-existing: still exit 0", code == 0, out[-200:])

    # folder input, recursive
    code, out = run([str(tmp), "-f", "jpg", "-o", str(tmp / "all"), "--json"])
    data = json.loads(out)
    check("folder input: converted several files", data["converted"] >= 2, out[:200])

    # video via CLI with audio extraction
    code, out = run([str(mov), "-f", "mp3", "-o", str(tmp / "au")])
    check("video -> mp3 via CLI", code == 0 and (tmp / "au" / "VID_0001.mp3").exists(),
          out[-200:])

    # unsupported input -> usage error
    junk = tmp / "notes.txt"
    junk.write_text("hello")
    code, out = run([str(junk)])
    check("unsupported input: exit code 2", code == 2, str(code))

    # missing input -> usage error
    code, _ = run([str(tmp / "ghost.heic")])
    check("missing input: exit code 2", code == 2)

    # failure path -> exit code 1 (corrupt file with a supported extension)
    bad = tmp / "broken.heic"
    bad.write_bytes(b"not really a heic file")
    code, out = run([str(bad), "-f", "jpg", "-o", str(tmp / "bad")])
    check("corrupt file: exit code 1 and FAIL reported",
          code == 1 and "FAIL" in out, out[-200:])
    lf = converter.log_file()
    if lf.exists():
        check("corrupt file: written to the log file",
              "FAILED image" in lf.read_text(encoding="utf-8", errors="replace"))

    # info command
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(["info", str(heic)])
    out = buf.getvalue()
    check("info: exit 0", code == 0)
    check("info: shows device and GPS",
          "iPhone 15 Pro" in out and "39.9" in out, out[:300])

    # info --json
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.main(["info", str(heic), "--json"])
    data = json.loads(buf.getvalue())
    check("info --json: machine readable",
          data["kind"] == "image" and "dimensions" in data, str(data)[:200])


def test_cli_windows_encoding(tmp: Path):
    """Regression: a cp1252 stdout used to raise UnicodeEncodeError."""
    print("== CLI on a legacy console ==")
    heic = tmp / "IMG_0009.heic"
    make_test_heic(heic)
    raw = io.BytesIO()
    legacy = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    real_out, real_err = sys.stdout, sys.stderr
    sys.stdout = legacy
    sys.stderr = legacy
    try:
        code = cli.main([str(heic), "-f", "jpg", "-o", str(tmp / "legacy")])
        legacy.flush()
    except UnicodeEncodeError as exc:  # the exact historical failure
        code = -1
        print(f"  UnicodeEncodeError: {exc}")
    finally:
        sys.stdout, sys.stderr = real_out, real_err
    check("cp1252 stdout: conversion completed without UnicodeEncodeError",
          code == 0, str(code))
    text = raw.getvalue().decode("cp1252", errors="replace")
    check("cp1252 stdout: ASCII arrow fallback in use", "->" in text, text[-160:])
    check("cp1252 stdout: no mojibake placeholders", "?" not in text, text[-160:])


def main():
    with tempfile.TemporaryDirectory(prefix="mediatrans_cli_") as d:
        tmp = Path(d)
        test_cli(tmp)
        test_cli_windows_encoding(tmp)
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
