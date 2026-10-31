from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from wechat_media_exporter.adb import AdbClient, AdbError, find_adb
from wechat_media_exporter.database import HashIndex, VerifiedExport
from wechat_media_exporter.exporter import export_android_media, file_sha256
from wechat_media_exporter.models import MediaItem, ScanReport
from wechat_media_exporter.preview import MediaPreviewCache
from wechat_media_exporter.scanner import scan_android


class ScanWorker(QThread):
    progress = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, project_root: Path, parent=None):  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.project_root = project_root
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        try:
            adb_path = find_adb(self.project_root)
            if adb_path is None:
                raise AdbError(
                    "未找到 ADB。请运行 scripts/fetch-adb.ps1，"
                    "或把 Android Platform Tools 放到 tools/adb。"
                )
            report: ScanReport = scan_android(
                AdbClient(adb_path),
                progress=self.progress.emit,
                should_cancel=self._cancel_event.is_set,
            )
            self.succeeded.emit(report)
        except Exception as exc:
            self.failed.emit(str(exc))


class ExportWorker(QThread):
    progress = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        project_root: Path,
        serial: str,
        items: list[MediaItem],
        destination: Path,
        database_path: Path,
        parent=None,  # type: ignore[no-untyped-def]
    ):
        super().__init__(parent)
        self.project_root = project_root
        self.serial = serial
        self.items = items
        self.destination = destination
        self.database_path = database_path
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        try:
            adb_path = find_adb(self.project_root)
            if adb_path is None:
                raise AdbError("未找到 ADB，无法导出手机文件。")
            with HashIndex(self.database_path) as hash_index:
                result = export_android_media(
                    AdbClient(adb_path),
                    self.serial,
                    self.items,
                    self.destination,
                    hash_index,
                    progress=self.progress.emit,
                    should_cancel=self._cancel_event.is_set,
                )
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ThumbnailWorker(QThread):
    preview_ready = Signal(str, str)
    progress = Signal(int, int, str)
    note = Signal(str)

    def __init__(
        self,
        cache: MediaPreviewCache,
        items: list[MediaItem],
        parent=None,  # type: ignore[no-untyped-def]
    ):
        super().__init__(parent)
        self.cache = cache
        self.items = items
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        failures = 0
        for index, item in enumerate(self.items, start=1):
            if self._cancel_event.is_set():
                break
            try:
                path = self.cache.ensure_thumbnail(item)
                self.preview_ready.emit(item.remote_path, str(path))
            except Exception:
                failures += 1
            self.progress.emit(index, len(self.items), item.name)
        if failures:
            self.note.emit(f"{failures} 个媒体未能生成缩略图，可双击打开检查。")


class OpenMediaWorker(QThread):
    succeeded = Signal(str, str)
    failed = Signal(str)

    def __init__(
        self,
        cache: MediaPreviewCache,
        item: MediaItem,
        parent=None,  # type: ignore[no-untyped-def]
    ):
        super().__init__(parent)
        self.cache = cache
        self.item = item

    def run(self) -> None:
        try:
            path = self.cache.download_full(self.item)
            self.succeeded.emit(self.item.remote_path, str(path))
        except Exception as exc:
            self.failed.emit(str(exc))


class CleanupWorker(QThread):
    succeeded = Signal(int)
    failed = Signal(str)

    def __init__(
        self,
        project_root: Path,
        serial: str,
        records: list[VerifiedExport],
        database_path: Path,
        parent=None,  # type: ignore[no-untyped-def]
    ):
        super().__init__(parent)
        self.project_root = project_root
        self.serial = serial
        self.records = records
        self.database_path = database_path

    def run(self) -> None:
        try:
            adb_path = find_adb(self.project_root)
            if adb_path is None:
                raise AdbError("未找到 ADB，无法清理手机文件。")

            verified_paths: list[str] = []
            for record in self.records:
                local_path = Path(record.local_path)
                if not local_path.is_file():
                    raise AdbError(f"本地备份不存在，禁止清理：{local_path}")
                if file_sha256(local_path) != record.checksum:
                    raise AdbError(f"本地备份校验失败，禁止清理：{local_path}")
                verified_paths.append(record.remote_path)

            AdbClient(adb_path).remove_many(self.serial, verified_paths)
            with HashIndex(self.database_path) as index:
                index.remove_verified_exports(verified_paths)
            self.succeeded.emit(len(verified_paths))
        except Exception as exc:
            self.failed.emit(str(exc))
