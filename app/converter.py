"""Core conversion engine.

Images:  HEIC / HEIF / HIF  ->  JPG / PNG / WebP   (pixel data preserved,
metadata — EXIF incl. GPS & device info, XMP, ICC color profile — is copied
to the output whenever the target format can store it).

Videos:  MOV / QT  ->  MP4.  First a lossless stream-copy remux is
attempted (works for H.264/HEVC + AAC, the typical iPhone content); if the
codecs are not MP4-compatible it falls back to a high-quality H.264/AAC
re-encode. Container metadata (creation date, etc.) is mapped over.
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

IMAGE_EXTS = {".heic", ".heif", ".hif"}
VIDEO_EXTS = {".mov", ".qt"}

IMAGE_FORMATS = ("JPEG", "PNG", "WEBP")
EXT_FOR_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


@dataclass
class ConvertOptions:
    image_format: str = "JPEG"          # JPEG | PNG | WEBP
    quality: int = 95                   # for JPEG / WebP
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
    """Flatten alpha onto white for formats without alpha (JPEG)."""
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
            if fmt == "JPEG":
                im = _flatten_to_rgb(im)

            exif = im.info.get("exif") if opts.keep_metadata else None
            icc = im.info.get("icc_profile") if opts.keep_metadata else None
            xmp = im.info.get("xmp") if opts.keep_metadata else None

            kwargs: dict = {}
            if exif:
                kwargs["exif"] = exif
            if icc:
                kwargs["icc_profile"] = icc

            if fmt == "JPEG":
                kwargs["quality"] = opts.quality
                if opts.quality >= 90:
                    kwargs["subsampling"] = 0  # keep full chroma at high quality
            elif fmt == "WEBP":
                if opts.quality >= 100:
                    kwargs["lossless"] = True
                else:
                    kwargs["quality"] = opts.quality
                    kwargs["method"] = 6
            # PNG needs no extra kwargs: always lossless

            _save_with_xmp(im, dst, fmt, xmp=xmp, **kwargs)
        return ConvertResult(True, dst, "converted")
    except Exception as exc:  # noqa: BLE001 — report any decode/save error per-file
        if dst.exists():
            dst.unlink(missing_ok=True)
        return ConvertResult(False, message=f"{type(exc).__name__}: {exc}")


def convert_video(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    try:
        ff = _ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        return ConvertResult(False, message=f"ffmpeg not available: {exc}")

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = unique_path(dst_dir / (src.stem + ".mp4"))
    common = ["-i", str(src), "-map_metadata", "0",
              "-map", "0:v:0", "-map", "0:a?", "-movflags", "+faststart"]

    # 1) Lossless attempt: stream copy (H.264/HEVC video + AAC audio)
    r = _run([ff, "-y", *common, "-c", "copy", str(dst)])
    if r.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
        return ConvertResult(True, dst, "lossless remux")

    # 2) Fallback: high-quality re-encode (ProRes, PCM audio, ... )
    if dst.exists():
        dst.unlink(missing_ok=True)
    r = _run([ff, "-y", *common,
              "-c:v", "libx264", "-preset", "medium", "-crf", "18",
              "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", str(dst)])
    if r.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
        return ConvertResult(True, dst, "re-encoded (H.264/AAC)")

    if dst.exists():
        dst.unlink(missing_ok=True)
    detail = (r.stderr or "ffmpeg failed").strip().splitlines()
    return ConvertResult(False, message=detail[-1][:300] if detail else "ffmpeg failed")


def convert_file(src: Path, dst_dir: Path, opts: ConvertOptions) -> ConvertResult:
    kind = detect_kind(src)
    if kind == "image":
        return convert_image(src, dst_dir, opts)
    if kind == "video":
        return convert_video(src, dst_dir, opts)
    return ConvertResult(False, message="unsupported file type")
