from __future__ import annotations

from datetime import datetime
from pathlib import Path

from wechat_media_exporter.database import HashIndex
from wechat_media_exporter.exporter import export_android_media, file_sha256
from wechat_media_exporter.media_types import (
    classify_media_path,
    detect_media_kind,
    looks_like_thumbnail,
    safe_export_name,
    unique_destination,
)
from wechat_media_exporter.models import MediaItem
from wechat_media_exporter.scanner import parse_stat_line


class FakeAdb:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads

    def pull(self, _serial: str, remote_path: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(self.payloads[remote_path])


def media(remote_path: str, modified_at: datetime, selected: bool = True) -> MediaItem:
    name = Path(remote_path).name
    return MediaItem(
        remote_path=remote_path,
        name=name,
        kind="image" if name.endswith(".jpg") else "video",
        size_bytes=12,
        modified_at=modified_at,
        source_root="/sdcard/Pictures/Weixin",
        extension=Path(name).suffix,
        selected=selected,
    )


def test_media_type_and_thumbnail_rules() -> None:
    assert classify_media_path("/a/photo.JPG") == ("image", ".jpg")
    assert classify_media_path("/a/video.MP4") == ("video", ".mp4")
    assert classify_media_path("/a/cache_123") == ("other", "")
    assert classify_media_path("/a/textstatus/thumb_123") == ("image", "")
    assert looks_like_thumbnail("/sdcard/cache/th_123")
    assert looks_like_thumbnail("/sdcard/tencent/MicroMsg/emoji/a.png")
    assert not looks_like_thumbnail("/sdcard/Pictures/Weixin/IMG_001.jpg")
    assert safe_export_name('bad<>:"|?*.jpg', "fallback") == "bad_______.jpg"


def test_detect_media_kind_from_file_header(tmp_path: Path) -> None:
    jpeg = tmp_path / "without-extension"
    jpeg.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 16)
    assert detect_media_kind(jpeg) == "image"
    mp4 = tmp_path / "cache-file"
    mp4.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 8)
    assert detect_media_kind(mp4) == "video"


def test_parse_stat_line() -> None:
    parsed = parse_stat_line("1048576|1761705600|/sdcard/Pictures/Weixin/a.jpg")
    assert parsed is not None
    size, timestamp, path = parsed
    assert size == 1_048_576
    assert timestamp.year >= 2025
    assert path.endswith("a.jpg")
    assert parse_stat_line("invalid output") is None


def test_unique_destination(tmp_path: Path) -> None:
    original = tmp_path / "photo.jpg"
    original.write_bytes(b"one")
    assert unique_destination(tmp_path, "photo.jpg") == tmp_path / "photo (2).jpg"


def test_hash_index_persists(tmp_path: Path) -> None:
    database_path = tmp_path / "index.sqlite3"
    file_path = tmp_path / "photo.jpg"
    file_path.write_bytes(b"same-content")
    checksum = file_sha256(file_path)

    with HashIndex(database_path) as index:
        assert index.get(checksum) is None
        index.add(checksum, file_path.stat().st_size, file_path)

    with HashIndex(database_path) as index:
        record = index.get(checksum)
        assert record is not None
        assert record.first_path == str(file_path)


def test_export_groups_by_month_and_skips_exact_duplicates(tmp_path: Path) -> None:
    first = media(
        "/sdcard/Pictures/Weixin/a.jpg",
        datetime(2026, 10, 3, 12, 0).astimezone(),
    )
    second = media(
        "/sdcard/Pictures/Weixin/b.jpg",
        datetime(2026, 10, 4, 12, 0).astimezone(),
    )
    video = media(
        "/sdcard/Pictures/Weixin/c.mp4",
        datetime(2026, 9, 1, 12, 0).astimezone(),
    )
    payloads = {
        first.remote_path: b"same-content",
        second.remote_path: b"same-content",
        video.remote_path: b"video-content",
    }
    destination = tmp_path / "WeChatBackup"

    with HashIndex(tmp_path / "index.sqlite3") as index:
        result = export_android_media(
            FakeAdb(payloads),  # type: ignore[arg-type]
            "SERIAL",
            [first, second, video],
            destination,
            index,
        )

    assert len(result.exported) == 2
    assert len(result.duplicates) == 1
    assert (destination / "2026" / "10" / "Images" / "a.jpg").is_file()
    assert (destination / "2026" / "09" / "Videos" / "c.mp4").is_file()
    assert list((destination / "Reports").glob("export-*.json"))
    with HashIndex(tmp_path / "index.sqlite3") as index:
        verified = index.list_verified_exports("SERIAL")
        assert len(verified) == 3
        assert {Path(record.remote_path).name for record in verified} == {"a.jpg", "b.jpg", "c.mp4"}
