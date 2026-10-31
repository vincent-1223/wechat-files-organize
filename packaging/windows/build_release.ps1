param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$icon = Join-Path $projectRoot "wechat_media_exporter\assets\app-icon.ico"
$versionFile = Join-Path $PSScriptRoot "version_info.txt"
$installerScript = Join-Path $PSScriptRoot "installer.iss"
$distExe = Join-Path $projectRoot "dist\WeChatFilesOrganize.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtual environment not found. Follow README.md first."
}

& $python (Join-Path $projectRoot "scripts\generate_icon.py")

Push-Location $projectRoot
try {
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --onefile `
        --name WeChatFilesOrganize `
        --icon $icon `
        --version-file $versionFile `
        --add-data "wechat_media_exporter\assets;wechat_media_exporter\assets" `
        --add-data "tools\adb\platform-tools;tools\adb\platform-tools" `
        "wechat_media_exporter\__main__.py"

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    if (-not $SkipInstaller) {
        $innoCandidates = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            "C:\Program Files\Inno Setup 6\ISCC.exe"
        )
        $iscc = $innoCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $iscc) {
            throw "Inno Setup 6 was not found. Install it or rerun with -SkipInstaller."
        }

        New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "release") | Out-Null
        & $iscc $installerScript
        if ($LASTEXITCODE -ne 0) {
            throw "Inno Setup failed with exit code $LASTEXITCODE."
        }

        Copy-Item -LiteralPath $distExe `
            -Destination (Join-Path $projectRoot "release\WeChat-Files-Organize-Portable-0.2.0.exe") `
            -Force
    }
} finally {
    Pop-Location
}

Write-Host "Release build complete."
Write-Host "Portable: $(Join-Path $projectRoot 'release\WeChat-Files-Organize-Portable-0.2.0.exe')"
if (-not $SkipInstaller) {
    Write-Host "Installer: $(Join-Path $projectRoot 'release\WeChat-Files-Organize-Setup-0.2.0.exe')"
}

