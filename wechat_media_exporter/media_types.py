from __future__ import annotations

from pathlib import Path

from wechat_media_exporter.models import MediaKind

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".heic",
    ".heif",
    ".bmp",
    ".avif",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".3gp",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".rtf",
    ".csv",
    ".md",
    ".odt",
    ".ods",
    ".odp",
    ".epub",
    ".mobi",
}

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
}

AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".amr",
    ".ogg",
    ".flac",
    ".opus",
}

FILE_EXTENSIONS = {
    ".apk",
    ".exe",
    ".iso",
    ".bin",
}

INTERNAL_FILE_PATH_MARKERS = {
    "/xlog/",
    "/wxanewfiles/",
    "/package/",
    "/crash/",
    "/fts/",
    "/recbiz/",
    "/selectrecord/",
    "/multitask/",
    "/taskbar/",
}

THUMBNAIL_HINTS = ("thumb", "thumbnail", "sns_", "/emoji/", "/sticker/")


def classify_media_path(path: str) -> tuple[MediaKind, str]:
    suffix = Path(path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image", suffix
    if suffix in VIDEO_EXTENSIONS:
        return "video", suffix
    normalized = path.replace("\\", "/").lower()
    if any(marker in normalized for marker in INTERNAL_FILE_PATH_MARKERS):
        return "other", suffix
    if suffix in DOCUMENT_EXTENSIONS:
        return "document", suffix
    if suffix in ARCHIVE_EXTENSIONS:
        return "archive", suffix
    if suffix in AUDIO_EXTENSIONS:
        return "audio", suffix
    if suffix in FILE_EXTENSIONS:
        return "file", suffix
    if not suffix and Path(normalized).name.startswith(("thumb_", "img_", "image_")):
        return "image", ""
    return "other", suffix


def detect_media_kind(path: Path) -> MediaKind:
    try:
        header = path.read_bytes()[:16]
    except OSError:
        return "other"
    return detect_media_header(header)


def detect_media_header(header: bytes) -> MediaKind:
    if header.startswith(b"\xff\xd8\xff"):
        return "image"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image"
    if header.startswith((b"GIF87a", b"GIF89a", b"BM")):
        return "image"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image"
    if header.startswith(b"%PDF"):
        return "document"
    if header.startswith(b"PK\x03\x04"):
        return "archive"
    if header.startswith((b"ID3", b"fLaC", b"OggS")):
        return "audio"
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "audio"
    if header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in {b"heic", b"heix", b"mif1", b"msf1"}:
            return "image"
        if brand in {b"M4A ", b"M4B "}:
            return "audio"
        return "video"
    if header.startswith(b"\x1aE\xdf\xa3"):
        return "video"
    if header.startswith(b"RIFF") and header[8:12] == b"AVI ":
        return "video"
    return "other"


def looks_like_thumbnail(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    name = Path(normalized).name
    return name.startswith("th_") or any(hint in normalized for hint in THUMBNAIL_HINTS)


def safe_export_name(name: str, fallback: str) -> str:
    candidate = Path(name.replace("\\", "/")).name.strip()
    candidate = "".join(
        character if character.isprintable() and character not in '<>:"/\\|?*' else "_"
        for character in candidate
    )
    return candidate or fallback


def unique_destination(directory: Path, filename: str) -> Path:
    destination = directory / filename
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    counter = 2
    while True:
        candidate = directory / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
