"""Core conversion engine for MediaTrans.

Images   HEIC/HEIF/HIF/AVIF/JPG/PNG/WebP/BMP/TIFF
         -> JPG/PNG/WebP/AVIF/TIFF/BMP/PDF/GIF
Videos   MOV/QT/MP4/M4V/AVI/MKV/WebM
         -> MP4/MKV/WebM/GIF + audio extraction (MP3/M4A/WAV/FLAC/OGG)
Audio    MP3/M4A/AAC/WAV/FLAC/OGG -> MP3/M4A/WAV/FLAC/OGG

Guarantees:
* metadata (EXIF incl. GPS & device info, XMP, ICC) is carried over whenever
  the target container can store it;
* PNG / WebP-100 / TIFF-LZW / BMP outputs are pixel-lossless;
* MP4/MKV remux with stream copy (bit-exact) when the codecs allow it;
* every failure is written to a rotating log with the full tool output.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps
from PIL.ExifTags import IFD

pillow_heif.register_heif_opener()
with contextlib.suppress(Exception):  # AVIF support is optional in older builds
    pillow_heif.register_avif_opener()

IMAGE_EXTS = {".heic", ".heif", ".hif", ".avif", ".jpg", ".jpeg", ".png",
              ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTS = {".mov", ".qt", ".mp4", ".m4v", ".avi", ".mkv", ".webm"}
AUDIO_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus"}
ALL_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "AVIF", "TIFF", "BMP", "PDF", "GIF")
AUDIO_FORMATS = ("MP3", "M4A", "WAV", "FLAC", "OGG")
VIDEO_FORMATS = ("MP4", "MKV", "WEBM", "GIF", *AUDIO_FORMATS)

EXT_FOR_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp",
                  "AVIF": ".avif", "TIFF": ".tiff", "BMP": ".bmp",
                  "PDF": ".pdf", "GIF": ".gif", "MP4": ".mp4", "MKV": ".mkv",
                  "WEBM": ".webm", "MP3": ".mp3", "M4A": ".m4a", "WAV": ".wav",
                  "FLAC": ".flac", "OGG": ".ogg"}
# formats that can carry EXIF/ICC via Pillow
META_FORMATS = {"JPEG", "PNG", "WEBP", "AVIF", "TIFF"}

CONFLICT_POLICIES = ("rename", "overwrite", "skip")

_AUDIO_CODECS = {
    "MP3": ["-c:a", "libmp3lame", "-q:a", "2"],
    "M4A": ["-c:a", "aac", "-b:a", "192k"],
    "WAV": ["-c:a", "pcm_s16le"],
    "FLAC": ["-c:a", "flac"],
    "OGG": ["-c:a", "libvorbis", "-q:a", "5"],
}

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
_MAX_LOG_BYTES = 5 * 1024 * 1024


# ---------------------------------------------------------------- logging ---

def log_file() -> Path:
    """Persistent log path: %LOCALAPPDATA%/MediaTrans/logs/mediatrans.log
    (macOS/Linux: ~/MediaTrans/logs)."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    d = Path(base) / "MediaTrans" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d / "mediatrans.log"


