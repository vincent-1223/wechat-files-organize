from __future__ import annotations

import argparse
import shlex
import tempfile
from pathlib import Path

from wechat_media_exporter.adb import AdbClient, find_adb
from wechat_media_exporter.database import HashIndex
from wechat_media_exporter.exporter import export_android_media, file_sha256
from wechat_media_exporter.scanner import scan_android


def main() -> int:
    parser = argparse.ArgumentParser(description="导出并校验一个真实手机媒体或文件")
    parser.add_argument(
        "--kind",
        choices=("image", "video", "file"),
        default="image",
    )
    arguments = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    adb_path = find_adb(project_root)
    if adb_path is None:
        raise SystemExit("未找到 ADB。")

    adb = AdbClient(adb_path)
    report = scan_android(adb)
    if report.device is None:
        raise SystemExit("未发现设备。")
    candidates = {
        "image": [item for item in report.images if item.size_bytes > 0],
        "video": [item for item in report.videos if item.size_bytes > 0],
        "file": [item for item in report.file_items if item.size_bytes > 0],
    }[arguments.kind]
    if not candidates:
        raise SystemExit(f"没有可用于测试导出的 {arguments.kind} 文件。")

    item = min(candidates, key=lambda candidate: candidate.size_bytes)
    item.selected = True
    destination = project_root / "WeChatBackup" / f"SmokeTest-{arguments.kind}"
    with tempfile.TemporaryDirectory(prefix="wechat-export-test-") as temp_root:
        with HashIndex(Path(temp_root) / "index.sqlite3") as index:
            result = export_android_media(
                adb,
                report.device.serial,
                [item],
                destination,
                index,
            )

    if result.failed or len(result.exported) != 1:
        raise SystemExit(f"导出失败：{result.failed}")

    local_file = result.exported[0]
    local_checksum = file_sha256(local_file)
    remote_result = adb.shell(
        report.device.serial,
        f"sha256sum {shlex.quote(item.remote_path)}",
        timeout=60,
    )
    remote_checksum = remote_result.stdout.strip().split()[0]
    print(f"remote={item.remote_path}")
    print(f"local={local_file}")
    print(f"local_sha256={local_checksum}")
    print(f"remote_sha256={remote_checksum}")
    if local_checksum != remote_checksum:
        raise SystemExit("SHA-256 不一致")
    print("SHA-256 verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
