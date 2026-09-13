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
SKIP = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def skip(name: str, detail: str = ""):
    global SKIP
    SKIP += 1
    print(f"  SKIP  {name}  {detail}")


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
        d = {int(k): v for k, v in exif.items()}
        d.update({f"exififd:{int(k)}": v
                  for k, v in exif.get_ifd(IFD.Exif).items()})
        d.update({f"gps:{int(k)}": v
                  for k, v in exif.get_ifd(IFD.GPSInfo).items()})
        d["_icc"] = bool(im.info.get("icc_profile"))
    return d


def test_images(tmp: Path):
    print("== image conversion ==")
    src = tmp / "IMG_0001.heic"
    make_test_heic(src)

    with_meta = ("JPEG", "PNG", "WEBP", "TIFF", "AVIF")
    no_meta = ("BMP", "PDF", "GIF")
    for fmt in with_meta + no_meta:
        opts = converter.ConvertOptions(image_format=fmt)
        res = converter.convert_image(src, tmp / "out", opts)
        if not res.ok and fmt == "AVIF" and "avif" in res.message.lower():
            skip(f"{fmt}: no AVIF encoder in this Pillow build", res.message)
            continue
        check(f"{fmt}: converted", res.ok, res.message)
        if not res.ok:
            continue
        if fmt == "PDF":
            check(f"{fmt}: non-empty output", res.output.stat().st_size > 0)
            continue
        meta = exif_dict(res.output)
        if fmt in with_meta:
            check(f"{fmt}: Make preserved", meta.get(int(Base.Make)) == "Apple")
            check(f"{fmt}: Model preserved",
                  meta.get(int(Base.Model)) == "iPhone 15 Pro")
            check(f"{fmt}: DateTimeOriginal preserved",
                  meta.get(f"exififd:{int(Base.DateTimeOriginal)}")
                  == "2026:09:13 12:00:00")
            lat = meta.get(f"gps:{int(GPS.GPSLatitude)}")
            check(f"{fmt}: GPS latitude preserved",
                  lat is not None and
                  tuple(float(x) for x in lat) == (39.0, 54.0, 30.0), str(lat))
        else:
            check(f"{fmt}: no metadata expected",
                  not meta.get(int(Base.Make)))

    # lossless round-trip sanity: PNG output must match decoded HEIC pixels
    with Image.open(src) as a, Image.open(tmp / "out" / "IMG_0001.png") as b:
        check("PNG: pixels identical to decoded HEIC",
              a.convert("RGB").tobytes() == b.convert("RGB").tobytes())

    # cross-format input: PNG file -> JPG keeps its EXIF too
    png_src = tmp / "IMG_0003.png"
    with Image.open(src) as im:
        im.save(png_src, exif=Image.open(src).info.get("exif"))
    opts = converter.ConvertOptions(image_format="JPEG")
    res = converter.convert_image(png_src, tmp / "out", opts)
    check("PNG→JPG: converted", res.ok, res.message)
    if res.ok:
        meta = exif_dict(res.output)
        check("PNG→JPG: Make preserved", meta.get(int(Base.Make)) == "Apple")


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


def probe(dst: Path) -> str:
    ff = converter._ffmpeg_exe()
    probe = subprocess.run([ff, "-i", str(dst)], capture_output=True,
                           text=True, creationflags=converter._NO_WINDOW)
    return probe.stderr


