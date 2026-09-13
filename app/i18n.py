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
        "drop_hint": "Drag & drop .heic / .heif / .mov files here,\nor click “Add Files”.",
        "list_header": "Files ({n})",
        "group_format": "Output Format",
        "fmt_jpg": "JPG  (small, lossy)",
        "fmt_png": "PNG  (lossless)",
        "fmt_webp": "WebP  (lossless at 100)",
        "video_note": "Video: MOV → MP4 (lossless remux when possible, otherwise high-quality H.264)",
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
        "dialog_filter": "Apple media (*.heic *.heif *.hif *.mov *.qt);;Images (*.heic *.heif *.hif);;Videos (*.mov *.qt);;All files (*)",
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
        "drop_hint": "将 .heic / .heif / .mov 文件拖到这里，\n或点击“添加文件”。",
        "list_header": "文件列表（{n}）",
        "group_format": "输出格式",
        "fmt_jpg": "JPG（体积小，有损）",
        "fmt_png": "PNG（无损）",
        "fmt_webp": "WebP（质量100时无损）",
        "video_note": "视频：MOV → MP4（优先无损封装，必要时转为高质量 H.264）",
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
        "dialog_filter": "苹果媒体文件 (*.heic *.heif *.hif *.mov *.qt);;图片 (*.heic *.heif *.hif);;视频 (*.mov *.qt);;所有文件 (*)",
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
