"""Core conversion engine.

Images:  HEIC / HEIF / HIF (plus common JPG / PNG / WebP / BMP / TIFF inputs)
         ->  JPG / PNG / WebP / AVIF / TIFF / BMP / PDF / GIF.
         Metadata — EXIF (incl. GPS & device info), XMP, ICC color profile —
         is copied to the output whenever the target format can store it;
         PNG / WebP-100 / TIFF-LZW / BMP are pixel-lossless.

Videos:  MOV / QT / MP4 / M4V / AVI / MKV / WebM
         ->  MP4 / MKV / WebM / GIF / MP3.
         MP4 & MKV use lossless stream-copy remux when codecs allow; other
         targets (and incompatible codecs) fall back to high-quality encodes.
         Container metadata (creation date, etc.) is mapped over.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pillow_heif
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()
try:
    pillow_heif.register_avif_opener()
except Exception:  # noqa: BLE001 — AVIF support is optional in older builds
    pass

IMAGE_EXTS = {".heic", ".heif", ".hif", ".avif", ".jpg", ".jpeg", ".png",
              ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTS = {".mov", ".qt", ".mp4", ".m4v", ".avi", ".mkv", ".webm"}

IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "AVIF", "TIFF", "BMP", "PDF", "GIF")
EXT_FOR_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp",
                  "AVIF": ".avif", "TIFF": ".tiff", "BMP": ".bmp",
                  "PDF": ".pdf", "GIF": ".gif"}
# formats that can carry EXIF/ICC via Pillow
META_FORMATS = {"JPEG", "PNG", "WEBP", "AVIF", "TIFF"}

VIDEO_FORMATS = ("MP4", "MKV", "WEBM", "GIF", "MP3")
EXT_FOR_VIDEO_FORMAT = {"MP4": ".mp4", "MKV": ".mkv", "WEBM": ".webm",
                        "GIF": ".gif", "MP3": ".mp3"}

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

_MAX_LOG_BYTES = 5 * 1024 * 1024


def log_file() -> Path:
    """Persistent log location: %LOCALAPPDATA%/MediaTrans/logs or ~/.mediatrans/logs."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    d = Path(base) / "MediaTrans" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d / "mediatrans.log"


def app_log(message: str) -> None:
    """Append a line to the persistent log (kept under ~5 MB)."""
    try:
        lf = log_file()
        if lf.exists() and lf.stat().st_size > _MAX_LOG_BYTES:
            lf.replace(lf.with_suffix(".old.log"))
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(lf, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {message}\n")
    except OSError:
        pass  # logging must never break conversion


@dataclass
class ConvertOptions:
    image_format: str = "JPEG"          # JPEG|PNG|WEBP|AVIF|TIFF|BMP|PDF|GIF
    video_format: str = "MP4"           # MP4 | MKV | WEBM | GIF | MP3
    quality: int = 95                   # for JPEG / WebP / AVIF
    keep_metadata: bool = True
    parallel: bool = True               # fan out across CPU cores
    use_gpu: bool = True                # prefer hardware video encoders


@dataclass
class ConvertResult:
    ok: bool
    output: Optional[Path] = None
    message: str = ""


def cpu_workers() -> int:
    """Sensible parallelism based on the machine: all cores minus one,
    always at least 2 (video work is subprocess-bound, images release the
    GIL during encode), capped at 8 to bound memory use."""
    return max(2, min(8, (os.cpu_count() or 4) - 1))


_GPU_PRIORITY = ("h264_nvenc",      # NVIDIA
                 "h264_qsv",        # Intel Quick Sync
                 "h264_amf",        # AMD
                 "h264_videotoolbox")  # macOS
_GPU_ENCODER_CACHE: Optional[str] = None


def gpu_encoder() -> Optional[str]:
    """Return the best hardware H.264 encoder this ffmpeg build offers,
    or None if only software encoders are available."""
    global _GPU_ENCODER_CACHE
    if _GPU_ENCODER_CACHE is not None:
        return _GPU_ENCODER_CACHE if _GPU_ENCODER_CACHE != "" else None
    enc = ""
    try:
        r = _run([_ffmpeg_exe(), "-hide_banner", "-encoders"])
        enc = r.stdout or ""
    except Exception:  # noqa: BLE001
        _GPU_ENCODER_CACHE = ""
        return None
    for name in _GPU_PRIORITY:
        if name in enc:
            _GPU_ENCODER_CACHE = name
            return name
    _GPU_ENCODER_CACHE = ""
    return None


def _h264_gpu_args(encoder: str) -> list[str]:
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19"]
    if encoder == "h264_qsv":
        return ["-c:v", "h264_qsv", "-global_quality", "20"]
    if encoder == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "quality",
                "-rc", "vbr_peak", "-b:v", "8M"]
    return ["-c:v", "h264_videotoolbox", "-b:v", "6M"]