def app_log(message: str) -> None:
    """Append to the persistent log, rotating once past ~5 MB."""
    try:
        lf = log_file()
        if lf.exists() and lf.stat().st_size > _MAX_LOG_BYTES:
            lf.replace(lf.with_suffix(".old.log"))
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(lf, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except OSError:
        pass  # logging must never break a conversion


# ---------------------------------------------------------------- options ---

@dataclass
class ConvertOptions:
    image_format: str = "JPEG"      # JPEG|PNG|WEBP|AVIF|TIFF|BMP|PDF|GIF
    video_format: str = "MP4"       # MP4|MKV|WEBM|GIF|MP3|M4A|WAV|FLAC|OGG
    audio_format: str = "MP3"       # MP3|M4A|WAV|FLAC|OGG
    quality: int = 95               # JPEG / WebP / AVIF
    keep_metadata: bool = True      # EXIF, GPS, device info, ICC, XMP
    keep_timestamps: bool = True    # copy file dates to the output
    parallel: bool = True           # fan out across CPU cores
    use_gpu: bool = True            # prefer hardware video encoders
    resize_long_edge: int = 0       # 0 = native size, else max pixels (HQ)
    conflict: str = "rename"        # rename | overwrite | skip
    organize_by_date: bool = False  # write into YYYY/MM from capture date


@dataclass
class ConvertResult:
    ok: bool
    output: Path | None = None
    message: str = ""
    in_bytes: int = 0
    out_bytes: int = 0
    skipped: bool = False
    seconds: float = 0.0


@dataclass
class BatchStats:
    ok: int = 0
    fail: int = 0
    skipped: int = 0
    in_bytes: int = 0
    out_bytes: int = 0
    seconds: float = 0.0
    failures: list = field(default_factory=list)

    @property
    def savings_pct(self) -> float:
        if not self.in_bytes:
            return 0.0
        return (1 - self.out_bytes / self.in_bytes) * 100


# ------------------------------------------------------------- system info ---

def cpu_workers() -> int:
    """Parallelism scaled to the machine: cores minus one, clamped to 2..8."""
    return max(2, min(8, (os.cpu_count() or 4) - 1))


_GPU_PRIORITY = ("h264_nvenc",       # NVIDIA
                 "h264_qsv",         # Intel Quick Sync
                 "h264_amf",         # AMD
                 "h264_videotoolbox")  # macOS
_GPU_ENCODER_CACHE: str | None = None


def gpu_encoder() -> str | None:
    """Best hardware H.264 encoder this ffmpeg offers, or None."""
    global _GPU_ENCODER_CACHE
    if _GPU_ENCODER_CACHE is not None:
        return _GPU_ENCODER_CACHE or None
    enc = ""
    with contextlib.suppress(Exception):
        enc = _run([_ffmpeg_exe(), "-hide_banner", "-encoders"]).stdout or ""
    _GPU_ENCODER_CACHE = next((n for n in _GPU_PRIORITY if n in enc), "")
    return _GPU_ENCODER_CACHE or None


def _h264_gpu_args(encoder: str) -> list[str]:
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19"]
    if encoder == "h264_qsv":
        return ["-c:v", "h264_qsv", "-global_quality", "20"]
    if encoder == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "quality",
                "-rc", "vbr_peak", "-b:v", "8M"]
    return ["-c:v", "h264_videotoolbox", "-b:v", "6M"]


def ffmpeg_available() -> bool:
    try:
        _ffmpeg_exe()
        return True
    except Exception:  # noqa: BLE001
        return False


def _ffmpeg_exe() -> str:
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True,
                          creationflags=_NO_WINDOW)


# ------------------------------------------------------------------ inputs ---

