"""Spool SQLite durable pour le buffer industriel read-only.

Le stockage conserve le payload brut avant conversion SI avec une séquence
locale monotone et une clé d'idempotence unique. WAL + synchronous=FULL sont
activés pour privilégier la durabilité locale. Ce composant n'ouvre aucune
connexion OT et n'écrit vers aucun automate/historian.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from hydro_api.industrial.buffer_checkpoint import BufferedIndustrialRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS spool_records (
    local_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload BLOB NOT NULL,
    payload_sha256 TEXT NOT NULL,
    source_timestamp TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class StoredSpoolRecord:
    """Payload brut durable et ses métadonnées de reprise."""

    local_sequence: int
    idempotency_key: str
    payload: bytes
    payload_sha256: str
    source_timestamp: datetime
    source_ref: str
    created_at: datetime

    def to_buffered_record(self) -> BufferedIndustrialRecord:
        return BufferedIndustrialRecord(
            local_sequence=self.local_sequence,
            idempotency_key=self.idempotency_key,
            payload_sha256=self.payload_sha256,
            source_timestamp=self.source_timestamp,
            source_ref=self.source_ref,
        )


class SQLiteIndustrialSpool:
    """Adaptateur local synchrone avec transactions courtes et explicites."""

    def __init__(self, path: Path) -> None:
        if str(path).strip() == "":
            raise ValueError("Le chemin du spool SQLite est obligatoire.")
        self._path = path
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute(_SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SQLiteIndustrialSpool:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    @property
    def journal_mode(self) -> str:
        row = self._connection.execute("PRAGMA journal_mode").fetchone()
        if row is None:
            raise RuntimeError("SQLite n'a pas retourné le mode de journalisation.")
        return str(row[0]).lower()

    @property
    def synchronous_level(self) -> int:
        row = self._connection.execute("PRAGMA synchronous").fetchone()
        if row is None:
            raise RuntimeError("SQLite n'a pas retourné le niveau synchronous.")
        return int(row[0])

    def append(
        self,
        *,
        idempotency_key: str,
        payload: bytes,
        source_timestamp: datetime,
        source_ref: str,
    ) -> StoredSpoolRecord:
        """Ajoute un payload ou retourne le replay strictement identique existant."""

        if not idempotency_key.strip():
            raise ValueError("La clé d'idempotence du spool est obligatoire.")
        if not payload:
            raise ValueError("Le payload brut du spool ne peut pas être vide.")
        if source_timestamp.tzinfo is None:
            raise ValueError("Le SourceTimestamp du spool doit être timezone-aware.")
        if not source_ref.strip():
            raise ValueError("La provenance du payload spoolé est obligatoire.")

        digest = hashlib.sha256(payload).hexdigest()
        source_utc = source_timestamp.astimezone(UTC)
        existing = self._connection.execute(
            "SELECT * FROM spool_records WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            stored = self._row_to_record(existing)
            if stored.payload_sha256 != digest or stored.payload != payload:
                raise ValueError("Une clé d'idempotence du spool référence un payload différent.")
            return stored

        created_at = datetime.now(UTC)
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO spool_records (
                    idempotency_key, payload, payload_sha256,
                    source_timestamp, source_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    idempotency_key,
                    payload,
                    digest,
                    source_utc.isoformat(),
                    source_ref,
                    created_at.isoformat(),
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite n'a pas retourné la séquence du payload inséré.")
            local_sequence = int(cursor.lastrowid)
        return StoredSpoolRecord(
            local_sequence=local_sequence,
            idempotency_key=idempotency_key,
            payload=payload,
            payload_sha256=digest,
            source_timestamp=source_utc,
            source_ref=source_ref,
            created_at=created_at,
        )

    def list_after(
        self,
        local_sequence: int,
        *,
        limit: int = 1_000,
    ) -> tuple[StoredSpoolRecord, ...]:
        """Lit un suffixe ordonné sans supprimer les données acquittées."""

        if local_sequence < 0:
            raise ValueError("La séquence de reprise doit être positive ou nulle.")
        if limit <= 0:
            raise ValueError("La limite de lecture doit être strictement positive.")
        rows = self._connection.execute(
            """
            SELECT * FROM spool_records
            WHERE local_sequence > ?
            ORDER BY local_sequence ASC
            LIMIT ?
            """,
            (local_sequence, limit),
        ).fetchall()
        return tuple(self._row_to_record(row) for row in rows)

    def compact_through(self, local_sequence: int) -> int:
        """Supprime uniquement un préfixe explicitement acquitté par le consommateur."""

        if local_sequence < 0:
            raise ValueError("La séquence de compaction doit être positive ou nulle.")
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM spool_records WHERE local_sequence <= ?",
                (local_sequence,),
            )
        return int(cursor.rowcount)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> StoredSpoolRecord:
        return StoredSpoolRecord(
            local_sequence=int(row["local_sequence"]),
            idempotency_key=str(row["idempotency_key"]),
            payload=bytes(row["payload"]),
            payload_sha256=str(row["payload_sha256"]),
            source_timestamp=datetime.fromisoformat(str(row["source_timestamp"])),
            source_ref=str(row["source_ref"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )


__all__ = ["SQLiteIndustrialSpool", "StoredSpoolRecord"]
