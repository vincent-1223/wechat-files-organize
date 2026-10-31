from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from wechat_media_exporter.adb import AdbClient, find_adb
from wechat_media_exporter.media_types import detect_media_header


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    report_path = max((root / "reports").glob("scan-*.json"), key=lambda path: path.stat().st_mtime)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    serial = payload["device"]["serial"]
    adb_path = find_adb(root)
    if adb_path is None:
        raise SystemExit("ADB 未准备好。")
    adb = AdbClient(adb_path)

    counts: Counter[str] = Counter()
    media: list[tuple[str, str]] = []
    for item in payload["items"]:
        if item["kind"] != "other":
            continue
        result = adb.exec_out(
            serial,
            ["head", "-c", "16", item["remote_path"]],
            timeout=20,
        )
        kind = detect_media_header(result.stdout) if result.returncode == 0 else "unreadable"
        counts[kind] += 1
        if kind != "other":
            media.append((kind, item["remote_path"]))

    print(dict(counts))
    for kind, path in media[:30]:
        print(f"{kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
