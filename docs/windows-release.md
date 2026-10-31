# Windows 发布构建

## 产物

- `WeChat-Files-Organize-Portable-0.1.0.exe`：单文件便携版，双击启动。
- `WeChat-Files-Organize-Setup-0.1.0.exe`：按当前用户安装，无需管理员权限。

便携版和安装版均内嵌官方 Android Platform Tools（ADB），不依赖系统单独安装。

## 构建

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\packaging\windows\build_release.ps1
```

只构建便携版：

```powershell
.\packaging\windows\build_release.ps1 -SkipInstaller
```

产物写入 `release/`。该目录被 Git 忽略；正式发布时应当把 EXE 作为 GitHub Release 附件上传，而不是提交进仓库历史。

## 注意

当前 EXE 未进行商业代码签名。Windows SmartScreen 可能提示“未知发布者”。正式对外分发前应配置代码签名证书。
