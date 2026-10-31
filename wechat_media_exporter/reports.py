from __future__ import annotations

import json
from pathlib import Path

from wechat_media_exporter.models import ScanReport


def _timestamp_stem(report: ScanReport) -> str:
    return report.scanned_at.astimezone().strftime("%Y%m%d-%H%M%S")


def write_scan_reports(report: ScanReport, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"scan-{_timestamp_stem(report)}"
    json_path = directory / f"{stem}.json"
    markdown_path = directory / f"{stem}.md"

    device = report.device
    payload = {
        "scanned_at": report.scanned_at.astimezone().isoformat(),
        "elapsed_seconds": report.elapsed_seconds,
        "device": (
            {
                "serial": device.serial,
                "model": device.model,
                "android_version": device.android_version,
                "wechat_version": device.wechat_version,
            }
            if device
            else None
        ),
        "summary": {
            "images": len(report.images),
            "videos": len(report.videos),
            "other": len(report.unknown),
            "thumbnails": len(report.thumbnails),
            "total_bytes": report.total_bytes,
        },
        "sources": [
            {
                "path": source.path,
                "state": source.state,
                "message": source.message,
                "file_count": source.file_count,
            }
            for source in report.sources
        ],
        "items": [
            {
                "remote_path": item.remote_path,
                "name": item.name,
                "kind": item.kind,
                "size_bytes": item.size_bytes,
                "modified_at": item.modified_at.isoformat(),
                "source_root": item.source_root,
                "is_thumbnail": item.is_thumbnail,
            }
            for item in report.items
        ],
        "warning": report.warning,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# 微信媒体扫描报告",
        "",
        f"- 扫描时间：{report.scanned_at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 设备：{device.display_name if device else '未连接'}",
        f"- Android：{device.android_version if device else '—'}",
        f"- 微信：{device.wechat_version if device else '—'}",
        f"- 用时：{report.elapsed_seconds:.1f} 秒",
        "",
        "## 统计",
        "",
        f"- 图片：{len(report.images):,}",
        f"- 视频：{len(report.videos):,}",
        f"- 待识别：{len(report.unknown):,}",
        f"- 缩略图：{len(report.thumbnails):,}",
        f"- 总容量：{report.total_bytes:,} bytes",
        "",
        "## 目录状态",
        "",
        "| 目录 | 状态 | 文件数 | 说明 |",
        "|---|---:|---:|---|",
    ]
    for source in report.sources:
        lines.append(
            f"| `{source.path}` | {source.state_label} | {source.file_count:,} | {source.message} |"
        )
    if report.warning:
        lines.extend(["", "## 说明", "", report.warning])
    lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path