def unique_path(path: Path) -> Path:
    """Return `path` itself if free, otherwise path_1, path_2, ..."""
    if not path.exists():
        return path
    for i in range(1, 1000):
        cand = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not cand.exists():
            return cand
    return path


def detect_kind(path: Path) -> Optional[str]:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return None


def ffmpeg_available() -> bool:
    try:
        _ffmpeg_exe()
        return True
    except Exception:
        return False


def _ffmpeg_exe() -> str:
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, creationflags=_NO_WINDOW
    )


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """Flatten alpha onto white for formats without alpha (JPEG/BMP/PDF)."""
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
    """Save TIFF; libtiff rejects pre-serialized sub-IFDs under some builds,
    so degrade gracefully: LZW+full EXIF → LZW+IFD0-only → uncompressed+full."""
    attempts = []
    if exif:
        attempts.append({"exif": exif, "compression": "tiff_lzw"})
        attempts.append({"exif": exif})  # uncompressed keeps sub-IFDs everywhere
        stripped = Image.Exif()
        stripped.load(exif)
        stripped.pop(34665, None)  # Exif IFD pointer
        stripped.pop(34853, None)  # GPS IFD pointer
        attempts.append({"exif": stripped.tobytes(), "compression": "tiff_lzw"})
    else:
        attempts.append({"compression": "tiff_lzw"})
    attempts.append({})
    last_exc: Exception | None = None
    for extra in attempts:
        try:
            _save_with_xmp(img, dst, "TIFF", xmp=xmp, **extra,
                           **({"icc_profile": icc} if icc else {}))
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc  # type: ignore[misc]


