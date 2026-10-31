from __future__ import annotations

from datetime import datetime

from wechat_media_exporter.models import DeviceInfo, MediaItem, ScanReport, SourceStatus


def demo_report() -> ScanReport:
    device = DeviceInfo(
        serial="DEMO-DEVICE",
        model="Xiaomi 14",
        android_version="14",
        wechat_version="8.0.54",
    )
    sources = [
        SourceStatus(
            "/sdcard/Pictures/Weixin",
            "readable",
            "stat 扫描完成",
            742,
        ),
        SourceStatus(
            "/sdcard/Android/media/com.tencent.mm",
            "readable",
            "stat 扫描完成",
            118,
        ),
        SourceStatus(
            "/sdcard/tencent/MicroMsg",
            "readable",
            "部分缓存文件没有扩展名",
            1260,
        ),
        SourceStatus(
            "/sdcard/Android/data/com.tencent.mm",
            "denied",
            "当前 ADB 权限无法列出目录",
        ),
    ]

    raw_items = (
        (
            "IMG_20261028_164512.jpg",
            "image",
            4.8,
            datetime(2026, 10, 28, 16, 45, 12).astimezone(),
            "/sdcard/Pictures/Weixin/IMG_20261028_164512.jpg",
            "/sdcard/Pictures/Weixin",
            False,
            None,
        ),
        (
            "VID_20261023_102211.mp4",
            "video",
            54.2,
            datetime(2026, 10, 23, 10, 22, 11).astimezone(),
            "/sdcard/Android/media/com.tencent.mm/video/VID_20261023_102211.mp4",
            "/sdcard/Android/media/com.tencent.mm",
            False,
            18,
        ),
        (
            "mmexport1761047271.jpg",
            "image",
            2.1,
            datetime(2026, 10, 22, 18, 33, 50).astimezone(),
            "/sdcard/tencent/MicroMsg/a1/b2/mmexport1761047271.jpg",
            "/sdcard/tencent/MicroMsg",
            False,
            None,
        ),
        (
            "wx_camera_1760916532000.jpg",
            "image",
            3.4,
            datetime(2026, 10, 20, 14, 8, 52).astimezone(),
            "/sdcard/Pictures/Weixin/wx_camera_1760916532000.jpg",
            "/sdcard/Pictures/Weixin",
            False,
            None,
        ),
        (
            "draft_20261017_210332.webp",
            "image",
            1.2,
            datetime(2026, 10, 17, 21, 3, 32).astimezone(),
            "/sdcard/tencent/MicroMsg/cache/draft_20261017_210332.webp",
            "/sdcard/tencent/MicroMsg",
            False,
            None,
        ),
        (
            "VID_20261012_173912.mp4",
            "video",
            126.0,
            datetime(2026, 10, 12, 17, 39, 12).astimezone(),
            "/sdcard/Android/media/com.tencent.mm/video/VID_20261012_173912.mp4",
            "/sdcard/Android/media/com.tencent.mm",
            False,
            64,
        ),
        (
            "IMG_20260929_101544.jpg",
            "image",
            5.7,
            datetime(2026, 9, 29, 10, 15, 44).astimezone(),
            "/sdcard/Pictures/Weixin/IMG_20260929_101544.jpg",
            "/sdcard/Pictures/Weixin",
            False,
            None,
        ),
        (
            "wx_video_1760128318.mp4",
            "video",
            88.3,
            datetime(2026, 9, 22, 8, 41, 58).astimezone(),
            "/sdcard/Android/media/com.tencent.mm/video/wx_video_1760128318.mp4",
            "/sdcard/Android/media/com.tencent.mm",
            False,
            46,
        ),
        (
            "mmexport1759321004.jpg",
            "image",
            3.8,
            datetime(2026, 9, 18, 20, 12, 4).astimezone(),
            "/sdcard/tencent/MicroMsg/a3/c4/mmexport1759321004.jpg",
            "/sdcard/tencent/MicroMsg",
            False,
            None,
        ),
    )

    items: list[MediaItem] = []
    for (
        name,
        kind,
        size_mb,
        modified_at,
        remote_path,
        source_root,
        is_thumbnail,
        duration_seconds,
    ) in raw_items:
        items.append(
            MediaItem(
                remote_path=remote_path,
                name=name,
                kind=kind,  # type: ignore[arg-type]
                size_bytes=int(size_mb * 1024 * 1024),
                modified_at=modified_at,
                source_root=source_root,
                is_thumbnail=is_thumbnail,
                extension=name[name.rfind(".") :].lower(),
                duration_seconds=duration_seconds,  # type: ignore[arg-type]
                selected=name
                in {
                    "IMG_20261028_164512.jpg",
                    "VID_20261023_102211.mp4",
                    "mmexport1761047271.jpg",
                },
                duplicate_of=(
                    "DEMO-DUPLICATE"
                    if name in {"mmexport1761047271.jpg", "mmexport1759321004.jpg"}
                    else None
                ),
            )
        )

    return ScanReport(
        device=device,
        items=items,
        sources=sources,
        elapsed_seconds=28.4,
        warning="当前为界面演示数据，不代表真实手机扫描结果。",
    )
