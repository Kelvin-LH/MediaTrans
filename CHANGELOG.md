# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] — 2026-09-13

### Added
- **Adaptive interface.** The settings panel switches between two columns and a
  single column, the top bar folds onto a second row, and the queue buttons
  become a 2x2 grid — each decision is made from the space actually available
  (widget size hints, language and font scale), so the window renders correctly
  from 780x460 up to 2560x1440.
- The window is sized to fit the screen it opens on, centred, and clamped when
  the stored size no longer fits; window size and position are remembered
  between sessions and re-clamped if the display changes.
- Sizes are derived from font metrics rather than hard-coded pixels, so custom
  system fonts and 100%–200% DPI scaling no longer clip text.
- `tests/test_layout.py`: 12 automated checks over 8 window sizes, 4 font
  scales, 2 languages and 2 themes, plus a CI run at 150% DPI.

### Changed
- Removed hard-coded pixel font sizes from the stylesheet; the system font and
  DPI settings are honoured.
- Format combo boxes no longer demand the width of their longest entry, which
  previously forced the settings panel wider than the window.

### Fixed
- Settings cards were stretched beyond their content height when the panel
  layout changed between compact and wide arrangements.

## [0.3.0] — 2026-09-13

### Added
- **Command line interface** (`mediatrans`): convert files or whole folders,
  with `--json` summaries, `--dry-run`, exit codes and `mediatrans info` for
  reading EXIF/GPS/device metadata. Scriptable and CI friendly.
- **Folder input** in the GUI (drag a folder or use “Add Folder”) — scanned
  recursively for every supported type.
- **Resize** option: cap the long edge in pixels with high-quality resampling,
  for both images and videos (aspect ratio preserved, never upscales).
- **Conflict policy**: keep both (auto-numbered), overwrite, or skip.
- **Capture-date organisation**: write output into `YYYY/MM` folders.
- **Timestamp preservation**: output files inherit the source file dates.
- **Audio support**: MP3 / M4A / WAV / FLAC / OGG as inputs, outputs, and as
  audio extraction targets for video files.
- **Presets** in the GUI: Web optimized, Social/email, Archive (lossless),
  Maximum compatibility, Smallest size.
- **Dark mode** and a light/dark toggle, persisted with all other settings.
- **Conversion summary**: total size before/after, savings percentage,
  elapsed time and throughput; per-file size deltas.
- **Error details dialog** — double-click a failed log entry for the full
  error, with copy to clipboard.
- WAV/FLAC/OGG lossless audio output, `--jobs` to control parallelism.
- CI: test matrix (Windows/macOS/Linux × Python 3.10/3.12), ruff lint job and
  an offscreen GUI smoke test.

### Changed
- Settings panel reorganised into two columns; the whole window is now
  scroll-safe on small screens.
- `MKV` output falls back to a re-encode when the source codecs are not
  Matroska-compatible instead of failing.
- Video `MP4`/`MKV` remux is skipped automatically when resizing is requested.

### Fixed
- Converting a file **in place** to its own format (e.g. JPG → JPG in the same
  folder) no longer risks clobbering the source — a suffixed name is used.
- `--dry-run` no longer creates the output directory.
- Background threads never let a failing progress callback abort a batch.

## [0.2.1] — 2026-09-13

### Fixed
- **Video conversion failed for newer iPhone recordings** that contain an
  Apple `apac` (spatial audio) track: ffmpeg could not decode it and every
  output failed with “Error opening output files”. Only the primary audio
  stream is mapped now. Verified against 38 real iPhone videos.
- Full ffmpeg diagnostics are written to a rotating log file
  (`%LOCALAPPDATA%/MediaTrans/logs/mediatrans.log`) with a “View Log” button.

### Added
- Parallel batch conversion, auto-scaled to the CPU core count.
- GPU-accelerated video encoding (NVENC / QSV / AMF / VideoToolbox) with
  automatic software fallback.

## [0.2.0] — 2026-09-13

### Added
- Extra image outputs: AVIF, TIFF (LZW lossless), BMP, PDF, GIF.
- Extra video outputs: MKV (lossless remux), WebM (VP9/Opus), animated GIF,
  MP3 audio extraction; MP4/AVI/MKV inputs.
- Redesigned bilingual UI with a modern card theme.
- Automated multi-platform builds (Windows, macOS Intel & Apple Silicon,
  Linux) with optional code signing.

## [0.0.1] — 2026-09-13

### Added
- Initial release: HEIC/HEIF → JPG/PNG/WebP and MOV → MP4 with EXIF, GPS,
  device info and ICC profiles preserved.
- Bilingual (English / 简体中文) desktop UI, drag & drop, batch progress.
- First Windows build published on GitHub Releases.

[Unreleased]: https://github.com/Kelvin-LH/MediaTrans/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/Kelvin-LH/MediaTrans/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Kelvin-LH/MediaTrans/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Kelvin-LH/MediaTrans/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Kelvin-LH/MediaTrans/compare/v0.0.1...v0.2.0
[0.0.1]: https://github.com/Kelvin-LH/MediaTrans/releases/tag/v0.0.1