def detect_kind(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    return None


def scan_folder(folder: Path, recursive: bool = True) -> list[Path]:
    """All convertible files in a folder, sorted naturally by name."""
    it = folder.rglob("*") if recursive else folder.glob("*")
    found = [p for p in it if p.is_file() and p.suffix.lower() in ALL_EXTS]
    return sorted(found, key=lambda p: (str(p.parent).lower(), p.name.lower()))


# -------------------------------------------------------------- output path ---

def _capture_date(src: Path) -> datetime | None:
    """Best-effort capture timestamp: EXIF, then container metadata, then mtime."""
    kind = detect_kind(src)
    if kind == "image":
        try:
            with Image.open(src) as im:
                exif = im.getexif()
                raw = (exif.get_ifd(IFD.Exif).get(36867)      # DateTimeOriginal
                       or exif.get_ifd(IFD.Exif).get(36868)   # DateTimeDigitized
                       or exif.get(306))                      # DateTime
                if raw:
                    return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
        except Exception:  # noqa: BLE001 — fall through to mtime
            pass
    elif kind in ("video", "audio"):
        try:
            r = _run([_ffmpeg_exe(), "-hide_banner", "-i", str(src)])
            m = re.search(r"creation_time\s*:\s*([0-9T:.\-]+)", r.stderr or "")
            if m:
                return datetime.fromisoformat(m.group(1).rstrip("Z"))
        except Exception:  # noqa: BLE001
            pass
    try:
        return datetime.fromtimestamp(src.stat().st_mtime)
    except OSError:
        return None


def plan_output(src: Path, dst_dir: Path, fmt: str, opts: ConvertOptions,
                create: bool = True) -> tuple[Path | None, str]:
    """Decide the output path. Returns (path, reason); path is None to skip.

    Enforces the conflict policy and never lets a conversion overwrite its own
    source file (e.g. JPG -> JPG in the same folder). Pass create=False for
    dry runs so that no directory is touched.
    """
    target_dir = dst_dir
    if opts.organize_by_date:
        d = _capture_date(src)
        if d:
            target_dir = dst_dir / f"{d.year:04d}" / f"{d.month:02d}"
    if create:
        target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / (src.stem + EXT_FOR_FORMAT[fmt])

    same_file = False
    try:
        same_file = dst.exists() and dst.samefile(src)
    except OSError:
        same_file = dst.resolve() == src.resolve()

    if not dst.exists() or same_file:
        if same_file:
            # never clobber the source: fall back to a suffixed name
            return _suffixed(dst), "rename"
        return dst, "new"

    policy = opts.conflict if opts.conflict in CONFLICT_POLICIES else "rename"
    if policy == "skip":
        return None, "skip"
    if policy == "overwrite":
        return dst, "overwrite"
    return _suffixed(dst), "rename"


def _suffixed(path: Path) -> Path:
    for i in range(1, 10000):
        cand = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not cand.exists():
            return cand
    return path


def unique_path(path: Path) -> Path:
    """Kept for API compatibility: first free name."""
    return path if not path.exists() else _suffixed(path)


def _finish(src: Path, dst: Path, opts: ConvertOptions) -> None:
    """Apply post-processing shared by every converter (timestamps)."""
    if opts.keep_timestamps:
        try:
            st = src.stat()
            os.utime(dst, (st.st_atime, st.st_mtime))
        except OSError:
            pass


def _sizes(src: Path, dst: Path | None) -> tuple[int, int]:
    try:
        in_b = src.stat().st_size
    except OSError:
        in_b = 0
    out_b = 0
    if dst is not None:
        try:
            out_b = dst.stat().st_size
        except OSError:
            out_b = 0
    return in_b, out_b


def _skip_result(src: Path) -> ConvertResult:
    in_b, _ = _sizes(src, None)
    app_log(f"SKIP (exists, policy=skip): {src}")
    return ConvertResult(True, None, "skipped (already exists)",
                         in_bytes=in_b, skipped=True)


# ------------------------------------------------------------------ images ---

def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """Flatten alpha onto white for formats without an alpha channel."""
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA", "PA"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def _save_with_xmp(img: Image.Image, dst: Path, fmt: str, **kwargs) -> None:
    xmp = kwargs.pop("xmp", None)
    if xmp:
        try:
            img.save(dst, fmt, xmp=xmp, **kwargs)
            return
        except (TypeError, ValueError, OSError):
            pass  # encoder does not accept XMP; save without it
    img.save(dst, fmt, **kwargs)


def _save_tiff(img: Image.Image, dst: Path, exif, icc, xmp) -> None:
    """Save TIFF; some libtiff builds reject pre-serialized sub-IFDs, so try
    progressively: LZW+full EXIF, uncompressed+full, LZW+IFD0 only, bare."""
    attempts = []
    if exif:
        attempts.append({"exif": exif, "compression": "tiff_lzw"})
        attempts.append({"exif": exif})
        stripped = Image.Exif()
        stripped.load(exif)
        stripped.pop(34665, None)  # Exif IFD pointer
        stripped.pop(34853, None)  # GPS IFD pointer
        attempts.append({"exif": stripped.tobytes(), "compression": "tiff_lzw"})
    else:
        attempts.append({"compression": "tiff_lzw"})
    attempts.append({})
    icc_kw = {"icc_profile": icc} if icc else {}
    last_exc: Exception | None = None
    for extra in attempts:
        try:
            _save_with_xmp(img, dst, "TIFF", xmp=xmp, **extra, **icc_kw)
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc  # type: ignore[misc]


def _resize_image(img: Image.Image, long_edge: int) -> Image.Image:
    if long_edge <= 0 or max(img.size) <= long_edge:
        return img
    out = img.copy()
    out.thumbnail((long_edge, long_edge), Image.LANCZOS, reducing_gap=3.0)
    return out


def convert_image(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    t0 = time.time()
    fmt = opts.image_format.upper()
    if fmt not in IMAGE_FORMATS:
        return ConvertResult(False, message=f"unknown image format {fmt!r}")

    dst, reason = plan_output(src, dst_dir, fmt, opts)
    if dst is None:
        return _skip_result(src)

    try:
        with Image.open(src) as im:
            im.load()
            # bake EXIF orientation into pixels, drop the stale tag
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                im = im.convert("RGB")
            im = _resize_image(im, opts.resize_long_edge)

            keep = opts.keep_metadata and fmt in META_FORMATS
            exif = im.info.get("exif") if keep else None
            icc = im.info.get("icc_profile") if keep else None
            xmp = im.info.get("xmp") if keep else None

            kwargs: dict = {}
            if exif:
                kwargs["exif"] = exif
            if icc:
                kwargs["icc_profile"] = icc

            if fmt == "JPEG":
                im = _flatten_to_rgb(im)
                kwargs["quality"] = opts.quality
                kwargs["optimize"] = True
                if opts.quality >= 90:
                    kwargs["subsampling"] = 0  # full chroma at high quality
            elif fmt == "BMP":
                im = _flatten_to_rgb(im)
            elif fmt == "WEBP":
                if opts.quality >= 100:
                    kwargs["lossless"] = True
                else:
                    kwargs["quality"] = opts.quality
                    kwargs["method"] = 6
            elif fmt == "AVIF":
                kwargs["quality"] = min(opts.quality, 100)
            elif fmt == "TIFF":
                _save_tiff(im, dst, exif, icc, xmp)
                _finish(src, dst, opts)
                in_b, out_b = _sizes(src, dst)
                app_log(f"OK image [{fmt}]: {src} -> {dst}")
                return ConvertResult(True, dst, "converted", in_b, out_b,
                                     seconds=time.time() - t0)
            elif fmt == "PDF":
                im = _flatten_to_rgb(im)
                kwargs = {"resolution": 144.0}  # PDF stores no EXIF/ICC
                xmp = None
            elif fmt == "GIF":
                im = im.convert("RGB").quantize(colors=256)
                kwargs = {}
                xmp = None
            # PNG: always lossless, no extra kwargs

            _save_with_xmp(im, dst, fmt, xmp=xmp, **kwargs)

        _finish(src, dst, opts)
        in_b, out_b = _sizes(src, dst)
        app_log(f"OK image [{fmt}]: {src} -> {dst}")
        return ConvertResult(True, dst, "converted", in_b, out_b,
                             seconds=time.time() - t0)
    except Exception as exc:  # noqa: BLE001 — one bad file must not stop the batch
        if dst.exists() and reason != "overwrite":
            dst.unlink(missing_ok=True)
        app_log(f"FAILED image -> {fmt}: {src}\n  {type(exc).__name__}: {exc}")
        return ConvertResult(False, message=f"{type(exc).__name__}: {exc}")


# ------------------------------------------------------------------ videos ---

def _ffmpeg_convert(src: Path, dst: Path, extra: list[str]) -> subprocess.CompletedProcess:
    return _run([_ffmpeg_exe(), "-y", "-i", str(src), *extra, str(dst)])


def _ok_file(dst: Path) -> bool:
    return dst.exists() and dst.stat().st_size > 0


def _scale_filter(long_edge: int) -> list[str]:
    if long_edge <= 0:
        return []
    expr = f"trunc(min({long_edge},iw)/2)*2:trunc(min({long_edge},ih)/2)*2"
    return ["-vf", f"scale={expr}:force_original_aspect_ratio=decrease"]


def _video_failure(src: Path, fmt: str, r: subprocess.CompletedProcess) -> ConvertResult:
    stderr = (r.stderr or "").strip()
    app_log(f"FAILED {fmt}: {src}\n  exit code: {r.returncode}\n"
            f"  ffmpeg stderr:\n{textwrap.indent(stderr, '    ')}")
    lines = stderr.splitlines() or ["ffmpeg failed"]
    hint = ""
    low = stderr.lower()
    if "unknown codec" in low or "could not find codec parameters" in low:
        hint = " (unsupported source codec)"
    return ConvertResult(False, message=lines[-1][:280] + hint + "  [see log]")


def convert_video(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    t0 = time.time()
    vfmt = opts.video_format.upper()
    if vfmt not in VIDEO_FORMATS:
        return ConvertResult(False, message=f"unknown video format {vfmt!r}")
    try:
        _ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        return ConvertResult(False, message=f"ffmpeg not available: {exc}")

    dst, reason = plan_output(src, dst_dir, vfmt, opts)
    if dst is None:
        return _skip_result(src)

    meta = ["-map_metadata", "0"] if opts.keep_metadata else []
    # Only the primary audio stream is mapped: newer iPhones add an Apple
    # "apac" spatial-audio track that ffmpeg cannot decode, and mapping it
    # makes every output fail with "Error opening output files".
    streams = ["-map", "0:v:0", "-map", "0:a:0?"]
    scale = _scale_filter(opts.resize_long_edge)

    def success(detail: str) -> ConvertResult:
        _finish(src, dst, opts)
        in_b, out_b = _sizes(src, dst)
        app_log(f"OK video [{detail}]: {src} -> {dst}")
        return ConvertResult(True, dst, detail, in_b, out_b,
                             seconds=time.time() - t0)

    if vfmt in AUDIO_FORMATS:  # extract the audio track
        r = _ffmpeg_convert(src, dst, ["-vn", *meta, *_AUDIO_CODECS[vfmt]])
        if r.returncode == 0 and _ok_file(dst):
            return success(f"audio extracted ({vfmt})")
        dst.unlink(missing_ok=True)
        return _video_failure(src, vfmt, r)

    if vfmt == "MP4":
        # 1) lossless attempt: stream copy (H.264/HEVC video + AAC audio).
        #    Skipped when resizing, since scaling requires a re-encode.
        if not scale:
            r = _ffmpeg_convert(src, dst,
                                [*meta, *streams, "-c", "copy",
                                 "-movflags", "+faststart"])
            if r.returncode == 0 and _ok_file(dst):
                return success("lossless remux")
            dst.unlink(missing_ok=True)
        # 2) re-encode: hardware encoder first, then software x264
        if opts.use_gpu:
            gpu = gpu_encoder()
            if gpu:
                r = _ffmpeg_convert(src, dst,
                                    [*meta, *streams, *scale, *_h264_gpu_args(gpu),
                                     "-pix_fmt", "yuv420p",
                                     "-c:a", "aac", "-b:a", "192k",
                                     "-movflags", "+faststart"])
                if r.returncode == 0 and _ok_file(dst):
                    return success(f"re-encoded ({gpu})")
                dst.unlink(missing_ok=True)
                app_log(f"GPU encoder {gpu} failed for {src}; "
                        f"falling back to software x264")
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams, *scale,
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                             "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "192k",
                             "-movflags", "+faststart"])
        if r.returncode == 0 and _ok_file(dst):
            return success("re-encoded (H.264/AAC)")
        dst.unlink(missing_ok=True)
        return _video_failure(src, vfmt, r)

    if vfmt == "MKV":
        # Matroska takes virtually any codec, so a plain remux is lossless
        if not scale:
            r = _ffmpeg_convert(src, dst,
                                [*meta, *streams, "-map", "0:s?", "-c", "copy"])
            if r.returncode == 0 and _ok_file(dst):
                return success("lossless remux")
            dst.unlink(missing_ok=True)
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams, *scale,
                             "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                             "-c:a", "aac", "-b:a", "192k"])
        if r.returncode == 0 and _ok_file(dst):
            return success("re-encoded (H.264/AAC)")
        dst.unlink(missing_ok=True)
        return _video_failure(src, vfmt, r)

    if vfmt == "WEBM":
        r = _ffmpeg_convert(src, dst,
                            [*meta, *scale,
                             "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
                             "-row-mt", "1", "-c:a", "libopus", "-b:a", "128k"])
        if r.returncode == 0 and _ok_file(dst):
            return success("re-encoded (VP9/Opus)")
        dst.unlink(missing_ok=True)
        return _video_failure(src, vfmt, r)

    # GIF — palette-optimized animation
    gif_scale = "scale=480:-1:flags=lanczos"
    if opts.resize_long_edge:
        gif_scale = (f"scale=trunc(min({opts.resize_long_edge},iw)/2)*2:"
                     f"trunc(min({opts.resize_long_edge},ih)/2)*2:"
                     f"force_original_aspect_ratio=decrease")
    r = _ffmpeg_convert(src, dst,
                        ["-vf", f"fps=12,{gif_scale},"
                                "split[a][b];[a]palettegen[p];[b][p]paletteuse",
                         "-loop", "0"])
    if r.returncode == 0 and _ok_file(dst):
        return success("animated GIF")
    dst.unlink(missing_ok=True)
    return _video_failure(src, vfmt, r)


# ------------------------------------------------------------------- audio ---

def convert_audio(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    t0 = time.time()
    afmt = opts.audio_format.upper()
    if afmt not in AUDIO_FORMATS:
        return ConvertResult(False, message=f"unknown audio format {afmt!r}")
    try:
        _ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        return ConvertResult(False, message=f"ffmpeg not available: {exc}")

    dst, reason = plan_output(src, dst_dir, afmt, opts)
    if dst is None:
        return _skip_result(src)

    meta = ["-map_metadata", "0"] if opts.keep_metadata else []
    r = _ffmpeg_convert(src, dst, ["-vn", *meta, *_AUDIO_CODECS[afmt]])
    if r.returncode == 0 and _ok_file(dst):
        _finish(src, dst, opts)
        in_b, out_b = _sizes(src, dst)
        app_log(f"OK audio [{afmt}]: {src} -> {dst}")
        return ConvertResult(True, dst, "converted", in_b, out_b,
                             seconds=time.time() - t0)
    dst.unlink(missing_ok=True)
    return _video_failure(src, afmt, r)


# --------------------------------------------------------------- dispatcher ---

def convert_file(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    kind = detect_kind(src)
    if kind == "image":
        return convert_image(src, dst_dir, opts)
    if kind == "video":
        return convert_video(src, dst_dir, opts)
    if kind == "audio":
        return convert_audio(src, dst_dir, opts)
    return ConvertResult(False, message="unsupported file type")


def convert_many(paths: list[Path], dst_dir: Path, opts: ConvertOptions,
                 on_progress=None, should_cancel=None) -> BatchStats:
    """Convert a batch, in parallel when opts.parallel is set.

    on_progress(done, total, path, result) is called from worker threads;
    should_cancel() is polled before each file so a batch can be stopped.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    stats = BatchStats()
    total = len(paths)
    if not total:
        return stats
    t0 = time.time()
    done = 0

    def work(p: Path) -> ConvertResult:
        if should_cancel and should_cancel():
            return ConvertResult(True, None, "cancelled", skipped=True)
        return convert_file(p, dst_dir, opts)

    def record(p: Path, res: ConvertResult) -> None:
        nonlocal done
        done += 1
        if res.skipped:
            stats.skipped += 1
        elif res.ok:
            stats.ok += 1
        else:
            stats.fail += 1
            stats.failures.append((p, res.message))
        stats.in_bytes += res.in_bytes
        stats.out_bytes += res.out_bytes
        if on_progress:
            with contextlib.suppress(Exception):  # progress must not break work
                on_progress(done, total, p, res)

    if opts.parallel and total > 1:
        with ThreadPoolExecutor(max_workers=min(total, cpu_workers())) as ex:
            futures = {ex.submit(work, p): p for p in paths}
            for f in as_completed(futures):
                p = futures[f]
                try:
                    record(p, f.result())
                except Exception as exc:  # noqa: BLE001
                    record(p, ConvertResult(False, message=str(exc)))
    else:
        for p in paths:
            record(p, work(p))

    stats.seconds = time.time() - t0
    return stats


def disk_free_gb(path: Path) -> float:
    try:
        return shutil.disk_usage(path).free / (1024 ** 3)
    except OSError:
        return 0.0
