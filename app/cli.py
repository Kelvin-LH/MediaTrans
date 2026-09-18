"""MediaTrans command line interface.

    mediatrans [options] INPUT [INPUT...]

INPUT may be files or folders. Folders are scanned recursively for every
supported media type unless --no-recursive is given.

Examples
--------
    mediatrans *.heic -f webp -o out/
    mediatrans ~/Pictures/iPhone --by-date -o ~/Pictures/converted
    mediatrans clip.mov -f mp4 -q 90
    mediatrans song.flac -f mp3
    mediatrans trip/ --resize 1920 --quality 88
    mediatrans info IMG_0001.heic
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import APP_NAME, __version__
from . import converter as C

# ext / alias -> (kind, canonical format)
_ALIASES: dict[str, tuple[str, str]] = {}
for _f in C.IMAGE_FORMATS:
    _ALIASES[_f.lower()] = ("image", _f)
for _f in C.VIDEO_FORMATS:
    _ALIASES.setdefault(_f.lower(), ("video", _f))
for _f in C.AUDIO_FORMATS:
    _ALIASES[_f.lower()] = ("audio", _f)
_ALIASES.update({
    "jpg": ("image", "JPEG"), "jpeg": ("image", "JPEG"), "tif": ("image", "TIFF"),
    "tiff": ("image", "TIFF"), "heic": ("image", "JPEG"), "heif": ("image", "JPEG"),
    "mov": ("video", "MP4"), "qt": ("video", "MP4"), "m4v": ("video", "MP4"),
    "avi": ("video", "MP4"), "mkv": ("video", "MKV"), "webm": ("video", "WEBM"),
    "aac": ("audio", "M4A"),
})

USE_COLOR = (sys.stderr.isatty() and os.environ.get("NO_COLOR") is None
             and os.name != "nt" or os.environ.get("FORCE_COLOR") is not None)


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def ok_s(t): return _c(t, "32")
def fail_s(t): return _c(t, "31")
def warn_s(t): return _c(t, "33")
def dim_s(t): return _c(t, "2")


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} GB"


# --------------------------------------------------------------- arguments ---

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mediatrans",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Convert Apple HEIC / MOV and other media to universal "
                    "formats while preserving EXIF, GPS and device metadata.",
        epilog=__doc__.split("Examples")[1].join(["Examples", ""]) if __doc__ else "",
    )
    p.add_argument("inputs", nargs="*", metavar="INPUT",
                   help="files and/or folders to convert")
    p.add_argument("-f", "--format", metavar="FMT",
                   help="output format: jpg png webp avif tiff bmp pdf gif "
                        "(images), mp4 mkv webm gif mp3 m4a wav flac ogg "
                        "(video/audio)")
    p.add_argument("--image-format", metavar="FMT", help="image output format")
    p.add_argument("--video-format", metavar="FMT", help="video output format")
    p.add_argument("--audio-format", metavar="FMT", help="audio output format")
    p.add_argument("-o", "--output", metavar="DIR",
                   help="output folder (default: next to each source file)")
    p.add_argument("-q", "--quality", type=int, default=95, metavar="N",
                   help="JPEG/WebP/AVIF quality 1-100 (default: 95)")

    g = p.add_argument_group("image & video options")
    g.add_argument("--resize", type=int, default=0, metavar="PX",
                   help="limit the long edge to PX pixels, keeping aspect "
                        "ratio and quality (default: keep original size)")
    g.add_argument("--by-date", action="store_true",
                   help="sort output into YYYY/MM folders by capture date")
    g.add_argument("--no-metadata", action="store_true",
                   help="strip EXIF/GPS/device info (privacy mode)")
    g.add_argument("--no-timestamps", action="store_true",
                   help="do not copy source file dates onto the output")

    g2 = p.add_argument_group("performance")
    g2.add_argument("--no-parallel", action="store_true",
                    help="convert one file at a time")
    g2.add_argument("--no-gpu", action="store_true",
                    help="do not use hardware video encoders")
    g2.add_argument("--jobs", type=int, default=0, metavar="N",
                    help="parallel worker count (default: auto from CPU cores)")

    g3 = p.add_argument_group("conflicts & safety")
    g3.add_argument("--conflict", choices=C.CONFLICT_POLICIES, default="rename",
                    help="what to do when the output exists (default: rename)")
    g3.add_argument("--overwrite", action="store_true",
                    help="shorthand for --conflict overwrite")
    g3.add_argument("--skip-existing", action="store_true",
                    help="shorthand for --conflict skip")
    g3.add_argument("-n", "--dry-run", action="store_true",
                    help="show what would be converted, change nothing")

    g4 = p.add_argument_group("output & misc")
    g4.add_argument("--no-recursive", action="store_true",
                    help="when an input is a folder, do not descend into it")
    g4.add_argument("-v", "--verbose", action="store_true",
                    help="per-file detail for every conversion")
    g4.add_argument("--quiet", action="store_true",
                    help="only print failures and the summary")
    g4.add_argument("--json", action="store_true",
                    help="print a machine-readable JSON summary")
    g4.add_argument("--list-formats", action="store_true",
                    help="list every supported input and output format")
    g4.add_argument("--version", action="version",
                    version=f"{APP_NAME} {__version__}")
    return p


def _resolve_formats(args) -> tuple[C.ConvertOptions, str | None]:
    opts = C.ConvertOptions(
        quality=max(1, min(100, args.quality)),
        resize_long_edge=max(0, args.resize),
        keep_metadata=not args.no_metadata,
        keep_timestamps=not args.no_timestamps,
        parallel=not args.no_parallel,
        use_gpu=not args.no_gpu,
        conflict="overwrite" if args.overwrite else
                 "skip" if args.skip_existing else args.conflict,
        organize_by_date=args.by_date,
    )
    if args.format:
        key = args.format.lower().lstrip(".")
        if key not in _ALIASES:
            return opts, (f"unknown format {args.format!r} — "
                          f"see --list-formats")
        _, canonical = _ALIASES[key]
        if canonical in C.IMAGE_FORMATS:
            opts.image_format = canonical
        if canonical in C.VIDEO_FORMATS:
            opts.video_format = canonical
        if canonical in C.AUDIO_FORMATS:
            opts.audio_format = canonical
    for field, value, valid in (
            ("image_format", args.image_format, C.IMAGE_FORMATS),
            ("video_format", args.video_format, C.VIDEO_FORMATS),
            ("audio_format", args.audio_format, C.AUDIO_FORMATS)):
        if not value:
            continue
        v = value.upper()
        if v == "JPG":
            v = "JPEG"
        if v not in valid:
            return opts, f"invalid {field.replace('_', ' ')}: {value!r}"
        setattr(opts, field, v)
    return opts, None


def _collect(args) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    problems: list[str] = []
    seen: set[str] = set()
    for raw in args.inputs:
        p = Path(raw).expanduser()
        if p.is_dir():
            found = C.scan_folder(p, recursive=not args.no_recursive)
            if not found:
                problems.append(f"no convertible files in folder: {p}")
            for f in found:
                if str(f).lower() not in seen:
                    seen.add(str(f).lower())
                    files.append(f)
        elif p.is_file():
            if str(p).lower() not in seen:
                seen.add(str(p).lower())
                files.append(p)
        else:
            problems.append(f"not found: {p}")
    return files, problems


# ---------------------------------------------------------------- commands ---

def cmd_convert(args) -> int:
    opts, err = _resolve_formats(args)
    if err:
        print(fail_s("error: ") + err, file=sys.stderr)
        return 2
    if not args.inputs:
        build_parser().print_help()
        return 2

    files, problems = _collect(args)
    for p in problems:
        print(warn_s("warning: ") + p, file=sys.stderr)
    supported = [f for f in files if C.detect_kind(f)]
    unsupported = [f for f in files if not C.detect_kind(f)]
    for f in unsupported:
        print(warn_s("skip: ") + f"{f} (unsupported type)", file=sys.stderr)
    if not supported:
        print(fail_s("error: ") + "nothing to convert", file=sys.stderr)
        return 2

    default_dir = Path(args.output).expanduser() if args.output else None

    jobs = [(f, default_dir or f.parent) for f in supported]

    if args.dry_run:
        print(dim_s(f"dry run — {len(jobs)} file(s), nothing written"))
        for src, d in jobs:
            kind = C.detect_kind(src)
            fmt = {"image": opts.image_format, "video": opts.video_format,
                   "audio": opts.audio_format}[kind]
            try:
                dst, reason = C.plan_output(src, d, fmt, opts, create=False)
            except OSError as exc:
                print(f"  {fail_s('ERR ')} {src.name}: {exc}")
                continue
            if dst is None:
                print(f"  {warn_s('SKIP')} {src.name} -> already exists")
            else:
                print(f"  {dim_s('PLAN')} {src.name} -> {dst}"
                      + (dim_s(f"  [{reason}]") if reason != "new" else ""))
        return 0

    if default_dir:
        default_dir.mkdir(parents=True, exist_ok=True)

    if not args.json and not args.quiet:
        kind_counts = {"image": 0, "video": 0, "audio": 0}
        for f, _ in jobs:
            kind_counts[C.detect_kind(f)] += 1
        bits = ", ".join(f"{v} {k}" for k, v in kind_counts.items() if v)
        print(dim_s(f"{APP_NAME} {__version__} — {len(jobs)} file(s) ({bits}), "
                    f"{C.cpu_workers() if opts.parallel else 1} worker(s)"))
        if opts.use_gpu and C.gpu_encoder():
            print(dim_s(f"hardware encoder: {C.gpu_encoder()}"))
        if default_dir:
            print(dim_s(f"output: {default_dir}"))

    def on_progress(done: int, total: int, path: Path, res: C.ConvertResult):
        if args.json:
            return
        tag = (warn_s("SKIP") if res.skipped else
               ok_s("OK  ") if res.ok else fail_s("FAIL"))
        if res.skipped:
            if args.verbose:
                print(f"[{done}/{total}] {tag} {path.name} (already exists)")
            return
        if not res.ok:
            print(f"[{done}/{total}] {tag} {path.name}: {res.message}")
            return
        if args.quiet and not args.verbose:
            return
        name = path.name
        out = res.output.name if res.output else "?"
        delta = ""
        if res.in_bytes and res.out_bytes:
            pct = (1 - res.out_bytes / res.in_bytes) * 100
            arrow = "↓" if pct >= 0 else "↑"
            delta = dim_s(f"  {human(res.in_bytes)} → {human(res.out_bytes)}"
                          f" ({arrow}{abs(pct):.0f}%)")
        print(f"[{done}/{total}] {tag} {name} → {out}"
              f"{dim_s('  ' + res.message)}{delta}")

    stats = C.convert_many([p for p, _ in jobs],
                          default_dir or Path("."), opts,
                          on_progress=on_progress) if default_dir else None
    if stats is None:
        # per-file output folders: run the batch grouped by destination
        stats = C.BatchStats()
        groups: dict[Path, list[Path]] = {}
        for src, d in jobs:
            groups.setdefault(d, []).append(src)
        total = len(jobs)
        offset = 0
        for d, group in groups.items():
            def on_group_progress(done, _total, path, res, _off=offset):
                on_progress(_off + done, total, path, res)

            s = C.convert_many(group, d, opts, on_progress=on_group_progress)
            stats.ok += s.ok
            stats.fail += s.fail
            stats.skipped += s.skipped
            stats.in_bytes += s.in_bytes
            stats.out_bytes += s.out_bytes
            stats.seconds += s.seconds
            stats.failures.extend(s.failures)
            offset += len(group)

    if args.json:
        print(json.dumps({
            "tool": APP_NAME, "version": __version__,
            "converted": stats.ok, "failed": stats.fail,
            "skipped": stats.skipped,
            "input_bytes": stats.in_bytes, "output_bytes": stats.out_bytes,
            "seconds": round(stats.seconds, 2),
            "failures": [{"file": str(p), "error": m} for p, m in stats.failures],
        }, indent=2, ensure_ascii=False))
    else:
        _print_summary(stats, len(jobs))

    if stats.fail:
        print(dim_s(f"details: {C.log_file()}"))
        return 1
    return 0


def _print_summary(stats: C.BatchStats, total: int) -> None:
    line = "─" * 46
    print(dim_s(line))
    print(f"  {ok_s(str(stats.ok) + ' converted')}"
          + (f"   {warn_s(str(stats.skipped) + ' skipped')}" if stats.skipped else "")
          + (f"   {fail_s(str(stats.fail) + ' failed')}" if stats.fail else ""))
    if stats.in_bytes:
        pct = stats.savings_pct
        trend = "smaller" if pct >= 0 else "larger"
        print(f"  size     {human(stats.in_bytes)} → {human(stats.out_bytes)}"
              f"  ({abs(pct):.0f}% {trend})")
    if stats.seconds > 0:
        rate = total / stats.seconds
        print(f"  time     {stats.seconds:.1f} s  ({rate:.1f} files/s)")
    if stats.failures:
        print(dim_s("  failures:"))
        for p, msg in stats.failures[:10]:
            print(f"    {fail_s('✘')} {p.name}: {msg}")
        if len(stats.failures) > 10:
            print(dim_s(f"    … and {len(stats.failures) - 10} more"))
    print(dim_s(line))


def cmd_info(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="mediatrans info",
                                description="Show metadata of a media file.")
    p.add_argument("file", metavar="FILE")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    path = Path(a.file).expanduser()
    if not path.is_file():
        print(fail_s("error: ") + f"not found: {path}", file=sys.stderr)
        return 2

    from PIL import Image
    from PIL.ExifTags import GPS, IFD, TAGS

    kind = C.detect_kind(path) or "unknown"
    data: dict = {
        "file": str(path),
        "kind": kind,
        "size": path.stat().st_size,
        "size_human": human(path.stat().st_size),
    }
    cap = C._capture_date(path)
    if cap:
        data["capture_date"] = cap.isoformat(sep=" ", timespec="seconds")

    if kind == "image":
        try:
            with Image.open(path) as im:
                data["dimensions"] = f"{im.width}x{im.height}"
                data["mode"] = im.mode
                exif = im.getexif()
                for tag in (271, 272, 274, 305, 306):     # Make, Model, Orientation, Software, DateTime
                    if tag in exif:
                        data[TAGS.get(tag, str(tag))] = str(exif[tag])
                sub = exif.get_ifd(IFD.Exif)
                for tag in (33434, 33437, 34855, 42036, 36867, 36868):
                    if tag in sub:
                        data[TAGS.get(tag, str(tag))] = str(sub[tag])
                gps = exif.get_ifd(IFD.GPSInfo)
                if gps:
                    lat = _dms(gps.get(GPS.GPSLatitude), gps.get(GPS.GPSLatitudeRef))
                    lon = _dms(gps.get(GPS.GPSLongitude), gps.get(GPS.GPSLongitudeRef))
                    if lat is not None and lon is not None:
                        data["gps"] = f"{lat:.6f}, {lon:.6f}"
                if im.info.get("icc_profile"):
                    data["icc_profile"] = f"{len(im.info['icc_profile'])} bytes"
                if im.info.get("xmp"):
                    data["xmp"] = f"{len(im.info['xmp'])} bytes"
        except Exception as exc:  # noqa: BLE001
            data["error"] = str(exc)
    elif kind in ("video", "audio"):
        r = C._run([C._ffmpeg_exe(), "-hide_banner", "-i", str(path)])
        stderr = r.stderr or ""
        import re as _re
        m = _re.search(r"Duration:\s*([0-9:.]+)", stderr)
        if m:
            data["duration"] = m.group(1)
        streams = _re.findall(r"Stream #\d+:\d+.*", stderr)
        data["streams"] = [s.strip()[:120] for s in streams]

    if a.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"\n  {_c(path.name, '1')}")
        for k, v in data.items():
            if k in ("file", "size_human"):
                continue
            if isinstance(v, list):
                print(f"  {k:<16} {v[0] if v else ''}")
                for extra in v[1:]:
                    print(f"  {'':<16} {extra}")
            else:
                print(f"  {k:<16} {v}")
        print()
    return 0


def _dms(value, ref) -> float | None:
    if not value:
        return None
    try:
        d, m, s = (float(x) for x in value)
        out = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            out = -out
        return out
    except (TypeError, ValueError):
        return None


def cmd_formats() -> int:
    print(f"\n  {APP_NAME} {__version__} — supported formats\n")
    print(f"  input images   {', '.join(sorted(e.lstrip('.') for e in C.IMAGE_EXTS))}")
    print(f"  input videos   {', '.join(sorted(e.lstrip('.') for e in C.VIDEO_EXTS))}")
    print(f"  input audio    {', '.join(sorted(e.lstrip('.') for e in C.AUDIO_EXTS))}")
    print(f"\n  image output   {', '.join(f.lower() for f in C.IMAGE_FORMATS)}")
    print(f"  video output   {', '.join(f.lower() for f in C.VIDEO_FORMATS)}")
    print(f"  audio output   {', '.join(f.lower() for f in C.AUDIO_FORMATS)}")
    print("\n  lossless       png, webp (quality 100), tiff, bmp, "
          "mp4/mkv remux (stream copy)")
    print(f"  ffmpeg         {'available' if C.ffmpeg_available() else 'MISSING'}")
    enc = C.gpu_encoder()
    print(f"  gpu encoder    {enc or 'none detected (software encoding)'}")
    print(f"  cpu workers    {C.cpu_workers()} of {os.cpu_count()} cores")
    print(f"  log file       {C.log_file()}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "info":
        return cmd_info(argv[1:])
    args = build_parser().parse_args(argv)
    if args.list_formats:
        return cmd_formats()
    return cmd_convert(args)


if __name__ == "__main__":
    sys.exit(main())
