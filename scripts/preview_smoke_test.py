from __future__ import annotations

from pathlib import Path

from wechat_media_exporter.adb import AdbClient, find_adb
from wechat_media_exporter.preview import MediaPreviewCache
from wechat_media_exporter.scanner import scan_android


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    adb_path = find_adb(root)
    if adb_path is None:
        raise SystemExit("ADB 未准备好。")

    adb = AdbClient(adb_path)
    report = scan_android(adb)
    if report.device is None:
        raise SystemExit("未发现设备。")
    cache = MediaPreviewCache(root / "reports" / "preview-smoke", adb, report.device.serial)

    for kind in ("image", "video"):
        candidates = [
            item for item in report.media_items if item.kind == kind and item.size_bytes > 0
        ]
        for item in sorted(candidates, key=lambda candidate: candidate.size_bytes):
            try:
                thumbnail = cache.ensure_thumbnail(item)
            except RuntimeError:
                continue
            print(f"{kind}: {item.name} -> {thumbnail}")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
