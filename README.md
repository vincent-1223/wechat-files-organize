# WeChat Files Organize

Windows 桌面工具，通过 USB 和 ADB 读取 Android 手机中可访问的微信图片与视频，按月份整理、按内容去重并安全导出。

![桌面界面预览](docs/screenshot-main.png)

## 当前状态

这是首个可运行版本，重点完成桌面界面和核心数据流程：

- Windows / PySide6 桌面界面
- ADB 设备识别与 Android / 微信版本读取
- 微信候选媒体目录探测
- 图片和视频浅层分类
- 真实图片缩略图和视频首帧预览，单击即可查看或播放
- 按月份分组浏览、搜索、筛选和多选
- 后台扫描与真实进度
- SHA-256 内容去重
- 按 `年/月/图片|视频` 导出
- 扫描能力报告
- 始终可见的安全清理入口，只清理已导出并通过 SHA-256 校验的手动勾选文件

已使用 OPPO Find X9（Android 17、微信 8.0.79）完成一轮真实只读扫描，详见
[P0 真机验证记录](docs/p0-real-device-verification.md)。

## Windows 下载

从 GitHub Releases 下载：

- `WeChat-Files-Organize-Setup-0.2.0.exe`：按当前用户安装，无需管理员权限。
- `WeChat-Files-Organize-Portable-0.2.0.exe`：免安装，双击启动。

发布包内置 ADB，用户不需要单独安装 Android Platform Tools。当前版本未做商业代码签名，
Windows SmartScreen 可能显示“未知发布者”。

聊天记录中尚未保存到公共存储的媒体仍受 Android 权限限制。工具不会使用 Root、破解、数据库解密或 AI 上传绕过限制，也不会承诺提取全部聊天媒体。

## 开发环境

- Windows 10/11
- Python 3.11+
- Android Platform Tools（ADB）

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## 运行

连接 Android 手机并开启 USB 调试后：

```powershell
.\.venv\Scripts\python -m wechat_media_exporter
```

使用示例数据预览界面：

```powershell
.\.venv\Scripts\python -m wechat_media_exporter --demo
```

生成界面截图：

```powershell
.\.venv\Scripts\python -m wechat_media_exporter --demo --screenshot screenshots/main.png
```

## ADB

程序会依次查找：

1. `tools/adb/platform-tools/adb.exe`
2. `tools/adb/adb.exe`
3. 系统 `PATH` 中的 `adb`

可运行以下命令下载官方 Android Platform Tools 到项目的忽略目录：

```powershell
.\scripts\fetch-adb.ps1
```

## 测试

```powershell
.\.venv\Scripts\python -m pytest
```

仅执行 P0 扫描并生成 JSON、Markdown 报告：

```powershell
.\.venv\Scripts\python scripts\p0_scan.py
```

## 当前限制

- 首版只读取普通 ADB 权限可访问的目录。
- 无扩展名文件会以“待识别”状态保留，不会直接当作原图。
- 首次扫描后会在后台生成媒体缩略图，用时取决于媒体数量和 USB 传输速度。
- 去重只在已有文件哈希和新导出文件哈希之间执行，不会把相似图片误判为重复。
- 手机文件清理功能尚未开放；必须先完成导出与双重校验，再由用户手动选择文件。

