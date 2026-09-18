# Contributing to MediaTrans

Thanks for taking the time to improve MediaTrans! This document explains how to
set up the project, how to test your changes, and what we look for in a pull
request.

## Getting started

```bash
git clone https://github.com/Kelvin-LH/MediaTrans.git
cd MediaTrans
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt ruff
```

Run the desktop app:

```bash
python run.py
```

Run the command line tool without installing anything:

```bash
python -m app --help
python -m app --list-formats
```

Install it as a real command (optional):

```bash
pip install -e .
mediatrans --help
```

## Tests and linting

Everything the CI runs can be run locally in a few seconds:

```bash
python tests/test_converter.py   # conversion engine, metadata, formats
python tests/test_cli.py         # CLI behaviour, exit codes, JSON output
ruff check .                     # style and bug lints
```

The engine tests generate their own test media (a HEIC with EXIF/GPS and a
MOV with audio), so no fixtures are needed. If ffmpeg is missing, video tests
are skipped rather than failed.

Please make sure all three commands pass before opening a pull request.

## Project layout

```
app/
  converter.py   conversion engine — formats, metadata, parallelism, GPU
  cli.py         `mediatrans` command line interface
  ui.py          PySide6 desktop window (bilingual, light/dark themes)
  i18n.py        all user-facing strings (English / 简体中文)
tests/           plain-script test suites (no pytest required)
tools/           helper scripts for icons and README screenshots
packaging/       macOS entitlements used by the release workflow
```

## Adding a new output format

1. Add the format to `IMAGE_FORMATS`, `VIDEO_FORMATS` or `AUDIO_FORMATS` in
   `app/converter.py` and to `EXT_FOR_FORMAT`.
2. Handle it in the relevant `convert_*` function (encoder flags, whether it
   can carry metadata, whether it is lossless).
3. Add the label key (for example `fmt_dng`) to **both** language dictionaries
   in `app/i18n.py`.
4. Extend the tests in `tests/test_converter.py`.

## Adding or changing UI text

Never hard-code a user-visible string in `ui.py` — add a key to `app/i18n.py`
in both `en` and `zh`, then call `tr("your_key")`. The offscreen GUI smoke test
in CI builds every language/theme combination so missing keys surface quickly.

## Pull request checklist

- [ ] `python tests/test_converter.py` passes
- [ ] `python tests/test_cli.py` passes
- [ ] `ruff check .` is clean
- [ ] New user-visible strings exist in English **and** Chinese
- [ ] `CHANGELOG.md` has an entry under `Unreleased`
- [ ] The change works both from the GUI and the CLI where applicable

## Reporting bugs

Open an issue with the bug report template. For conversion problems, the log
file is the most useful thing you can attach:

- Windows: `%LOCALAPPDATA%\MediaTrans\logs\mediatrans.log`
- macOS / Linux: `~/MediaTrans/logs/mediatrans.log`

It contains the exact ffmpeg command output for every failure.

## Code style

- Python 3.10+, standard library where practical; the only runtime
  dependencies are PySide6, Pillow, pillow-heif and imageio-ffmpeg.
- Type hints on public functions, docstrings explaining *why* not *what*.
- Keep user-visible behaviour identical between the GUI and the CLI.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
