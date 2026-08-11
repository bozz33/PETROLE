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

from hydro_api.industrial.buffer_checkpoint import (
    BufferedIndustrialRecord,
    ConnectorCheckpoint,
)

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

CREATE TABLE IF NOT EXISTS spool_checkpoints (
    connector_ref TEXT NOT NULL,
    checkpoint_version TEXT NOT NULL,
    last_local_sequence INTEGER NOT NULL,
    last_idempotency_key TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (connector_ref, checkpoint_version),
    CHECK (last_local_sequence >= 0)
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
        self._connection.executescript(_SCHEMA)
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

    def load_checkpoint(
        self,
        *,
        connector_ref: str,
        checkpoint_version: str,
    ) -> ConnectorCheckpoint | None:
        """Relit le dernier checkpoint durable d'un connecteur/version."""

        if not connector_ref.strip() or not checkpoint_version.strip():
            raise ValueError("Le connecteur et la version de checkpoint sont obligatoires.")
        row = self._connection.execute(
            """
            SELECT connector_ref, checkpoint_version, last_local_sequence, last_idempotency_key
            FROM spool_checkpoints
            WHERE connector_ref = ? AND checkpoint_version = ?
            """,
            (connector_ref, checkpoint_version),
        ).fetchone()
        if row is None:
            return None
        last_key = row["last_idempotency_key"]
        return ConnectorCheckpoint(
            connector_ref=str(row["connector_ref"]),
            checkpoint_version=str(row["checkpoint_version"]),
            last_local_sequence=int(row["last_local_sequence"]),
            last_idempotency_key=str(last_key) if last_key is not None else None,
        )

    @staticmethod
    def _validate_checkpoint_progress(
        existing: ConnectorCheckpoint | None,
        checkpoint: ConnectorCheckpoint,
    ) -> None:
        if existing is None:
            return
        if checkpoint.last_local_sequence < existing.last_local_sequence:
            raise ValueError("Un checkpoint durable ne peut pas régresser.")
        if (
            checkpoint.last_local_sequence == existing.last_local_sequence
            and checkpoint.last_idempotency_key != existing.last_idempotency_key
        ):
            raise ValueError(
                "Une même séquence checkpoint ne peut pas changer de clé d'idempotence."
            )

    def _upsert_checkpoint(self, checkpoint: ConnectorCheckpoint) -> None:
        self._connection.execute(
            """
            INSERT INTO spool_checkpoints (
                connector_ref, checkpoint_version, last_local_sequence,
                last_idempotency_key, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(connector_ref, checkpoint_version) DO UPDATE SET
                last_local_sequence = excluded.last_local_sequence,
                last_idempotency_key = excluded.last_idempotency_key,
                updated_at = excluded.updated_at
            """,
            (
                checkpoint.connector_ref,
                checkpoint.checkpoint_version,
                checkpoint.last_local_sequence,
                checkpoint.last_idempotency_key,
                datetime.now(UTC).isoformat(),
            ),
        )

    def save_checkpoint(self, checkpoint: ConnectorCheckpoint) -> None:
        """Persiste un checkpoint sans autoriser de retour en arrière."""

        existing = self.load_checkpoint(
            connector_ref=checkpoint.connector_ref,
            checkpoint_version=checkpoint.checkpoint_version,
        )
        self._validate_checkpoint_progress(existing, checkpoint)
        with self._connection:
            self._upsert_checkpoint(checkpoint)

    def acknowledge_through(self, checkpoint: ConnectorCheckpoint) -> int:
        """Persiste le checkpoint puis compacte son préfixe dans une transaction unique.

        Pour une progression réelle, la séquence finale doit encore exister dans
        le spool et porter exactement la clé d'idempotence annoncée. Rejouer le
        même checkpoint après une compaction déjà réussie reste idempotent.
        """

        existing = self.load_checkpoint(
            connector_ref=checkpoint.connector_ref,
            checkpoint_version=checkpoint.checkpoint_version,
        )
        self._validate_checkpoint_progress(existing, checkpoint)
        if existing == checkpoint:
            return 0
        if checkpoint.last_local_sequence == 0:
            if checkpoint.last_idempotency_key is not None:
                raise ValueError("Le checkpoint zéro ne doit pas référencer de clé d'idempotence.")
        else:
            if checkpoint.last_idempotency_key is None:
                raise ValueError(
                    "Un checkpoint non nul doit référencer sa clé d'idempotence finale."
                )
            row = self._connection.execute(
                """
                SELECT idempotency_key
                FROM spool_records
                WHERE local_sequence = ?
                """,
                (checkpoint.last_local_sequence,),
            ).fetchone()
            if row is None:
                raise ValueError("La séquence finale du checkpoint n'existe plus dans le spool.")
            if str(row["idempotency_key"]) != checkpoint.last_idempotency_key:
                raise ValueError(
                    "La séquence finale ne correspond pas à la clé d'idempotence annoncée."
                )

        with self._connection:
            self._upsert_checkpoint(checkpoint)
            cursor = self._connection.execute(
                "DELETE FROM spool_records WHERE local_sequence <= ?",
                (checkpoint.last_local_sequence,),
            )
        return int(cursor.rowcount)

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
