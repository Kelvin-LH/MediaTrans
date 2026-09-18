"""Bilingual strings (English / 简体中文) for MediaTrans."""

from __future__ import annotations

import contextlib

LANG_NAMES = {"en": "English", "zh": "简体中文"}

_current = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # window & top bar
        "window_title": "MediaTrans — HEIC / MOV to universal formats",
        "language": "Language",
        "theme_dark": "Dark mode",
        "theme_light": "Light mode",
        "view_log": "View Log",
        "menu_about": "About MediaTrans",
        # queue
        "list_header": "Queue — {n} file(s)",
        "list_empty": "Queue — drop files or folders here",
        "tooltip_list": "Drag & drop files or whole folders; double-click a file for details",
        "tooltip_log": "Double-click a failed entry to see the full error",
        "add_files": "Add Files",
        "add_folder": "Add Folder",
        "remove": "Remove",
        "clear": "Clear",
        "status_added": "Added {n} file(s).",
        # presets
        "group_preset": "Preset",
        "preset_custom": "Custom (my settings)",
        "preset_web": "Web optimized — WebP q85, max 2560px",
        "preset_social": "Social / email — JPG q88, max 1920px",
        "preset_archive": "Archive (lossless) — PNG / MKV / FLAC",
        "preset_compat": "Maximum compatibility — JPG q95 / MP4",
        "preset_small": "Smallest size — WebP q75, max 1280px",
        "preset_note": "A preset fills in the formats and quality below; changing anything switches back to Custom.",
        # formats
        "group_format": "Output Format",
        "image_format": "Image",
        "video_format": "Video",
        "audio_format": "Audio",
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
        "vfmt_m4a": "M4A  (audio only, AAC)",
        "vfmt_wav": "WAV  (audio only, uncompressed)",
        "vfmt_flac": "FLAC  (audio only, lossless)",
        "vfmt_ogg": "OGG  (audio only, Vorbis)",
        "afmt_mp3": "MP3  (universal)",
        "afmt_m4a": "M4A  (AAC)",
        "afmt_wav": "WAV  (uncompressed)",
        "afmt_flac": "FLAC  (lossless)",
        "afmt_ogg": "OGG  (Vorbis)",
        "video_note": "Lossless stream-copy when the container allows; otherwise automatic high-quality re-encode.",
        # quality & resize
        "quality": "Quality",
        "resize_enable": "Resize",
        "resize": "Long edge",
        # metadata
        "group_metadata": "Metadata & Files",
        "keep_metadata": "Preserve EXIF / GPS / device info / ICC",
        "keep_timestamps": "Keep original file dates",
        "organize_by_date": "Sort output into YYYY/MM by date",
        "metadata_note": "Kept automatically when the target format supports it (JPG, PNG, WebP, TIFF, AVIF).",
        # performance
        "group_performance": "Performance",
        "parallel_tip": "Parallel conversion (auto CPU scaling)",
        "gpu_tip": "GPU video encoding (NVENC / QSV / AMF)",
        "gpu_found": "Hardware encoder detected: {name} — used automatically when a re-encode is needed.",
        "gpu_none": "No hardware video encoder found — software encoding will be used.",
        # output
        "group_output": "Output",
        "out_same": "Same folder as source file",
        "out_custom": "Custom folder:",
        "browse": "Browse…",
        "conflict": "If file exists:",
        "conflict_rename": "Keep both (add a number)",
        "conflict_overwrite": "Overwrite",
        "conflict_skip": "Skip",
        # actions & status
        "convert": "Convert",
        "cancel": "Cancel",
        "open_output": "Open Output Folder",
        "status_ready": "Ready. Add files or folders to begin.",
        "status_converting": "Converting {i}/{n}: {name}",
        "status_cancelling": "Cancelling…",
        "status_cancelled": "Cancelled.",
        "status_done": "Done: {ok} converted, {fail} failed, {skip} skipped · "
                       "{secs:.1f}s ({speed:.1f} files/s)",
        "log_ok": "✔ {name}  [{out}]{detail}",
        "log_fail": "✘ {name} — {reason}",
        "log_summary": "Total: {inb} → {outb}  ({pct:.0f}% smaller)",
        "size_delta": "  {arrow}{pct:.0f}%",
        "log_detail_hint": "Full output is in the log file:",
        "error_detail": "Error details",
        "copy": "Copy",
        # dialogs
        "err_no_files": "Please add files first.",
        "ffmpeg_missing": "ffmpeg is not available — video/audio conversion is disabled. Run: pip install imageio-ffmpeg",
        "dialog_title": "Select media files",
        "dialog_folder": "Select a folder (scanned recursively)",
        "dialog_filter": "Media files (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm *.mp3 *.m4a *.aac *.wav *.flac *.ogg *.opus);;Images (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff);;Videos (*.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm);;Audio (*.mp3 *.m4a *.aac *.wav *.flac *.ogg *.opus);;All files (*)",
        "about_text": "MediaTrans {version}\n\nConvert Apple HEIC images and MOV videos to universal formats\n"
                      "(JPG / PNG / WebP / AVIF / TIFF / PDF / GIF / MP4 / MKV / WebM / MP3 …)\n"
                      "while preserving EXIF, GPS, device info and color profiles.\n\n"
                      "Batch conversion with parallel workers and GPU-accelerated video encoding.\n"
                      "Also available on the command line:  mediatrans --help\n\n"
                      "MIT License — {repo}",
    },
    "zh": {
        "window_title": "MediaTrans — HEIC / MOV 转通用格式",
        "language": "语言",
        "theme_dark": "深色模式",
        "theme_light": "浅色模式",
        "view_log": "查看日志",
        "menu_about": "关于 MediaTrans",
        "list_header": "任务队列 — {n} 个文件",
        "list_empty": "任务队列 — 把文件或文件夹拖到这里",
        "tooltip_list": "可拖入文件或整个文件夹；双击文件查看详细信息",
        "tooltip_log": "双击失败条目可查看完整错误",
        "add_files": "添加文件",
        "add_folder": "添加文件夹",
        "remove": "移除",
        "clear": "清空",
        "status_added": "已添加 {n} 个文件。",
        "group_preset": "预设方案",
        "preset_custom": "自定义（使用我的设置）",
        "preset_web": "网页优化 — WebP 质量85，最长边 2560px",
        "preset_social": "社交/邮件 — JPG 质量88，最长边 1920px",
        "preset_archive": "归档（无损）— PNG / MKV / FLAC",
        "preset_compat": "最大兼容性 — JPG 质量95 / MP4",
        "preset_small": "极限压缩 — WebP 质量75，最长边 1280px",
        "preset_note": "预设会自动填好下方格式与质量；任何手动改动都会切回“自定义”。",
        "group_format": "输出格式",
        "image_format": "图片",
        "video_format": "视频",
        "audio_format": "音频",
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
        "vfmt_m4a": "M4A（仅提取音频，AAC）",
        "vfmt_wav": "WAV（仅提取音频，未压缩）",
        "vfmt_flac": "FLAC（仅提取音频，无损）",
        "vfmt_ogg": "OGG（仅提取音频，Vorbis）",
        "afmt_mp3": "MP3（通用）",
        "afmt_m4a": "M4A（AAC）",
        "afmt_wav": "WAV（未压缩）",
        "afmt_flac": "FLAC（无损）",
        "afmt_ogg": "OGG（Vorbis）",
        "video_note": "目标容器支持时无损流复制；不支持时自动转为高质量重编码。",
        "quality": "质量",
        "resize_enable": "缩放",
        "resize": "最长边",
        "group_metadata": "元数据与文件",
        "keep_metadata": "保留 EXIF / GPS / 设备信息 / 色彩配置",
        "keep_timestamps": "保留原文件日期时间",
        "organize_by_date": "按日期归档到 YYYY/MM",
        "metadata_note": "目标格式支持时自动保留（JPG、PNG、WebP、TIFF、AVIF 均支持）。",
        "group_performance": "性能",
        "parallel_tip": "并行转换（按 CPU 核数调度）",
        "gpu_tip": "GPU 硬件编码（NVENC / QSV / AMF）",
        "gpu_found": "检测到硬件编码器：{name}，需要转码时自动启用。",
        "gpu_none": "未检测到硬件视频编码器，将使用软件编码。",
        "group_output": "输出位置",
        "out_same": "与源文件相同目录",
        "out_custom": "自定义目录：",
        "browse": "浏览…",
        "conflict": "文件已存在时：",
        "conflict_rename": "都保留（自动加序号）",
        "conflict_overwrite": "覆盖",
        "conflict_skip": "跳过",
        "convert": "开始转换",
        "cancel": "取消",
        "open_output": "打开输出文件夹",
        "status_ready": "就绪。请添加文件或文件夹。",
        "status_converting": "正在转换 {i}/{n}：{name}",
        "status_cancelling": "正在取消…",
        "status_cancelled": "已取消。",
        "status_done": "完成：成功 {ok} 个，失败 {fail} 个，跳过 {skip} 个 · "
                       "{secs:.1f} 秒（{speed:.1f} 文件/秒）",
        "log_ok": "✔ {name}  [{out}]{detail}",
        "log_fail": "✘ {name} — {reason}",
        "log_summary": "合计：{inb} → {outb}（减小 {pct:.0f}%）",
        "size_delta": "  {arrow}{pct:.0f}%",
        "log_detail_hint": "完整输出记录在日志文件：",
        "error_detail": "错误详情",
        "copy": "复制",
        "err_no_files": "请先添加文件。",
        "ffmpeg_missing": "未找到 ffmpeg，视频/音频转换不可用。请运行：pip install imageio-ffmpeg",
        "dialog_title": "选择媒体文件",
        "dialog_folder": "选择文件夹（将递归扫描）",
        "dialog_filter": "媒体文件 (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm *.mp3 *.m4a *.aac *.wav *.flac *.ogg *.opus);;图片 (*.heic *.heif *.hif *.avif *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff);;视频 (*.mov *.qt *.mp4 *.m4v *.avi *.mkv *.webm);;音频 (*.mp3 *.m4a *.aac *.wav *.flac *.ogg *.opus);;所有文件 (*)",
        "about_text": "MediaTrans {version}\n\n将苹果 HEIC 图片和 MOV 视频转换为通用格式\n"
                      "（JPG / PNG / WebP / AVIF / TIFF / PDF / GIF / MP4 / MKV / WebM / MP3 …），\n"
                      "完整保留 EXIF、GPS 位置、设备信息和色彩配置。\n\n"
                      "支持并行批量转换与 GPU 硬件加速视频编码。\n"
                      "同时提供命令行工具：mediatrans --help\n\n"
                      "MIT 许可证 — {repo}",
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
        with contextlib.suppress(KeyError, IndexError):
            text = text.format(**kwargs)
    return text