def test_video(tmp: Path):
    print("== video conversion ==")
    src = tmp / "VID_0002.mov"
    make_test_mov(src)

    res = converter.convert_video(src, tmp / "out",
                                  converter.ConvertOptions(video_format="MP4"))
    check("MOV→MP4: converted", res.ok, res.message)
    if res.ok:
        check("MOV→MP4: lossless remux", res.message == "lossless remux")
        err = probe(res.output)
        check("MP4: h264 video stream", "Video: h264" in err, err[:200])
        check("MP4: aac audio stream", "Audio: aac" in err, err[:200])
        check("MP4: creation_time metadata preserved", "2026-09-13" in err)

    res = converter.convert_video(src, tmp / "out",
                                  converter.ConvertOptions(video_format="MKV"))
    check("MOV→MKV: converted", res.ok, res.message)
    if res.ok:
        check("MOV→MKV: lossless remux", res.message == "lossless remux")

    res = converter.convert_video(src, tmp / "out",
                                  converter.ConvertOptions(video_format="GIF"))
    check("MOV→GIF: converted", res.ok, res.message)

    res = converter.convert_video(src, tmp / "out",
                                  converter.ConvertOptions(video_format="MP3"))
    check("MOV→MP3: converted", res.ok, res.message)

    res = converter.convert_video(src, tmp / "out",
                                  converter.ConvertOptions(video_format="WEBM"))
    if not res.ok and "libvpx" in res.message.lower():
        skip("MOV→WebM: encoder not in bundled ffmpeg", res.message)
    else:
        check("MOV→WebM: converted", res.ok, res.message)


def test_parallel_and_gpu(tmp: Path):
    print("== parallel & GPU ==")
    check("cpu_workers() sane",
          2 <= converter.cpu_workers() <= 8, str(converter.cpu_workers()))
    enc = converter.gpu_encoder()
    print(f"  (info) gpu encoder: {enc or 'none'}")

    src = tmp / "IMG_0001.heic"
    make_test_heic(src)

    # thread-safety: many concurrent image conversions on one engine
    from concurrent.futures import ThreadPoolExecutor
    opts = converter.ConvertOptions(image_format="JPEG")
    with ThreadPoolExecutor(max_workers=converter.cpu_workers()) as ex:
        futs = [ex.submit(converter.convert_image, src, tmp / f"par{i}", opts)
                for i in range(converter.cpu_workers() * 2)]
        results = [f.result() for f in futs]
    check(f"parallel: {len(results)} concurrent conversions all OK",
          all(r.ok for r in results),
          "; ".join(r.message for r in results if not r.ok))

    # GPU re-encode path: ProRes MOV cannot be stream-copied into MP4
    ff = converter._ffmpeg_exe()
    prores = tmp / "VID_prores.mov"
    gen = subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "testsrc=duration=0.5:size=160x120:rate=15",
         "-c:v", "prores_ks", "-profile:v", "0", str(prores)],
        capture_output=True, creationflags=converter._NO_WINDOW)
    if gen.returncode != 0 or not prores.exists():
        skip("GPU/re-encode: prores encoder unavailable in bundled ffmpeg")
        return
    vopts = converter.ConvertOptions(video_format="MP4", use_gpu=True)
    res = converter.convert_video(prores, tmp / "out_v", vopts)
    check("ProRes→MP4: converted (GPU or software fallback)", res.ok, res.message)
    if res.ok:
        check("ProRes→MP4: re-encoded", "re-encoded" in res.message, res.message)
        err = probe(res.output)
        check("ProRes→MP4: playable h264 output", "Video: h264" in err, err[:200])


def test_strip_metadata(tmp: Path):
    print("== metadata stripping ==")
    src = tmp / "IMG_0001.heic"
    opts = converter.ConvertOptions(image_format="JPEG", keep_metadata=False)
    res = converter.convert_image(src, tmp / "out_strip", opts)
    check("strip: converted", res.ok, res.message)
    if res.ok:
        meta = exif_dict(res.output)
        check("strip: Make removed", not meta.get(int(Base.Make)))


def main():
    with tempfile.TemporaryDirectory(prefix="mediatrans_") as d:
        tmp = Path(d)
        test_images(tmp)
        test_video(tmp)
        test_parallel_and_gpu(tmp)
        test_strip_metadata(tmp)
    print(f"\n{PASS} passed, {FAIL} failed, {SKIP} skipped")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
