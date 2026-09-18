# Security Policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
[security advisory](https://github.com/Kelvin-LH/MediaTrans/security/advisories/new)
form rather than a public issue. You can expect a response within a few days.

## What MediaTrans does with your data

MediaTrans runs **entirely on your machine**. It performs no network requests,
has no telemetry and no analytics, and never uploads your media or metadata.
Every conversion is a local process (Pillow for images, a bundled static
ffmpeg for video and audio).

The only files it writes outside your chosen output folder are:

| Path | Content |
| --- | --- |
| `%LOCALAPPDATA%\MediaTrans\logs\mediatrans.log` (Windows)<br>`~/MediaTrans/logs/mediatrans.log` (macOS/Linux) | Conversion results and tool diagnostics, rotated at ~5 MB |
| `QSettings` store | Your UI preferences (language, theme, format choices) |

## Metadata and privacy

Preserving EXIF/GPS/device information is the point of the tool, so by default
that information is copied into the converted files. If you plan to share
images publicly, enable privacy mode to strip it:

- GUI: uncheck *Preserve EXIF / GPS / device info / ICC*
- CLI: `mediatrans photo.heic --no-metadata`

## Supported versions

Security fixes are applied to the latest release. Please reproduce issues on
the newest version before reporting.
