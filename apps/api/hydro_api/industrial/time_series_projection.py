"""Projection des batches industriels read-only vers les séries PETROLE.

Le flux conserve d'abord chaque échantillon brut dans ``samples_raw`` puis crée
une projection SI versionnée quand la valeur est exploitable. Aucun faux dataset
fichier n'est créé pour une source OPC UA ou historian.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.industrial.quality_mapping import CanonicalQuality
from hydro_api.models import MeasurementTag, SampleNormalized, SampleRaw, TimeSeriesImport
from hydro_shared.errors import DimensionalityMismatchError, UnknownUnitError
from hydro_shared.units import SI_UNITS, Dimension, to_si

_SOURCE_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_ERROR_LIMIT = 100


@dataclass(frozen=True, slots=True)
class IndustrialBatchSample:
    """Échantillon industriel brut avec lignage explicite et réversible."""

    sequence_number: int
    source_timestamp: datetime
    server_timestamp: datetime | None
    source_value: Any
    source_unit: str
    quality: CanonicalQuality
    source_quality_code: str
    quality_mapping_ref: str
    raw_payload: dict[str, Any]

    def __post_init__(self) -> None:
        if self.sequence_number < 0:
            raise ValueError("La séquence industrielle doit être positive ou nulle.")
        if self.source_timestamp.tzinfo is None:
            raise ValueError("Le SourceTimestamp industriel doit être timezone-aware.")
        if self.server_timestamp is not None and self.server_timestamp.tzinfo is None:
            raise ValueError("Le ServerTimestamp industriel doit être timezone-aware.")
        if not self.source_unit.strip():
            raise ValueError("L'unité source industrielle est obligatoire.")
        if not self.source_quality_code.strip() or not self.quality_mapping_ref.strip():
            raise ValueError("Le code qualité source et son mapping sont obligatoires.")

    @property
    def source_timestamp_utc(self) -> datetime:
        return self.source_timestamp.astimezone(UTC)

    @property
    def server_timestamp_utc(self) -> datetime | None:
        if self.server_timestamp is None:
            return None
        return self.server_timestamp.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class IndustrialBatchResult:
    import_id: uuid.UUID
    replayed: bool
    row_count: int
    accepted_count: int
    rejected_count: int
    raw_created_count: int
    status: str


def _validate_batch_contract(
    *,
    idempotency_key: str,
    processing_version: str,
    source_hash: str,
    source_ref: str,
    samples: tuple[IndustrialBatchSample, ...],
) -> None:
    if not idempotency_key.strip() or not processing_version.strip() or not source_ref.strip():
        raise ValueError("Clé d'idempotence, version de traitement et source sont obligatoires.")
    if not _SOURCE_HASH_PATTERN.fullmatch(source_hash):
        raise ValueError("Le hash source industriel doit être un SHA-256 préfixé par 'sha256:'.")
    if not samples:
        raise ValueError("Un batch industriel doit contenir au moins un échantillon.")
    sequences = [sample.sequence_number for sample in samples]
    if len(sequences) != len(set(sequences)):
        raise ValueError("Chaque séquence ne peut apparaître qu'une fois dans un batch industriel.")


def _tag_dimension(tag: MeasurementTag) -> Dimension:
    try:
        return Dimension(tag.dimension)
    except ValueError as exc:
        raise ResourceConflictError("La dimension du tag industriel n'est pas reconnue.") from exc


def _append_error(
    errors: list[dict[str, Any]],
    *,
    sequence_number: int,
    code: str,
    message: str,
) -> None:
    if len(errors) < _ERROR_LIMIT:
        errors.append(
            {
                "sequence_number": sequence_number,
                "code": code,
                "message": message,
            }
        )


def _raw_payload_envelope(
    sample: IndustrialBatchSample,
    *,
    source_ref: str,
) -> dict[str, Any]:
    return {
        "source_payload": sample.raw_payload,
        "industrial_lineage": {
            "source_ref": source_ref,
            "source_quality_code": sample.source_quality_code,
            "quality_mapping_ref": sample.quality_mapping_ref,
            "server_timestamp": (
                sample.server_timestamp_utc.isoformat()
                if sample.server_timestamp_utc is not None
                else None
            ),
        },
    }


def _existing_batch(
    session: Session,
    *,
    tag_id: uuid.UUID,
    idempotency_key: str,
) -> TimeSeriesImport | None:
    return session.scalar(
        select(TimeSeriesImport).where(
            TimeSeriesImport.tag_id == tag_id,
            TimeSeriesImport.dataset_id.is_(None),
            TimeSeriesImport.idempotency_key == idempotency_key,
        )
    )


def ingest_industrial_batch(
    session: Session,
    *,
    tag_id: uuid.UUID,
    idempotency_key: str,
    processing_version: str,
    source_hash: str,
    source_ref: str,
    samples: tuple[IndustrialBatchSample, ...],
) -> IndustrialBatchResult:
    """Conserve le brut puis projette en SI un batch industriel idempotent."""

    _validate_batch_contract(
        idempotency_key=idempotency_key,
        processing_version=processing_version,
        source_hash=source_hash,
        source_ref=source_ref,
        samples=samples,
    )
    tag = session.scalar(select(MeasurementTag).where(MeasurementTag.id == tag_id).with_for_update())
    if tag is None:
        raise ResourceNotFoundError("Tag de mesure", tag_id)
    if tag.status != "active":
        raise ResourceConflictError("Une source industrielle ne peut alimenter qu'un tag actif.")
    dimension = _tag_dimension(tag)

    existing = _existing_batch(session, tag_id=tag.id, idempotency_key=idempotency_key)
    if existing is not None:
        if existing.processing_version != processing_version or existing.source_hash != source_hash:
            raise ResourceConflictError(
                "La clé d'idempotence industrielle existe avec une autre version ou source."
            )
        return IndustrialBatchResult(
            import_id=existing.id,
            replayed=True,
            row_count=existing.row_count,
            accepted_count=existing.accepted_count,
            rejected_count=existing.rejected_count,
            raw_created_count=existing.raw_created_count,
            status=existing.status,
        )

    now = utc_now()
    import_run = TimeSeriesImport(
        organization_id=tag.organization_id,
        dataset_id=None,
        tag_id=tag.id,
        idempotency_key=idempotency_key,
        processing_version=processing_version,
        status="running",
        source_hash=source_hash,
        row_count=len(samples),
        accepted_count=0,
        rejected_count=0,
        raw_created_count=0,
        raw_reused_count=0,
        errors=[],
        created_at=now,
        finished_at=None,
    )
    session.add(import_run)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ResourceConflictError("Le batch industriel existe déjà.") from exc

    errors: list[dict[str, Any]] = []
    accepted_count = 0
    rejected_count = 0
    for sample in sorted(samples, key=lambda item: item.sequence_number):
        raw_id = uuid.uuid4()
        session.add(
            SampleRaw(
                id=raw_id,
                tag_id=tag.id,
                time_series_import_id=import_run.id,
                dataset_id=None,
                dataset_row_id=None,
                source_timestamp=sample.source_timestamp_utc,
                ingest_timestamp=now,
                source_value=sample.source_value,
                source_unit=sample.source_unit,
                quality=sample.quality,
                sequence_number=sample.sequence_number,
                raw_payload=_raw_payload_envelope(sample, source_ref=source_ref),
            )
        )
        import_run.raw_created_count += 1

        if sample.source_unit != tag.source_unit:
            rejected_count += 1
            _append_error(
                errors,
                sequence_number=sample.sequence_number,
                code="SOURCE_UNIT_MISMATCH",
                message="L'unité reçue diffère de l'unité validée du tag.",
            )
            continue
        if isinstance(sample.source_value, bool) or not isinstance(sample.source_value, int | float):
            rejected_count += 1
            _append_error(
                errors,
                sequence_number=sample.sequence_number,
                code="NON_NUMERIC_VALUE",
                message="La valeur industrielle ne peut pas être projetée numériquement en SI.",
            )
            continue
        numeric_value = float(sample.source_value)
        if not math.isfinite(numeric_value):
            rejected_count += 1
            _append_error(
                errors,
                sequence_number=sample.sequence_number,
                code="NON_FINITE_VALUE",
                message="La valeur industrielle numérique n'est pas finie.",
            )
            continue
        try:
            value_si = to_si(numeric_value, sample.source_unit, dimension)
        except (DimensionalityMismatchError, UnknownUnitError) as exc:
            rejected_count += 1
            _append_error(
                errors,
                sequence_number=sample.sequence_number,
                code="UNIT_CONVERSION_ERROR",
                message=str(exc),
            )
            continue

        session.add(
            SampleNormalized(
                id=uuid.uuid4(),
                tag_id=tag.id,
                raw_sample_id=raw_id,
                time_series_import_id=import_run.id,
                timestamp=sample.source_timestamp_utc,
                value_si=value_si,
                si_unit=SI_UNITS[dimension],
                quality=sample.quality,
                processing_version=processing_version,
                processing_payload={
                    "source_kind": "industrial",
                    "source_ref": source_ref,
                    "source_unit": sample.source_unit,
                    "source_quality_code": sample.source_quality_code,
                    "quality_mapping_ref": sample.quality_mapping_ref,
                    "server_timestamp": (
                        sample.server_timestamp_utc.isoformat()
                        if sample.server_timestamp_utc is not None
                        else None
                    ),
                },
                processed_at=now,
            )
        )
        accepted_count += 1

    import_run.accepted_count = accepted_count
    import_run.rejected_count = rejected_count
    import_run.errors = errors
    import_run.status = "completed" if rejected_count == 0 else "completed_with_errors"
    import_run.finished_at = utc_now()
    try:
        session.flush()
    except IntegrityError as exc:
        raise ResourceConflictError(
            "Une séquence industrielle du batch existe déjà ou viole le lignage temporel."
        ) from exc

    return IndustrialBatchResult(
        import_id=import_run.id,
        replayed=False,
        row_count=import_run.row_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        raw_created_count=import_run.raw_created_count,
        status=import_run.status,
    )


__all__ = ["IndustrialBatchResult", "IndustrialBatchSample", "ingest_industrial_batch"]
