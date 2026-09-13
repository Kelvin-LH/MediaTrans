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


@dataclass
class ConvertOptions:
    image_format: str = "JPEG"          # JPEG|PNG|WEBP|AVIF|TIFF|BMP|PDF|GIF
    video_format: str = "MP4"           # MP4 | MKV | WEBM | GIF | MP3
    quality: int = 95                   # for JPEG / WebP / AVIF
    keep_metadata: bool = True


@dataclass
class ConvertResult:
    ok: bool
    output: Optional[Path] = None
    message: str = ""


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
        return ConvertResult(True, dst, "converted")
    except Exception as exc:  # noqa: BLE001 — report any decode/save error per-file
        if dst.exists():
            dst.unlink(missing_ok=True)
        return ConvertResult(False, message=f"{type(exc).__name__}: {exc}")


def _ffmpeg_convert(src: Path, dst: Path, extra: list[str]) -> subprocess.CompletedProcess:
    ff = _ffmpeg_exe()
    return _run([ff, "-y", "-i", str(src), *extra, str(dst)])


def _ok_file(dst: Path) -> bool:
    return dst.exists() and dst.stat().st_size > 0


def convert_video(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    vfmt = opts.video_format.upper()
    if vfmt not in VIDEO_FORMATS:
        return ConvertResult(False, message=f"unknown video format {vfmt!r}")
    try:
        _ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        return ConvertResult(False, message=f"ffmpeg not available: {exc}")

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = unique_path(dst_dir / (src.stem + EXT_FOR_VIDEO_FORMAT[vfmt]))
    meta = ["-map_metadata", "0"] if opts.keep_metadata else []
    streams = ["-map", "0:v:0", "-map", "0:a?"]

    if vfmt == "MP4":
        # 1) lossless attempt: stream copy (H.264/HEVC video + AAC audio)
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams, "-c", "copy",
                             "-movflags", "+faststart"])
        if r.returncode == 0 and _ok_file(dst):
            return ConvertResult(True, dst, "lossless remux")
        # 2) fallback: high-quality re-encode (ProRes, PCM audio, ...)
        dst.unlink(missing_ok=True)
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams,
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                             "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "192k",
                             "-movflags", "+faststart"])
        detail = "re-encoded (H.264/AAC)"
    elif vfmt == "MKV":
        # Matroska accepts virtually every codec → plain remux is lossless
        r = _ffmpeg_convert(src, dst,
                            [*meta, *streams, "-map", "0:s?", "-c", "copy"])
        detail = "lossless remux"
    elif vfmt == "WEBM":
        r = _ffmpeg_convert(src, dst,
                            [*meta, "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
                             "-row-mt", "1", "-c:a", "libopus", "-b:a", "128k"])
        detail = "re-encoded (VP9/Opus)"
    elif vfmt == "GIF":
        r = _ffmpeg_convert(src, dst,
                            ["-vf", "fps=12,scale=480:-1:flags=lanczos,"
                                    "split[a][b];[a]palettegen[p];[b][p]paletteuse",
                             "-loop", "0"])
        detail = "animated GIF (12 fps, 480px)"
    else:  # MP3 — extract the audio track
        r = _ffmpeg_convert(src, dst,
                            ["-vn", *meta, "-c:a", "libmp3lame", "-q:a", "2"])
        detail = "audio extracted (MP3)"

    if r.returncode == 0 and _ok_file(dst):
        return ConvertResult(True, dst, detail)

    dst.unlink(missing_ok=True)
    lines = (r.stderr or "ffmpeg failed").strip().splitlines()
    return ConvertResult(False, message=lines[-1][:300] if lines else "ffmpeg failed")


def convert_file(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    kind = detect_kind(src)
    if kind == "image":
        return convert_image(src, dst_dir, opts)
    if kind == "video":
        return convert_video(src, dst_dir, opts)
    return ConvertResult(False, message="unsupported file type")
