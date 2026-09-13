<div align="center">

# MediaTrans

**苹果 HEIC / MOV 无损转换为通用格式 —— 完整保留所有元数据。**

中文说明 | [English](README.md)

![License](https://img.shields.io/github/license/Kelvin-LH/MediaTrans)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

</div>

---

MediaTrans 是一款中英双语的桌面应用，可以把苹果专有的 **HEIC / HEIF 照片**和
**MOV 视频**转换为通用格式 **JPG / PNG / WebP / MP4**，同时完整保留原文件的
全部内容信息：EXIF、**GPS 位置**、**设备信息**（品牌 / 机型 / 镜头）、拍摄时间
以及 ICC 色彩配置。

| | |
|---|---|
| ![English UI](docs/screenshot_en.png) | ![中文界面](docs/screenshot_zh.png) |

## ✨ 功能特性

- 🖼 **图片**：`HEIC / HEIF / HIF → JPG / PNG / WebP`
  - PNG 与 WebP（质量 100）输出为**像素级无损**（已验证与 HEIC 解码结果逐字节一致）
  - JPG 以最高实用质量保存（默认 95，≥90 时保留完整 4:4:4 色度）
- 🎬 **视频**：`MOV / QT → MP4`
  - 编码与 MP4 兼容时（H.264/HEVC + AAC，即 iPhone 常见内容）**无损流复制封装**
  - 遇到 ProRes 等特殊编码时自动回退为高质量 H.264（CRF 18）转码
- 📍 **元数据保留**：EXIF（拍摄时间、ISO、曝光……）、**GPS 位置**、**设备信息**、XMP 与 ICC 色彩配置，只要目标格式支持就全部写入
- 🌐 **原生双语界面**：内置中文与英文，随时切换，首次启动自动跟随系统语言
- 🖱 **拖拽添加**、批量转换、进度条、逐文件日志、随时取消
- 📁 输出到源文件目录或任意自定义目录；重名自动加后缀
- 🧩 无需安装外部工具 —— 静态 `ffmpeg` 随 pip 依赖自动提供

## 🚀 快速开始

```bash
pip install -r requirements.txt
python run.py
```

环境要求：Python 3.10+。支持 Windows、macOS、Linux。

### 打包为独立可执行文件（可选）

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name MediaTrans --collect-all pillow_heif run.py
```

## 📋 转换原理

| 输入 | 输出 | 方式 | 是否无损 |
|---|---|---|---|
| HEIC / HEIF / HIF | PNG | 像素级精确重编码 | ✅ 无损 |
| HEIC / HEIF / HIF | WebP | 质量 100 时使用无损模式 | ✅ 无损 |
| HEIC / HEIF / HIF | JPG | 高质量编码（q95、4:4:4） | ⚠️ JPG 格式下的最佳质量 |
| MOV / QT | MP4 | 流复制（`-c copy`） | ✅ 编码兼容时完全无损 |
| MOV / QT | MP4 | H.264 CRF 18 + AAC 转码 | ⚠️ ProRes 等场景的回退方案 |

元数据处理：EXIF（含 GPS IFD 与设备字段）、XMP 和 ICC 配置会从源文件读出，
在目标容器支持的情况下原样写入。EXIF 方向信息会被烘焙进像素，即使查看器忽略
方向标签，图片方向也始终正确。也可以一键关闭元数据保留（隐私模式）。

> 说明：JPG 本身是有损格式，“无损”指 PNG / WebP-100 以及 MP4 无损封装。
> JPG 已使用实际可行的最高质量，画质差异肉眼不可辨。

## ❓ 常见问题

**为什么不能直接把 .heic 改名为 .jpg？**
改后缀既不会转码也不会提升兼容性 —— 数据仍是 HEVC 编码。MediaTrans 会正确
解码并重新编码，同时把元数据一并带过去。

**我的数据会被上传吗？**
不会。所有处理都在本机完成。

**为什么输出的图片方向总是正确的？**
转换时 MediaTrans 会把 EXIF 方向应用到像素上，任何查看器都能正确显示。

**视频转换失败？**
请确认已安装 `imageio-ffmpeg`（已包含在 `requirements.txt` 中），它会提供
静态 ffmpeg，无需在系统中单独安装。

## ⭐ Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=Kelvin-LH/MediaTrans&type=Date)](https://star-history.com/#Kelvin-LH/MediaTrans&Date)

## 📄 许可证

[MIT](LICENSE)
