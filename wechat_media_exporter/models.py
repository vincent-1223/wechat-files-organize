from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

MediaKind = Literal["image", "video", "other"]
SourceState = Literal["readable", "partial", "empty", "missing", "denied", "error"]


@dataclass(slots=True, frozen=True)
class DeviceInfo:
    serial: str
    model: str
    android_version: str
    wechat_version: str = "未检测到"

    @property
    def display_name(self) -> str:
        return self.model or self.serial


@dataclass(slots=True, frozen=True)
class SourceStatus:
    path: str
    state: SourceState
    message: str
    file_count: int = 0

    @property
    def state_label(self) -> str:
        return {
            "readable": "可读取",
            "partial": "部分可读",
            "empty": "目录为空",
            "missing": "不存在",
            "denied": "权限不足",
            "error": "读取失败",
        }[self.state]


@dataclass(slots=True)
class MediaItem:
    remote_path: str
    name: str
    kind: MediaKind
    size_bytes: int
    modified_at: datetime
    source_root: str
    is_thumbnail: bool = False
    extension: str = ""
    duration_seconds: int | None = None
    checksum: str | None = None
    local_path: Path | None = None
    duplicate_of: str | None = None
    selected: bool = False

    @property
    def month_key(self) -> str:
        return self.modified_at.strftime("%Y-%m")

    @property
    def month_label(self) -> str:
        value = self.modified_at
        return f"{value.year} 年 {value.month} 月"

    @property
    def kind_label(self) -> str:
        return {"image": "图片", "video": "视频", "other": "待识别"}[self.kind]

    @property
    def size_label(self) -> str:
        value = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{self.size_bytes} B"

    @property
    def day_label(self) -> str:
        return self.modified_at.strftime("%m 月 %d 日")


@dataclass(slots=True)
class ScanReport:
    device: DeviceInfo | None
    items: list[MediaItem] = field(default_factory=list)
    sources: list[SourceStatus] = field(default_factory=list)
    scanned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    elapsed_seconds: float = 0.0
    warning: str = ""

    @property
    def images(self) -> list[MediaItem]:
        return [item for item in self.items if item.kind == "image"]

    @property
    def videos(self) -> list[MediaItem]:
        return [item for item in self.items if item.kind == "video"]

    @property
    def unknown(self) -> list[MediaItem]:
        return [item for item in self.items if item.kind == "other"]

    @property
    def media_items(self) -> list[MediaItem]:
        return [item for item in self.items if item.kind in {"image", "video"}]

    @property
    def thumbnails(self) -> list[MediaItem]:
        return [item for item in self.items if item.is_thumbnail]

    @property
    def duplicates(self) -> list[MediaItem]:
        return [item for item in self.items if item.duplicate_of]

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.items)

    @property
    def media_bytes(self) -> int:
        return sum(item.size_bytes for item in self.media_items)

    @property
    def readable_sources(self) -> int:
        return sum(source.state in {"readable", "partial", "empty"} for source in self.sources)

    def months(self) -> list[tuple[str, str, list[MediaItem]]]:
        grouped: dict[str, list[MediaItem]] = {}
        for item in self.media_items:
            grouped.setdefault(item.month_key, []).append(item)

        result: list[tuple[str, str, list[MediaItem]]] = []
        for key in sorted(grouped, reverse=True):
            items = grouped[key]
            result.append((key, items[0].month_label, items))
        return result


@dataclass(slots=True, frozen=True)
class ExportProgress:
    completed: int
    total: int
    current_name: str
    bytes_done: int
    bytes_total: int
    bytes_per_second: float

    @property
    def percent(self) -> int:
        if self.total <= 0:
            return 0
        return round(self.completed / self.total * 100)

    @property
    def remaining_seconds(self) -> int | None:
        if self.bytes_per_second <= 0 or self.bytes_total <= self.bytes_done:
            return 0 if self.bytes_total <= self.bytes_done else None
        return round((self.bytes_total - self.bytes_done) / self.bytes_per_second)


@dataclass(slots=True)
class ExportResult:
    exported: list[Path] = field(default_factory=list)
    duplicates: list[Path] = field(default_factory=list)
    failed: list[tuple[MediaItem, str]] = field(default_factory=list)