def convert_image(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    fmt = opts.image_format.upper()
    if fmt not in IMAGE_FORMATS:
        return ConvertResult(False, message=f"unknown image format {fmt!r}")
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = unique_path(dst_dir / (src.stem + EXT_FOR_FORMAT[fmt]))
    try:
        with Image.open(src) as im:
            im.load()
            # Bake EXIF orientation into pixels and drop the stale tag
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                im = im.convert("RGB")

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
                if opts.quality >= 90:
                    kwargs["subsampling"] = 0  # keep full chroma at high quality
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
                return ConvertResult(True, dst, "converted")
            elif fmt == "PDF":
                im = _flatten_to_rgb(im)
                kwargs = {"resolution": 144.0}  # PDF stores no EXIF/ICC
                xmp = None
            elif fmt == "GIF":
                im = im.convert("RGB").quantize(colors=256)
                kwargs = {}
                xmp = None
            # PNG needs no extra kwargs: always lossless

            _save_with_xmp(im, dst, fmt, xmp=xmp, **kwargs)
        app_log(f"OK image [{fmt}]: {src} -> {dst}")
        return ConvertResult(True, dst, "converted")
    except Exception as exc:  # noqa: BLE001 — report any decode/save error per-file
        if dst.exists():
            dst.unlink(missing_ok=True)
        app_log(f"FAILED image -> {fmt}: {src}\n"
                f"  {type(exc).__name__}: {exc}")
        return ConvertResult(False, message=f"{type(exc).__name__}: {exc}")


def _ffmpeg_convert(src: Path, dst: Path, extra: list[str]) -> subprocess.CompletedProcess:
    ff = _ffmpeg_exe()
    return _run([ff, "-y", "-i", str(src), *extra, str(dst)])


def _ok_file(dst: Path) -> bool:
    return dst.exists() and dst.stat().st_size > 0


def _video_result(src: Path, dst: Path, vfmt: str,
                  r: subprocess.CompletedProcess) -> ConvertResult:
    """Shared success/failure handling + full diagnostics to the log file."""
    if r.returncode == 0 and _ok_file(dst):
        return ConvertResult(True, dst, "converted")
    dst.unlink(missing_ok=True)
    stderr = (r.stderr or "").strip()
    app_log(f"FAILED video -> {vfmt}: {src}\n"
            f"  exit code: {r.returncode}\n"
            f"  ffmpeg stderr:\n{textwrap.indent(stderr, '    ')}")
    lines = stderr.splitlines() or ["ffmpeg failed"]
    return ConvertResult(False, message=lines[-1][:300] + "  (details in log)")


def convert_video(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    vfmt = opts.video_format.upper()
    if vfmt not in VIDEO_FORMATS:
        return ConvertResult(False, message=f"unknown video format {vfmt!r}")
    try:
        _ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        app_log(f"FAILED video: {src} — ffmpeg not available: {exc}")
        return ConvertResult(False, message=f"ffmpeg not available: {exc}")

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = unique_path(dst_dir / (src.stem + EXT_FOR_VIDEO_FORMAT[vfmt]))
    meta = ["-map_metadata", "0"] if opts.keep_metadata else []
    # Map only the primary audio stream: newer iPhones record an extra
    # Apple "apac" (spatial audio) track ffmpeg can't decode, and mapping it
    # makes every output fail with "Error opening output files".
    streams = ["-map", "0:v:0", "-map", "0:a:0?"]

    def success(detail: str) -> ConvertResult:
        app_log(f"OK video [{detail}]: {src} -> {dst}")
        return ConvertResult(True, dst, detail)

    if vfmt == "MP4":
        # 1) lossless attempt: stream copy (H.264/HEVC video + AAC audio)
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams, "-c", "copy",
                             "-movflags", "+faststart"])
        if r.returncode == 0 and _ok_file(dst):
            return success("lossless remux")
        # 2) fallback: re-encode — hardware encoder first, then software x264
        dst.unlink(missing_ok=True)
        if opts.use_gpu:
            gpu = gpu_encoder()
            if gpu:
                r = _ffmpeg_convert(src, dst,
                                    [*meta, *streams, *_h264_gpu_args(gpu),
                                     "-pix_fmt", "yuv420p",
                                     "-c:a", "aac", "-b:a", "192k",
                                     "-movflags", "+faststart"])
                if r.returncode == 0 and _ok_file(dst):
                    return success(f"re-encoded ({gpu})")
                dst.unlink(missing_ok=True)
                app_log(f"GPU encoder {gpu} failed for {src}; "
                        f"falling back to software x264")
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams,
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                             "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "192k",
                             "-movflags", "+faststart"])
        res = _video_result(src, dst, "MP4", r)
        if res.ok:
            res.message = "re-encoded (H.264/AAC)"
            app_log(f"OK video [re-encoded (H.264/AAC)]: {src} -> {dst}")
        return res

    if vfmt == "MKV":
        # Matroska accepts virtually every codec → plain remux is lossless
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams, "-map", "0:s?", "-c", "copy"])
        if r.returncode == 0 and _ok_file(dst):
            return success("lossless remux")
        return _video_result(src, dst, "MKV", r)

    if vfmt == "WEBM":
        r = _ffmpeg_convert(src, dst,
                            [*meta, "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
                             "-row-mt", "1", "-c:a", "libopus", "-b:a", "128k"])
        res = _video_result(src, dst, "WEBM", r)
        if res.ok:
            res.message = "re-encoded (VP9/Opus)"
        return res

    if vfmt == "GIF":
        r = _ffmpeg_convert(src, dst,
                            ["-vf", "fps=12,scale=480:-1:flags=lanczos,"
                                    "split[a][b];[a]palettegen[p];[b][p]paletteuse",
                             "-loop", "0"])
        res = _video_result(src, dst, "GIF", r)
        if res.ok:
            res.message = "animated GIF (12 fps, 480px)"
        return res

    # MP3 — extract the audio track
    r = _ffmpeg_convert(src, dst, ["-vn", *meta, "-c:a", "libmp3lame", "-q:a", "2"])
    res = _video_result(src, dst, "MP3", r)
    if res.ok:
        res.message = "audio extracted (MP3)"
    return res


def convert_file(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    kind = detect_kind(src)
    if kind == "image":
        return convert_image(src, dst_dir, opts)
    if kind == "video":
        return convert_video(src, dst_dir, opts)
    return ConvertResult(False, message="unsupported file type")
