from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from wechat_media_exporter.adb import AdbClient
from wechat_media_exporter.database import HashIndex
from wechat_media_exporter.media_types import (
    detect_media_kind,
    safe_export_name,
    unique_destination,
)
from wechat_media_exporter.models import ExportProgress, ExportResult, MediaItem

ExportProgressCallback = Callable[[ExportProgress], None]


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def export_android_media(
    adb: AdbClient,
    serial: str,
    items: Sequence[MediaItem],
    destination: Path,
    hash_index: HashIndex,
    *,
    progress: ExportProgressCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> ExportResult:
    selected = [item for item in items if item.selected]
    result = ExportResult()
    total_bytes = sum(item.size_bytes for item in selected)
    bytes_done = 0
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="wechat-files-organize-") as temp_root:
        temp_directory = Path(temp_root)
        for index, item in enumerate(selected):
            if should_cancel and should_cancel():
                break

            temp_file = temp_directory / f"{index:08d}.part"
            try:
                adb.pull(serial, item.remote_path, temp_file)
                checksum = file_sha256(temp_file)
                known = hash_index.get(checksum)
                if known:
                    result.duplicates.append(Path(known.first_path))
                    item.checksum = checksum
                    item.duplicate_of = known.first_path
                    hash_index.record_verified_export(
                        remote_path=item.remote_path,
                        serial=serial,
                        checksum=checksum,
                        local_path=Path(known.first_path),
                        size_bytes=item.size_bytes,
                    )
                    temp_file.unlink(missing_ok=True)
                else:
                    detected_kind = detect_media_kind(temp_file)
                    if item.kind in {"other", "image", "video"} and detected_kind != "other":
                        item.kind = detected_kind
                    folder_name = {
                        "image": "Images",
                        "video": "Videos",
                        "document": "Documents",
                        "archive": "Archives",
                        "audio": "Audio",
                        "file": "Files",
                        "other": "Other",
                    }[item.kind]
                    target_directory = (
                        destination
                        / item.modified_at.strftime("%Y")
                        / item.modified_at.strftime("%m")
                        / folder_name
                    )
                    target_directory.mkdir(parents=True, exist_ok=True)
                    filename = safe_export_name(item.name, f"media-{index:06d}{item.extension}")
                    target_path = unique_destination(target_directory, filename)
                    shutil.move(temp_file, target_path)
                    hash_index.add(checksum, item.size_bytes, target_path)
                    hash_index.record_verified_export(
                        remote_path=item.remote_path,
                        serial=serial,
                        checksum=checksum,
                        local_path=target_path,
                        size_bytes=item.size_bytes,
                    )
                    item.checksum = checksum
                    item.local_path = target_path
                    result.exported.append(target_path)
            except Exception as exc:
                result.failed.append((item, str(exc)))

            bytes_done += item.size_bytes
            elapsed = max(time.perf_counter() - started, 0.001)
            if progress:
                progress(
                    ExportProgress(
                        completed=index + 1,
                        total=len(selected),
                        current_name=item.name,
                        bytes_done=bytes_done,
                        bytes_total=total_bytes,
                        bytes_per_second=bytes_done / elapsed,
                    )
                )

    reports_directory = destination / "Reports"
    reports_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).astimezone().strftime("%Y%m%d-%H%M%S")
    report_path = reports_directory / f"export-{timestamp}.json"
    report_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).astimezone().isoformat(),
                "device_serial": serial,
                "selected": len(selected),
                "exported": [str(path) for path in result.exported],
                "duplicates": [str(path) for path in result.duplicates],
                "failed": [
                    {"path": item.remote_path, "name": item.name, "error": message}
                    for item, message in result.failed
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return result
