$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $projectRoot "tools\adb"
$archivePath = Join-Path $env:TEMP "platform-tools-latest-windows.zip"

New-Item -ItemType Directory -Force -Path $toolsRoot | Out-Null

Write-Host "Downloading Android Platform Tools..."
Invoke-WebRequest `
    -Uri "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" `
    -OutFile $archivePath

Write-Host "Extracting to $toolsRoot"
Expand-Archive -LiteralPath $archivePath -DestinationPath $toolsRoot -Force

$adbPath = Join-Path $toolsRoot "platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adbPath)) {
    throw "ADB executable was not found after extraction."
}

Write-Host "ADB ready: $adbPath"
& $adbPath version

