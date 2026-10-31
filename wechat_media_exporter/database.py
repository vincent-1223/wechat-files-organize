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


@dataclass(slots=True, frozen=True)
class VerifiedExport:
    remote_path: str
    serial: str
    checksum: str
    local_path: str
    size_bytes: int
    exported_at: str


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
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS verified_exports (
                remote_path TEXT PRIMARY KEY,
                serial TEXT NOT NULL,
                checksum TEXT NOT NULL,
                local_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                exported_at TEXT NOT NULL
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

    def record_verified_export(
        self,
        *,
        remote_path: str,
        serial: str,
        checksum: str,
        local_path: Path,
        size_bytes: int,
    ) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO verified_exports
                (remote_path, serial, checksum, local_path, size_bytes, exported_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                remote_path,
                serial,
                checksum,
                str(local_path),
                size_bytes,
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()

    def list_verified_exports(self, serial: str | None = None) -> list[VerifiedExport]:
        if serial:
            rows = self._connection.execute(
                """
                SELECT remote_path, serial, checksum, local_path, size_bytes, exported_at
                FROM verified_exports
                WHERE serial = ?
                ORDER BY exported_at DESC
                """,
                (serial,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT remote_path, serial, checksum, local_path, size_bytes, exported_at
                FROM verified_exports
                ORDER BY exported_at DESC
                """
            ).fetchall()
        return [VerifiedExport(*row) for row in rows]

    def remove_verified_exports(self, remote_paths: list[str]) -> None:
        if not remote_paths:
            return
        placeholders = ",".join("?" for _ in remote_paths)
        self._connection.execute(
            f"DELETE FROM verified_exports WHERE remote_path IN ({placeholders})",
            remote_paths,
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> HashIndex:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
