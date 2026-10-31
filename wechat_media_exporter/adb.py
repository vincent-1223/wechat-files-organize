from __future__ import annotations

import os
import re
import shlex
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from wechat_media_exporter.models import DeviceInfo


class AdbError(RuntimeError):
    """Raised when ADB is unavailable or a command fails."""


@dataclass(slots=True, frozen=True)
class AdbDevice:
    serial: str
    state: str
    model_hint: str = ""


def find_adb(project_root: Path | None = None) -> Path | None:
    env_override = os.environ.get("WECHAT_FILES_ORGANIZE_ADB")
    if env_override:
        candidate = Path(env_override)
        if candidate.is_file():
            return candidate

    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    candidates = (
        project_root / "tools" / "adb" / "platform-tools" / "adb.exe",
        project_root / "tools" / "adb" / "adb.exe",
        project_root / "adb.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        for filename in ("adb.exe", "adb"):
            candidate = Path(directory) / filename
            if candidate.is_file():
                return candidate
    return None


class AdbClient:
    def __init__(self, executable: Path):
        self.executable = executable

    def _run(
        self,
        arguments: Iterable[str],
        *,
        timeout: int = 30,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        creation_flags = 0
        if os.name == "nt":
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                [str(self.executable), *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=creation_flags,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise AdbError(f"无法运行 ADB：{exc}") from exc

        if check and result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "ADB 命令执行失败"
            raise AdbError(message)
        return result

    def version(self) -> str:
        result = self._run(["version"], timeout=10, check=False)
        first_line = (result.stdout or result.stderr).splitlines()
        return first_line[0].strip() if first_line else ""

    def list_devices(self) -> list[AdbDevice]:
        result = self._run(["devices", "-l"], timeout=15)
        devices: list[AdbDevice] = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("List of devices attached"):
                continue
            parts = stripped.split()
            if len(parts) < 2:
                continue
            model = ""
            for part in parts[2:]:
                if part.startswith("model:"):
                    model = part.removeprefix("model:").replace("_", " ")
                    break
            devices.append(AdbDevice(serial=parts[0], state=parts[1], model_hint=model))
        return devices

    def primary_device(self) -> AdbDevice:
        devices = self.list_devices()
        ready = [device for device in devices if device.state == "device"]
        if not ready:
            if not devices:
                raise AdbError("未检测到 Android 手机。请连接 USB 并开启 USB 调试。")
            first = devices[0]
            if first.state == "unauthorized":
                raise AdbError("手机尚未授权这台电脑。请在手机上确认 USB 调试授权。")
            if first.state == "offline":
                raise AdbError("手机处于离线状态。请重新连接 USB 或重新授权调试。")
            raise AdbError(f"设备状态不可用：{first.state}")
        return ready[0]

    def shell(
        self,
        serial: str,
        command: str,
        *,
        timeout: int = 60,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return self._run(["-s", serial, "shell", command], timeout=timeout, check=check)

    def exec_out(
        self,
        serial: str,
        command_arguments: list[str],
        *,
        timeout: int = 90,
    ) -> subprocess.CompletedProcess[bytes]:
        creation_flags = 0
        if os.name == "nt":
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.run(
            [str(self.executable), "-s", serial, "exec-out", *command_arguments],
            capture_output=True,
            timeout=timeout,
            check=False,
            creationflags=creation_flags,
        )

    def device_info(self, serial: str) -> DeviceInfo:
        model = self._shell_value(serial, "getprop ro.product.model")
        android_version = self._shell_value(serial, "getprop ro.build.version.release")
        wechat_version = self._wechat_version(serial)
        return DeviceInfo(
            serial=serial,
            model=model or "Android Device",
            android_version=android_version or "未知",
            wechat_version=wechat_version,
        )

    def _shell_value(self, serial: str, command: str) -> str:
        result = self.shell(serial, command, timeout=15)
        return result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""

    def _wechat_version(self, serial: str) -> str:
        result = self.shell(
            serial,
            "dumpsys package com.tencent.mm | grep -m1 versionName",
            timeout=20,
        )
        match = re.search(r"versionName=([^\s]+)", result.stdout)
        return match.group(1) if match else "未检测到"

    def directory_exists(self, serial: str, remote_path: str) -> bool:
        result = self.shell(serial, f"test -d {shlex.quote(remote_path)}", timeout=12)
        return result.returncode == 0

    def directory_listable(self, serial: str, remote_path: str) -> bool:
        result = self.shell(serial, f"ls -la {shlex.quote(remote_path)}", timeout=20)
        return result.returncode == 0

    def directory_access(self, serial: str, remote_path: str) -> tuple[str, str]:
        result = self.shell(serial, f"ls -la {shlex.quote(remote_path)}", timeout=20)
        if result.returncode == 0:
            return "readable", ""
        message = f"{result.stderr}\n{result.stdout}".strip()
        lowered = message.lower()
        if "permission denied" in lowered or "denied" in lowered:
            return "denied", "当前 ADB 权限无法列出目录"
        if "no such file" in lowered or "not found" in lowered:
            return "missing", "目录不存在"
        return "error", message or "目录读取失败"

    def canonical_path(self, serial: str, remote_path: str) -> str:
        result = self.shell(serial, f"realpath {shlex.quote(remote_path)}", timeout=12)
        canonical = result.stdout.strip()
        return canonical or remote_path

    def scan_path(self, serial: str, remote_path: str) -> tuple[str, str, str]:
        quoted = shlex.quote(remote_path)
        stat_command = f"find {quoted} -type f -exec stat -c '%s|%Y|%n' {{}} +"
        result = self.shell(serial, stat_command, timeout=180)
        output = result.stdout.strip("\r\n")
        if output:
            return output, "stat", result.stderr.strip()

        fallback = self.shell(
            serial,
            f"find {quoted} -type f",
            timeout=180,
        )
        return fallback.stdout.strip("\r\n"), "find", fallback.stderr.strip()

    def discover_wechat_directories(self, serial: str) -> list[str]:
        parents = (
            "/sdcard/Pictures",
            "/sdcard/DCIM",
            "/sdcard/tencent",
            "/sdcard/Android/media",
        )
        discovered: list[str] = []
        for parent in parents:
            command = (
                f"find {shlex.quote(parent)} -maxdepth 2 -type d "
                "\\( -iname '*weixin*' -o -iname '*wechat*' \\) 2>/dev/null"
            )
            result = self.shell(serial, command, timeout=30)
            for line in result.stdout.splitlines():
                path = line.strip()
                if path and path not in discovered:
                    discovered.append(path)
        return discovered

    def pull(self, serial: str, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            ["-s", serial, "pull", remote_path, str(local_path)],
            timeout=1800,
            check=True,
        )
        if not local_path.is_file():
            raise AdbError(f"文件未成功传输：{remote_path}")

    def remove_many(self, serial: str, remote_paths: list[str]) -> subprocess.CompletedProcess[str]:
        if not remote_paths:
            raise AdbError("没有待清理文件")
        command = "rm -f -- " + " ".join(shlex.quote(path) for path in remote_paths)
        return self.shell(serial, command, timeout=180, check=True)
