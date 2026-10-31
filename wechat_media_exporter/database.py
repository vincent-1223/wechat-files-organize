from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(slots=True, frozen=True)
class HashRecord:
    checksum: str
    size_bytes: int
    first_path: str
    first_seen_at: str


class HashIndex:
    """Persistent exact-content index used to avoid duplicate exports."""

    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_hashes (
                checksum TEXT PRIMARY KEY,
                size_bytes INTEGER NOT NULL,
                first_path TEXT NOT NULL,
                first_seen_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def get(self, checksum: str) -> HashRecord | None:
        row = self._connection.execute(
            """
            SELECT checksum, size_bytes, first_path, first_seen_at
            FROM content_hashes
            WHERE checksum = ?
            """,
            (checksum,),
        ).fetchone()
        return HashRecord(*row) if row else None

    def add(self, checksum: str, size_bytes: int, first_path: Path) -> None:
        self._connection.execute(
            """
            INSERT OR IGNORE INTO content_hashes
                (checksum, size_bytes, first_path, first_seen_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                checksum,
                size_bytes,
                str(first_path),
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> HashIndex:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
