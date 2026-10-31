from __future__ import annotations

import hashlib
import io
import subprocess
import tempfile
from pathlib import Path

import av
from PIL import Image, ImageOps

from wechat_media_exporter.adb import AdbClient
from wechat_media_exporter.models import MediaItem


class MediaPreviewCache:
    def __init__(self, root: Path, adb: AdbClient, serial: str):
        self.root = root
        self.adb = adb
        self.serial = serial
        self.thumbnail_directory = root / "thumbnails"
        self.full_directory = root / "full"
        self.thumbnail_directory.mkdir(parents=True, exist_ok=True)
        self.full_directory.mkdir(parents=True, exist_ok=True)

    def _key(self, item: MediaItem) -> str:
        source = f"{item.remote_path}|{item.size_bytes}|{item.modified_at.isoformat()}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]

    def thumbnail_path(self, item: MediaItem) -> Path:
        return self.thumbnail_directory / f"{self._key(item)}.jpg"

    def full_path(self, item: MediaItem) -> Path:
        suffix = item.extension if item.extension else ".bin"
        return self.full_directory / f"{self._key(item)}{suffix}"

    def ensure_thumbnail(self, item: MediaItem) -> Path:
        target = self.thumbnail_path(item)
        if target.is_file() and target.stat().st_size > 0:
            return target

        temporary = target.with_suffix(".part.jpg")
        if item.kind == "image":
            image = self._read_image(item)
        else:
            image = self._read_video_frame(item)
        image.thumbnail((360, 360), Image.Resampling.LANCZOS)
        image.convert("RGB").save(temporary, "JPEG", quality=84)
        temporary.replace(target)
        return target

    def _read_image(self, item: MediaItem) -> Image.Image:
        result = subprocess.run(
            [
                str(self.adb.executable),
                "-s",
                self.serial,
                "exec-out",
                "cat",
                item.remote_path,
            ],
            capture_output=True,
            timeout=90,
            check=False,
        )
        if result.returncode != 0 or not result.stdout:
            message = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(message or "无法读取图片")
        with Image.open(io.BytesIO(result.stdout)) as image:
            return ImageOps.exif_transpose(image).copy()

    def _read_video_frame(self, item: MediaItem) -> Image.Image:
        with tempfile.TemporaryDirectory(prefix="wechat-preview-") as temporary_directory:
            video_path = Path(temporary_directory) / f"video{item.extension or '.mp4'}"
            self.adb.pull(self.serial, item.remote_path, video_path)
            with av.open(str(video_path)) as container:
                stream = container.streams.video[0]
                selected = None
                for index, frame in enumerate(container.decode(stream)):
                    selected = frame
                    if index >= 24 or (frame.time or 0) >= 1.0:
                        break
                if selected is None:
                    raise RuntimeError("视频中没有可解码的画面")
                return selected.to_image()

    def download_full(self, item: MediaItem) -> Path:
        target = self.full_path(item)
        if target.is_file() and target.stat().st_size == item.size_bytes:
            return target
        temporary = target.with_suffix(target.suffix + ".part")
        self.adb.pull(self.serial, item.remote_path, temporary)
        temporary.replace(target)
        return target
