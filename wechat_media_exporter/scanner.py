from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime

from wechat_media_exporter.adb import AdbClient, AdbError
from wechat_media_exporter.media_types import classify_media_path, looks_like_thumbnail
from wechat_media_exporter.models import MediaItem, ScanReport, SourceStatus

scan_paths = (
    "/sdcard/Pictures/Weixin",
    "/sdcard/Pictures/WeChat",
    "/sdcard/DCIM/WeChat",
    "/sdcard/DCIM/Weixin",
    "/sdcard/tencent/MicroMsg",
    "/sdcard/Android/media/com.tencent.mm",
    "/sdcard/Android/data/com.tencent.mm",
)


ProgressCallback = Callable[[int, str], None]


def parse_stat_line(line: str) -> tuple[int, datetime, str] | None:
    parts = line.split("\t", 2)
    if len(parts) != 3:
        return None

    size_text, timestamp_text, remote_path = parts
    try:
        size = int(size_text)
        timestamp = int(float(timestamp_text))
    except ValueError:
        return None

    if timestamp > 10_000_000_000:
        timestamp //= 1000
    return size, datetime.fromtimestamp(timestamp, tz=UTC).astimezone(), remote_path


def parse_find_line(line: str) -> tuple[int, datetime, str] | None:
    remote_path = line.strip()
    if not remote_path:
        return None
    return 0, datetime.now().astimezone(), remote_path


def scan_android(
    adb: AdbClient,
    *,
    progress: ProgressCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> ScanReport:
    started = time.perf_counter()
    device = adb.primary_device()
    device_info = adb.device_info(device.serial)
    report = ScanReport(device=device_info)
    mode = "unknown"
    items_by_path: dict[str, MediaItem] = {}

    for index, remote_root in enumerate(scan_paths):
        if should_cancel and should_cancel():
            report.warning = "扫描已取消"
            break

        if progress:
            progress(round(index / len(scan_paths) * 100), f"正在探测 {remote_root}")

        if not adb.directory_exists(device.serial, remote_root):
            report.sources.append(SourceStatus(remote_root, "missing", "目录不存在"))
            continue
        if not adb.directory_listable(device.serial, remote_root):
            report.sources.append(SourceStatus(remote_root, "denied", "当前 ADB 权限无法列出目录"))
            continue

        try:
            output, mode = adb.scan_path(device.serial, remote_root)
        except AdbError as exc:
            report.sources.append(SourceStatus(remote_root, "error", str(exc)))
            continue

        count = 0
        for line in output.splitlines():
            parsed = parse_stat_line(line) if mode == "stat" else parse_find_line(line)
            if parsed is None:
                continue
            size, modified_at, remote_path = parsed
            if remote_path in items_by_path:
                continue
            kind, extension = classify_media_path(remote_path)
            item = MediaItem(
                remote_path=remote_path,
                name=remote_path.rsplit("/", 1)[-1],
                kind=kind,
                size_bytes=size,
                modified_at=modified_at,
                source_root=remote_root,
                is_thumbnail=looks_like_thumbnail(remote_path),
                extension=extension,
            )
            items_by_path[remote_path] = item
            count += 1

        report.sources.append(
            SourceStatus(
                remote_root,
                "readable" if count else "empty",
                f"{mode} 扫描完成" if count else "目录可访问，但未发现文件",
                count,
            )
        )

    report.items = sorted(items_by_path.values(), key=lambda item: item.modified_at, reverse=True)
    report.elapsed_seconds = round(time.perf_counter() - started, 2)
    if progress:
        progress(100, "扫描完成")
    return report
