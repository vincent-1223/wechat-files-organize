from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from wechat_media_exporter.adb import AdbClient, AdbError, find_adb
from wechat_media_exporter.database import HashIndex
from wechat_media_exporter.exporter import export_android_media
from wechat_media_exporter.models import MediaItem, ScanReport
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
