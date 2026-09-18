<div align="center">

# MediaTrans

**苹果 HEIC / MOV 转换为通用格式 —— 完整保留所有元数据。**

中文说明 | [English](README.md)

[![Tests](https://github.com/Kelvin-LH/MediaTrans/actions/workflows/tests.yml/badge.svg)](https://github.com/Kelvin-LH/MediaTrans/actions/workflows/tests.yml)
[![Build Release](https://github.com/Kelvin-LH/MediaTrans/actions/workflows/release.yml/badge.svg)](https://github.com/Kelvin-LH/MediaTrans/actions/workflows/release.yml)
[![License](https://img.shields.io/github/license/Kelvin-LH/MediaTrans)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

</div>

---

MediaTrans 可以把苹果专有的 **HEIC / HEIF 照片**和 **MOV 视频**转换为通用格式，
同时完整保留原文件记录的全部信息：EXIF、**GPS 位置**、**设备信息**（品牌 / 机型 /
镜头）、拍摄时间以及 ICC 色彩配置。提供中英双语桌面应用，**同时提供可脚本化的
命令行工具**。

| 浅色 | 深色 |
|---|---|
| ![English UI](docs/screenshot_en.png) | ![中文界面 · 深色](docs/screenshot_dark_zh.png) |

## ✨ 功能特性

### 转换能力
- 🖼 **图片**：`HEIC / HEIF / HIF / AVIF / JPG / PNG / WebP / BMP / TIFF` →
  `JPG / PNG / WebP / AVIF / TIFF / BMP / PDF / GIF`
  - PNG、WebP（质量100）、TIFF-LZW 与 BMP 输出为**像素级无损**
  - JPG 以最高实用质量保存（默认 95，≥90 时保留完整 4:4:4 色度）
- 🎬 **视频**：`MOV / QT / MP4 / M4V / AVI / MKV / WebM` →
  `MP4 / MKV / WebM / GIF`，并可提取音轨为 `MP3 / M4A / WAV / FLAC / OGG`
  - 编码与目标容器兼容时（H.264/HEVC + AAC，即 iPhone 常见内容）**无损流复制封装**
  - 遇到 ProRes 等特殊编码自动回退到 GPU 或高质量软件编码
- 🎵 **音频**：`MP3 / M4A / AAC / WAV / FLAC / OGG / OPUS` → `MP3 / M4A / WAV / FLAC / OGG`
- 📍 **元数据保留**：EXIF（拍摄时间、ISO、曝光……）、**GPS 位置**、**设备信息**、
  XMP 与 ICC 色彩配置，只要目标格式支持就全部写入
- 🔐 **隐私模式**：一键清除全部元数据（命令行 `--no-metadata`）

### 工作流
- 📁 **文件夹与拖拽** —— 直接把整个相册拖进来，自动递归扫描
- 🎚 **预设方案** —— 网页优化、社交/邮件、归档（无损）、最大兼容性、极限压缩
- 📐 **缩放** —— 限制最长边并保持比例，图片与视频均支持
- 🗓 **按拍摄日期归档** —— 自动写入 `YYYY/MM` 目录
- ⚔️ **冲突策略** —— 都保留（自动加序号）/ 覆盖 / 跳过
- 🕒 **时间戳保留** —— 输出文件继承源文件的日期属性
- 📊 **实时汇总** —— 转换前后体积、压缩比例、速度、逐文件体积变化
- 🌐 **双语界面**，支持**深色模式**，设置自动记忆
- 🖥 **自适应界面** —— 从 780×460 到 4K 分辨率自动重排布局，100%–200% 缩放下
  文字均不裁切；窗口大小与位置自动记忆
- 📜 **诊断能力** —— 每次转换都写入日志（含完整工具输出）；一键打开日志，
  双击失败条目查看原始报错
- ⚡ **并行与 GPU 加速** —— 按 CPU 核数并行，自动探测
  NVENC / QSV / AMF / VideoToolbox

## 🚀 快速开始

### 下载安装包

到 [Releases 页面](https://github.com/Kelvin-LH/MediaTrans/releases) 下载对应平台版本 ——
每个版本 tag 都会由 CI 自动构建 Windows、macOS（Intel 与 Apple Silicon）、Linux 安装包。

> 未配置签名密钥（`WINDOWS_CERT_B64`、`MACOS_CERT_B64`）时产物为未签名状态，
> 系统可能弹出 SmartScreen / Gatekeeper 提示，处理方式见 Release 说明。
> macOS 首次打开请右键点击应用选择“打开”。

### 使用 pip 安装

```bash
pip install git+https://github.com/Kelvin-LH/MediaTrans.git
mediatrans --help          # 命令行
mediatrans-gui             # 桌面应用
```

### 从源码运行

```bash
pip install -r requirements.txt
python run.py              # 桌面应用
python -m app --help       # 命令行
```

环境要求：Python 3.10+，支持 Windows / macOS / Linux。

### 打包为独立可执行文件

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name MediaTrans --icon MediaTrans.ico \
  --collect-all pillow_heif --collect-all imageio_ffmpeg run.py
```

## 🖥 命令行工具

`mediatrans` 接受文件**或文件夹**，自动转换其中所有支持的媒体。专为脚本与 CI 设计：
全部成功退出码为 `0`，部分失败为 `1`，用法错误为 `2`。

```bash
# 转换单张照片，保留元数据
mediatrans IMG_0001.heic -f webp -o converted/

# 整个相册，缩放并按拍摄日期归档
mediatrans ~/Pictures/iPhone --resize 2560 --quality 88 --by-date -o ~/Pictures/web

# 视频转 MP4（编码兼容时无损封装）
mediatrans clip.mov -f mp4

# 从视频提取音频，或转换音频格式
mediatrans interview.mov -f mp3
mediatrans album.flac -f m4a

# 先预览不写任何文件，再正式执行
mediatrans vacation/ -f jpg --dry-run
mediatrans vacation/ -f jpg -o out/ --skip-existing

# 供脚本/CI 使用的机器可读输出
mediatrans photos/ -f avif --json | jq .converted

# 转换前查看元数据
mediatrans info IMG_0001.heic
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `-f, --format` | 输出格式（`jpg` `png` `webp` `avif` `tiff` `bmp` `pdf` `gif` `mp4` `mkv` `webm` `mp3` `m4a` `wav` `flac` `ogg`） |
| `-o, --output` | 输出目录（默认与源文件同目录） |
| `-q, --quality` | JPEG / WebP / AVIF 质量 1–100 |
| `--resize` | 限制最长边像素数 |
| `--by-date` | 按拍摄日期归档到 `YYYY/MM` |
| `--no-metadata` | 清除 EXIF / GPS / 设备信息 |
| `--no-timestamps` | 不复制源文件日期属性 |
| `--conflict`、`--overwrite`、`--skip-existing` | 输出已存在时的处理方式 |
| `--no-parallel`、`--jobs N` | 控制并行度 |
| `--no-gpu` | 强制使用软件视频编码 |
| `-n, --dry-run` | 只显示计划，不写入任何文件 |
| `--json`、`--quiet`、`-v` | 输出格式控制 |
| `--list-formats` | 列出支持的格式、编码器与硬件能力 |

## 📋 转换原理

| 输入 | 输出 | 方式 | 是否无损 |
|---|---|---|---|
| HEIC / HEIF / HIF / AVIF | PNG / BMP / TIFF-LZW | 像素级精确重编码 | ✅ 无损 |
| HEIC / HEIF / HIF / AVIF | WebP | 质量 100 时使用无损模式 | ✅ 无损 |
| HEIC / HEIF / HIF / AVIF | JPG | 高质量编码（q95、4:4:4） | ⚠️ JPG 格式下的最佳质量 |
| 各类支持图片 | PDF / GIF | 文档 / 256 色输出 | ⚠️ 内容保留 |
| MOV / QT / MP4 / AVI / MKV | MP4 | 流复制（`-c copy`） | ✅ 编码兼容时完全无损 |
| MOV / QT / MP4 / AVI / MKV | MKV | 流复制 | ✅ Matroska 兼容一切编码 |
| MOV / QT / MP4 / AVI / MKV | MP4 / MKV | GPU 或 H.264 CRF 18 转码 | ⚠️ 回退方案（ProRes、缩放等） |
| MOV / QT / MP4 / AVI / MKV | WebM / GIF / 音频 | VP9+Opus / 调色板动图 / 提取音轨 | ⚠️ 重编码 |

**元数据处理**：EXIF（含 GPS IFD 与设备字段）、XMP 和 ICC 配置会从源文件读出，
在目标容器支持的情况下原样写入。EXIF 方向信息会被烘焙进像素，即使查看器忽略
方向标签，图片方向也始终正确。

**关于“无损”**：JPG 本身有损，WebM/GIF 必须重编码 —— 这些场景我们使用实际可行的
最高质量，画质差异肉眼不可辨。真正无损的路径是 PNG、WebP-100、TIFF-LZW、BMP、
WAV/FLAC 以及 MP4/MKV 无损封装。

## ⚙️ 注意事项与限制

- 较新 iPhone 录制的**空间音频轨道**（`apac`）ffmpeg 无法解码；MediaTrans 会只映射
  主 AAC 音轨，保证转换成功而不是因未知流失败。
- **实况照片（Live Photo）**按两个独立文件处理（同名的 HEIC 与 MOV）——两者都会
  转换，且输出后文件名配对关系保持不变。
- **多图 HEIC**（连拍）导出主图。
- 启用缩放时会跳过 MP4/MKV 的无损封装快速路径（缩放必须重编码）。
- **显示要求**：窗口约需 780×460 逻辑像素。更小的屏幕上仍会在可用区域内打开、
  各面板均可滚动，但界面会比较局促。

## ❓ 常见问题

**为什么不能直接把 .heic 改名为 .jpg？**
改后缀既不会转码也不会提升兼容性 —— 数据仍是 HEVC 编码。MediaTrans 会正确
解码并重新编码，同时把元数据一并带过去。

**我的数据会被上传吗？**
不会。所有处理都在本机完成，没有遥测。详见 [SECURITY.md](SECURITY.md)。

**视频转换失败，怎么查原因？**
打开日志，里面有该次失败完整的 ffmpeg 输出。
Windows：`%LOCALAPPDATA%\MediaTrans\logs\mediatrans.log`；
macOS / Linux：`~/MediaTrans/logs/mediatrans.log`。
界面里可点“查看日志”，或双击失败条目查看原始报错。

**会用上我的显卡吗？**
当视频必须重编码时，MediaTrans 会探测 NVENC、Quick Sync、AMF、VideoToolbox，
优先使用可用的硬件编码器，失败时回退软件 x264。无损封装不需要任何编码器。

**一次能处理多少文件？**
上千个也没问题 —— 任务按 CPU 核数并行（2–8 个 worker）。
可用 `--jobs N` 覆盖，`--no-parallel` 改为串行。

## 🤝 参与贡献

欢迎贡献！项目结构、如何新增格式、PR 检查清单见
[CONTRIBUTING.md](CONTRIBUTING.md)，版本变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## ⭐ Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=Kelvin-LH/MediaTrans&type=Date)](https://star-history.com/#Kelvin-LH/MediaTrans&Date)

## 📄 许可证

[MIT](LICENSE)
