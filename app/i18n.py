"""Bilingual strings (English / 简体中文) for MediaTrans."""

from __future__ import annotations

LANG_NAMES = {"en": "English", "zh": "简体中文"}

_current = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "window_title": "MediaTrans — HEIC / MOV to universal formats",
        "language": "Language",
        "add_files": "Add Files",
        "clear": "Clear",
        "convert": "Convert",
        "cancel": "Cancel",
        "open_output": "Open Output Folder",
        "drop_hint": "Drag & drop photos or videos here\n(HEIC, HEIF, MOV, MP4, JPG, PNG…),\nor click “Add Files”.",
        "list_header": "Files ({n})",
        "group_format": "Output Format",
        "image_format": "Image",
        "video_format": "Video",
        "fmt_jpg": "JPG  (small, lossy)",
        "fmt_png": "PNG  (lossless)",
        "fmt_webp": "WebP  (lossless at 100)",
        "fmt_avif": "AVIF  (modern, compact)",
        "fmt_tiff": "TIFF  (lossless, archival)",
        "fmt_bmp": "BMP  (lossless, uncompressed)",
        "fmt_pdf": "PDF  (document)",
        "fmt_gif": "GIF  (256 colors)",
        "vfmt_mp4": "MP4  (universal, lossless remux)",
        "vfmt_mkv": "MKV  (lossless remux, keeps any codec)",
        "vfmt_webm": "WebM  (VP9/Opus, web-optimized)",
        "vfmt_gif": "GIF  (animated, 12 fps)",
        "vfmt_mp3": "MP3  (audio only)",
        "video_note": "Lossless stream-copy whenever the target container allows; otherwise automatic high-quality re-encode.",
        "quality": "Quality",
        "group_metadata": "Metadata",
        "keep_metadata": "Preserve EXIF / GPS / device info / color profile",
        "metadata_note": "Kept automatically when the target format supports it (JPG, PNG, WebP).",
        "group_output": "Output",
        "out_same": "Same folder as source file",
        "out_custom": "Custom folder:",
        "browse": "Browse…",
        "status_ready": "Ready. Add files to begin.",
        "status_converting": "Converting {i}/{n}: {name}",
        "status_done": "Finished: {ok} succeeded, {fail} failed.",
        "status_cancelled": "Cancelled.",
        "log_ok": "✔ {name} → {out}  [{detail}]",
        "log_fail": "✘ {name}: {reason}",
        "ffmpeg_missing": "ffmpeg is not available — video conversion is disabled. Run: pip install imageio-ffmpeg",
        "err_no_files": "Please add files first.",
        "dialog_title": "Select media files",
        "dialog_filter": "Media files (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm);;Images (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff);;Videos (*.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm);;All files (*)",
        "menu_help": "Help",
        "menu_about": "About MediaTrans",
        "about_text": "MediaTrans {version}\n\nConvert Apple HEIC images and MOV videos to universal formats\n(JPG / PNG / WebP / MP4) while preserving EXIF, GPS, device info\nand color profiles.\n\nMIT License — {repo}",
    },
    "zh": {
        "window_title": "MediaTrans — HEIC / MOV 转通用格式",
        "language": "语言",
        "add_files": "添加文件",
        "clear": "清空",
        "convert": "开始转换",
        "cancel": "取消",
        "open_output": "打开输出文件夹",
        "drop_hint": "将照片或视频拖到这里\n（HEIC、HEIF、MOV、MP4、JPG、PNG 等），\n或点击“添加文件”。",
        "list_header": "文件列表（{n}）",
        "group_format": "输出格式",
        "image_format": "图片",
        "video_format": "视频",
        "fmt_jpg": "JPG（体积小，有损）",
        "fmt_png": "PNG（无损）",
        "fmt_webp": "WebP（质量100时无损）",
        "fmt_avif": "AVIF（新一代，更紧凑）",
        "fmt_tiff": "TIFF（无损，适合存档）",
        "fmt_bmp": "BMP（无损，未压缩）",
        "fmt_pdf": "PDF（文档）",
        "fmt_gif": "GIF（256色）",
        "vfmt_mp4": "MP4（通用，优先无损封装）",
        "vfmt_mkv": "MKV（无损封装，兼容一切编码）",
        "vfmt_webm": "WebM（VP9/Opus，适合网页）",
        "vfmt_gif": "GIF（动图，12帧/秒）",
        "vfmt_mp3": "MP3（仅提取音频）",
        "video_note": "目标容器支持时无损流复制；不支持时自动转为高质量重编码。",
        "quality": "质量",
        "group_metadata": "元数据",
        "keep_metadata": "保留 EXIF / GPS 位置 / 设备信息 / 色彩配置",
        "metadata_note": "目标格式支持时自动保留（JPG、PNG、WebP 均支持）。",
        "group_output": "输出位置",
        "out_same": "与源文件相同目录",
        "out_custom": "自定义目录：",
        "browse": "浏览…",
        "status_ready": "就绪。请先添加文件。",
        "status_converting": "正在转换 {i}/{n}：{name}",
        "status_done": "完成：成功 {ok} 个，失败 {fail} 个。",
        "status_cancelled": "已取消。",
        "log_ok": "✔ {name} → {out}  [{detail}]",
        "log_fail": "✘ {name}：{reason}",
        "ffmpeg_missing": "未找到 ffmpeg，视频转换不可用。请运行：pip install imageio-ffmpeg",
        "err_no_files": "请先添加文件。",
        "dialog_title": "选择媒体文件",
        "dialog_filter": "媒体文件 (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm);;图片 (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff);;视频 (*.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm);;所有文件 (*)",
        "menu_help": "帮助",
        "menu_about": "关于 MediaTrans",
        "about_text": "MediaTrans {version}\n\n将苹果 HEIC 图片和 MOV 视频转换为通用格式\n（JPG / PNG / WebP / MP4），完整保留 EXIF、GPS 位置、\n设备信息和色彩配置。\n\nMIT 许可证 — {repo}",
    },
}


def set_language(lang: str) -> None:
    global _current
    if lang in _STRINGS:
        _current = lang


def current_language() -> str:
    return _current


def tr(key: str, **kwargs) -> str:
    text = _STRINGS.get(_current, {}).get(key) or _STRINGS["en"].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
