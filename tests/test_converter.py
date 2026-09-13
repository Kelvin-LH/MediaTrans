"""End-to-end test: run with `python tests/test_converter.py`.

Generates a HEIC with EXIF (device + GPS) and a MOV, converts them with the
MediaTrans engine, and verifies the metadata survived in every output.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from PIL.ExifTags import Base, GPS, IFD

from app import converter

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


def make_test_heic(dst: Path):
    """Gradient image with Apple-ish EXIF: Make/Model, DateTime, GPS."""
    img = Image.new("RGB", (320, 240))
    px = img.load()
    for y in range(240):
        for x in range(320):
            px[x, y] = (x * 255 // 319, y * 255 // 239, 128)

    exif = Image.Exif()
    exif[Base.Make] = "Apple"
    exif[Base.Model] = "iPhone 15 Pro"
    exif[Base.Software] = "MediaTrans test"
    sub_ifd = exif.get_ifd(IFD.Exif)
    sub_ifd[Base.DateTimeOriginal] = "2026:09:13 12:00:00"
    gps = exif.get_ifd(IFD.GPSInfo)
    gps[GPS.GPSLatitudeRef] = "N"
    gps[GPS.GPSLatitude] = (39.0, 54.0, 30.0)
    gps[GPS.GPSLongitudeRef] = "E"
    gps[GPS.GPSLongitude] = (116.0, 23.0, 29.0)

    img.save(dst, format="HEIF", exif=exif.tobytes(), quality=90)


def exif_dict(path: Path) -> dict:
    with Image.open(path) as im:
        exif = im.getexif()
        d = {k: v for k, v in exif.items()}
        d.update({f"exififd:{k}": v for k, v in exif.get_ifd(IFD.Exif).items()})
        d.update({f"gps:{k}": v for k, v in exif.get_ifd(IFD.GPSInfo).items()})
        d["_icc"] = bool(im.info.get("icc_profile"))
    return d


def test_images(tmp: Path):
    print("== image conversion ==")
    src = tmp / "IMG_0001.heic"
    make_test_heic(src)

    opts = converter.ConvertOptions()
    for fmt in ("JPEG", "PNG", "WEBP"):
        opts.image_format = fmt
        res = converter.convert_image(src, tmp / "out", opts)
        check(f"{fmt}: converted", res.ok, res.message)
        if not res.ok:
            continue
        meta = exif_dict(res.output)
        check(f"{fmt}: Make preserved", meta.get(Base.Make) == "Apple", str(meta))
        check(f"{fmt}: Model preserved", meta.get(Base.Model) == "iPhone 15 Pro")
        check(f"{fmt}: DateTimeOriginal preserved",
              meta.get(f"exififd:{int(Base.DateTimeOriginal)}") == "2026:09:13 12:00:00")
        lat = meta.get(f"gps:{int(GPS.GPSLatitude)}")
        check(f"{fmt}: GPS latitude preserved",
              lat is not None and
              tuple(float(x) for x in lat) == (39.0, 54.0, 30.0), str(lat))

    # lossless round-trip sanity: PNG output must match decoded HEIC pixels
    with Image.open(src) as a, Image.open(tmp / "out" / "IMG_0001.png") as b:
        check("PNG: pixels identical to decoded HEIC",
              a.convert("RGB").tobytes() == b.convert("RGB").tobytes())


def make_test_mov(dst: Path):
    ff = converter._ffmpeg_exe()
    subprocess.run(
        [ff, "-y",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
         "-f", "lavfi", "-i", "sine=duration=1:frequency=440",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-metadata", "creation_time=2026-09-13T12:00:00Z",
         str(dst)],
        check=True, capture_output=True, creationflags=converter._NO_WINDOW)


def test_video(tmp: Path):
    print("== video conversion ==")
    src = tmp / "VID_0002.mov"
    make_test_mov(src)
    opts = converter.ConvertOptions()
    res = converter.convert_video(src, tmp / "out", opts)
    check("MOV→MP4: converted", res.ok, res.message)
    if not res.ok:
        return
    check("MOV→MP4: lossless remux", res.message == "lossless remux", res.message)
    ff = converter._ffmpeg_exe()
    probe = subprocess.run([ff, "-i", str(res.output)], capture_output=True,
                           text=True, creationflags=converter._NO_WINDOW)
    err = probe.stderr
    check("MP4: h264 video stream", "Video: h264" in err, err[:200])
    check("MP4: aac audio stream", "Audio: aac" in err, err[:200])
    check("MP4: creation_time metadata preserved",
          "2026-09-13" in err, err[:200])


def test_strip_metadata(tmp: Path):
    print("== metadata stripping ==")
    src = tmp / "IMG_0001.heic"
    opts = converter.ConvertOptions(image_format="JPEG", keep_metadata=False)
    res = converter.convert_image(src, tmp / "out_strip", opts)
    check("strip: converted", res.ok, res.message)
    if res.ok:
        meta = exif_dict(res.output)
        check("strip: Make removed", not meta.get(Base.Make))


def main():
    with tempfile.TemporaryDirectory(prefix="mediatrans_") as d:
        tmp = Path(d)
        test_images(tmp)
        test_video(tmp)
        test_strip_metadata(tmp)
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
