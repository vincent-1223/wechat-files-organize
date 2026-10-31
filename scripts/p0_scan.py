from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wechat_media_exporter.adb import AdbClient, find_adb
from wechat_media_exporter.reports import write_scan_reports
from wechat_media_exporter.scanner import scan_android


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="只读扫描 Android 手机微信媒体目录")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "reports",
        help="JSON 和 Markdown 报告输出目录",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    adb_path = find_adb(project_root)
    if adb_path is None:
        raise SystemExit("未找到 ADB。请先运行 scripts/fetch-adb.ps1。")

    report = scan_android(
        AdbClient(adb_path),
        progress=lambda value, message: print(f"[{value:3d}%] {message}", flush=True),
    )
    json_path, markdown_path = write_scan_reports(report, args.output)
    summary = {
        "device": (
            {
                "model": report.device.model,
                "android": report.device.android_version,
                "wechat": report.device.wechat_version,
            }
            if report.device
            else None
        ),
        "images": len(report.images),
        "videos": len(report.videos),
        "files": len(report.file_items),
        "other": len(report.unknown),
        "thumbnails": len(report.thumbnails),
        "total_bytes": report.total_bytes,
        "elapsed_seconds": report.elapsed_seconds,
        "json_report": str(json_path),
        "markdown_report": str(markdown_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
