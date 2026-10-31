# WeChat Files Organize 0.1.0

发布日期：2026-10-31

## 功能

- Windows 桌面媒体库，支持图片、视频、月份和重复文件筛选
- ADB 设备检测，读取 Android、微信版本和真实目录权限
- 自动发现大小写不同的微信媒体目录
- 130+ 图片、14 个视频的 OPPO Find X9 真机扫描验证
- 按 `年/月/Images|Videos` 导出
- SHA-256 精确内容去重
- JSON / Markdown 真实扫描报告
- 手动安全清理入口，不会自动删除手机文件
- 内置 ADB，便携版无需安装

## 发布文件

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `WeChat-Files-Organize-Setup-0.1.0.exe` | 50,507,813 bytes | `0620AE315754CF6F326B078A96976BA9B859081F8B2AC077265DED845D74F3E5` |
| `WeChat-Files-Organize-Portable-0.1.0.exe` | 48,963,045 bytes | `6DE3CD9CA20296BB347F57E24E01AC058BA35447C55E0AF37FA043407ADF73ED` |

## 已知限制

- 远程手机媒体使用占位缩略图，尚未缓存真实图片预览。
- Android 应用私有目录仍有部分子目录无法访问，必须通过扫描报告明确展示。
- 未配置商业代码签名证书，Windows 可能显示 SmartScreen 提示。
- 当前发布仅覆盖 Windows x64。
