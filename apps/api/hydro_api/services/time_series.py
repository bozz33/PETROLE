"""Persistance immuable des mesures temporelles du Pilote/V1.

Le flux initial est volontairement hors ligne : un dataset déjà normalisé par
le pipeline d'import est rattaché explicitement à un tag de site. Cela conserve
les données brutes et leurs unités tout en créant une projection numérique SI
versionnée, sans introduire de connecteur SCADA ou de calibration implicite.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AssetInstance,
    AuditEvent,
    Dataset,
    DatasetImport,
    DatasetRow,
    MeasurementTag,
    ModelVersion,
    Organization,
    Project,
    SampleNormalized,
    SampleRaw,
    Site,
    TimeSeriesImport,
)
from hydro_api.schemas.time_series import MeasurementTagCreate
from hydro_api.services.data_import import get_dataset
from hydro_shared.errors import DimensionalityMismatchError, UnknownUnitError
from hydro_shared.units import SI_UNITS, Dimension, to_si

INGESTION_BATCH_SIZE = 5_000
INGESTION_ERROR_LIMIT = 100


def _audit(
    session: Session,
    *,
    organization_id: uuid.UUID,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    details: dict[str, Any],
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details,
            created_at=utc_now(),
        )
    )


def get_measurement_tag(session: Session, tag_id: uuid.UUID) -> MeasurementTag:
    tag = session.get(MeasurementTag, tag_id)
    if tag is None:
        raise ResourceNotFoundError("Tag de mesure", tag_id)
    return tag


def _validate_asset_hierarchy(
    session: Session,
    *,
    asset_instance_id: uuid.UUID,
    site_id: uuid.UUID,
) -> None:
    """Garantit qu'un tag ne rattache pas un actif d'un autre site."""

    record = session.execute(
        select(AssetInstance.id, Project.site_id)
        .join(ModelVersion, AssetInstance.model_version_id == ModelVersion.id)
        .join(Project, ModelVersion.project_id == Project.id)
        .where(AssetInstance.id == asset_instance_id)
    ).one_or_none()
    if record is None:
        raise ResourceNotFoundError("Équipement", asset_instance_id)
    if record.site_id != site_id:
        raise ResourceConflictError(
            "L'équipement rattaché au tag doit appartenir au même site que le tag."
        )


def create_measurement_tag(session: Session, data: MeasurementTagCreate) -> MeasurementTag:
    """Crée un tag, après vérification stricte de la hiérarchie organisation/site."""

    if session.get(Organization, data.organization_id) is None:
        raise ResourceNotFoundError("Organisation", data.organization_id)
    site = session.get(Site, data.site_id)
    if site is None:
        raise ResourceNotFoundError("Site", data.site_id)
    if site.organization_id != data.organization_id:
        raise ResourceConflictError("Le site du tag appartient à une autre organisation.")
    if data.asset_instance_id is not None:
        _validate_asset_hierarchy(
            session,
            asset_instance_id=data.asset_instance_id,
            site_id=data.site_id,
        )
    try:
        to_si(1.0, data.source_unit, data.dimension)
    except (DimensionalityMismatchError, UnknownUnitError) as exc:
        raise ResourceConflictError(
            "L'unité source du tag est inconnue ou incompatible avec sa dimension."
        ) from exc

    tag = MeasurementTag(
        organization_id=data.organization_id,
        site_id=data.site_id,
        asset_instance_id=data.asset_instance_id,
        external_name=data.external_name,
        name=data.name,
        measurement_type=data.measurement_type,
        dimension=data.dimension.value,
        source_unit=data.source_unit,
        si_unit=SI_UNITS[data.dimension],
        source=data.source,
        status="active",
        metadata_payload=data.metadata,
    )
    session.add(tag)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ResourceConflictError(
            f"Le tag externe « {data.external_name} » existe déjà sur ce site."
        ) from exc
    _audit(
        session,
        organization_id=tag.organization_id,
        action="create",
        object_type="measurement_tag",
        object_id=tag.id,
        details={
            "site_id": str(tag.site_id),
            "external_name": tag.external_name,
            "dimension": tag.dimension,
        },
    )
    return tag


def list_measurement_tags(
    session: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[MeasurementTag], int]:
    """Liste les tags d'une organisation, éventuellement restreints à un site."""

    statement = select(MeasurementTag).where(MeasurementTag.organization_id == organization_id)
    count_statement = (
        select(func.count())
        .select_from(MeasurementTag)
        .where(MeasurementTag.organization_id == organization_id)
    )
    if site_id is not None:
        statement = statement.where(MeasurementTag.site_id == site_id)
        count_statement = count_statement.where(MeasurementTag.site_id == site_id)
    total = session.scalar(count_statement)
    items = session.scalars(
        statement.order_by(MeasurementTag.external_name).limit(limit).offset(offset)
    ).all()
    return list(items), int(total or 0)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return None
    return timestamp.astimezone(UTC)


def _append_error(
    errors: list[dict[str, Any]],
    *,
    source_row: int,
    code: str,
    message: str,
) -> None:
    if len(errors) < INGESTION_ERROR_LIMIT:
        errors.append({"source_row": source_row, "code": code, "message": message})


def _assert_dataset_matches_tag(
    session: Session,
    *,
    dataset: Dataset,
    tag: MeasurementTag,
) -> Dimension:
    if dataset.kind != "measurements" or dataset.status != "imported":
        raise ResourceConflictError(
            "Le dataset doit être un jeu de mesures importé sans erreur avant son ingestion temporelle."
        )
    if dataset.organization_id != tag.organization_id:
        raise ResourceConflictError(
            "Le dataset et le tag doivent appartenir à la même organisation."
        )
    project = session.get(Project, dataset.project_id) if dataset.project_id is not None else None
    if project is None or project.site_id != tag.site_id:
        raise ResourceConflictError(
            "Le dataset de mesures doit être rattaché à un projet du même site que le tag."
        )
    raw_dimension = dataset.mapping.get("dimensions", {}).get("value")
    try:
        dimension = Dimension(str(raw_dimension))
    except ValueError as exc:
        raise ResourceConflictError(
            "La dimension du dataset de mesures n'est pas reconnue."
        ) from exc
    if dimension.value != tag.dimension:
        raise ResourceConflictError(
            "La dimension du dataset doit correspondre à la dimension du tag."
        )
    return dimension


def _flush_samples(
    session: Session,
    raw_samples: list[dict[str, Any]],
    normalized_samples: list[dict[str, Any]],
) -> None:
    if raw_samples:
        session.execute(insert(SampleRaw), raw_samples)
        session.execute(insert(SampleNormalized), normalized_samples)
        raw_samples.clear()
        normalized_samples.clear()


def import_dataset_time_series(
    session: Session,
    *,
    dataset_id: uuid.UUID,
    tag_id: uuid.UUID,
    idempotency_key: str,
    processing_version: str,
) -> TimeSeriesImport:
    """Projette un dataset immuable vers les tables temporelles D12.

    Les lignes invalides restent présentes dans ``dataset_rows``. Elles ne sont
    simplement pas projetées lorsqu'elles n'ont pas de timestamp/valeur
    exploitable ; les mesures ``bad`` valides sont, elles, conservées.
    """

    dataset = get_dataset(session, dataset_id)
    tag = get_measurement_tag(session, tag_id)
    dimension = _assert_dataset_matches_tag(session, dataset=dataset, tag=tag)
    existing = session.scalar(
        select(TimeSeriesImport).where(
            TimeSeriesImport.dataset_id == dataset.id,
            TimeSeriesImport.tag_id == tag.id,
            TimeSeriesImport.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing

    now = utc_now()
    import_run = TimeSeriesImport(
        organization_id=tag.organization_id,
        dataset_id=dataset.id,
        tag_id=tag.id,
        idempotency_key=idempotency_key,
        processing_version=processing_version,
        status="running",
        source_hash=session.scalar(
            select(DatasetImport.content_hash)
            .where(DatasetImport.dataset_id == dataset.id)
            .order_by(DatasetImport.created_at.desc())
            .limit(1)
        )
        or "sha256:unknown",
        row_count=0,
        accepted_count=0,
        rejected_count=0,
        errors=[],
        created_at=now,
        finished_at=None,
    )
    session.add(import_run)
    session.flush()

    value_column = dataset.mapping.get("fields", {}).get("value")
    raw_samples: list[dict[str, Any]] = []
    normalized_samples: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    row_count = 0
    accepted_count = 0
    rejected_count = 0
    for row in session.scalars(
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset.id)
        .order_by(DatasetRow.source_row)
        .execution_options(yield_per=INGESTION_BATCH_SIZE)
    ):
        row_count += 1
        if row.errors:
            rejected_count += 1
            _append_error(
                errors,
                source_row=row.source_row,
                code="DATASET_ROW_REJECTED",
                message="La ligne contient déjà des erreurs de normalisation du dataset.",
            )
            continue
        normalized = row.normalized_payload
        source_name = str(normalized.get("source") or "").strip()
        if source_name != tag.external_name:
            rejected_count += 1
            _append_error(
                errors,
                source_row=row.source_row,
                code="TAG_SOURCE_MISMATCH",
                message="La source de la ligne ne correspond pas au nom externe du tag ciblé.",
            )
            continue
        timestamp = _parse_timestamp(normalized.get("timestamp"))
        raw_value = normalized.get("value")
        if timestamp is None:
            rejected_count += 1
            _append_error(
                errors,
                source_row=row.source_row,
                code="INVALID_TIMESTAMP",
                message="La ligne ne possède pas d'horodatage UTC exploitable.",
            )
            continue
        if not isinstance(raw_value, int | float) or not math.isfinite(float(raw_value)):
            rejected_count += 1
            _append_error(
                errors,
                source_row=row.source_row,
                code="INVALID_VALUE",
                message="La ligne ne possède pas de valeur numérique normalisée exploitable.",
            )
            continue
        unit_metadata = normalized.get("_units", {}).get("value", {})
        source_unit = str(unit_metadata.get("source_unit") or tag.source_unit)
        si_unit = str(unit_metadata.get("si_unit") or SI_UNITS[dimension])
        source_value = (
            row.raw_payload.get(value_column)
            if isinstance(value_column, str)
            else dataset.mapping.get("constants", {}).get("value")
        )
        raw_sample_id = uuid.uuid4()
        quality = row.quality
        raw_samples.append(
            {
                "id": raw_sample_id,
                "tag_id": tag.id,
                "time_series_import_id": import_run.id,
                "dataset_id": dataset.id,
                "dataset_row_id": row.id,
                "source_timestamp": timestamp,
                "ingest_timestamp": now,
                "source_value": source_value,
                "source_unit": source_unit,
                "quality": quality,
                "sequence_number": row.source_row,
                "raw_payload": row.raw_payload,
            }
        )
        normalized_samples.append(
            {
                "id": uuid.uuid4(),
                "tag_id": tag.id,
                "raw_sample_id": raw_sample_id,
                "timestamp": timestamp,
                "value_si": float(raw_value),
                "si_unit": si_unit,
                "quality": quality,
                "processing_version": processing_version,
                "processing_payload": {
                    "dimension": dimension.value,
                    "dataset_id": str(dataset.id),
                    "dataset_row_id": str(row.id),
                    "source_unit": source_unit,
                },
                "processed_at": now,
            }
        )
        accepted_count += 1
        if len(raw_samples) >= INGESTION_BATCH_SIZE:
            _flush_samples(session, raw_samples, normalized_samples)
    _flush_samples(session, raw_samples, normalized_samples)

    import_run.row_count = row_count
    import_run.accepted_count = accepted_count
    import_run.rejected_count = rejected_count
    import_run.errors = errors
    import_run.status = "completed" if not rejected_count else "completed_with_errors"
    import_run.finished_at = utc_now()
    session.flush()
    _audit(
        session,
        organization_id=tag.organization_id,
        action="import",
        object_type="time_series_import",
        object_id=import_run.id,
        details={
            "dataset_id": str(dataset.id),
            "tag_id": str(tag.id),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "processing_version": processing_version,
        },
    )
    return import_run


def get_time_series_import(session: Session, import_id: uuid.UUID) -> TimeSeriesImport:
    import_run = session.get(TimeSeriesImport, import_id)
    if import_run is None:
        raise ResourceNotFoundError("Import temporel", import_id)
    return import_run


def list_normalized_samples(
    session: Session,
    *,
    tag_id: uuid.UUID,
    start_timestamp: datetime | None,
    end_timestamp: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Lit la projection SI avec assez de lignage pour une future série UI."""

    get_measurement_tag(session, tag_id)
    filters = [SampleNormalized.tag_id == tag_id]
    if start_timestamp is not None:
        filters.append(SampleNormalized.timestamp >= start_timestamp)
    if end_timestamp is not None:
        filters.append(SampleNormalized.timestamp <= end_timestamp)
    total = session.scalar(select(func.count()).select_from(SampleNormalized).where(*filters))
    records = session.execute(
        select(SampleNormalized, SampleRaw)
        .join(SampleRaw, SampleNormalized.raw_sample_id == SampleRaw.id)
        .where(*filters)
        .order_by(SampleNormalized.timestamp, SampleRaw.sequence_number, SampleNormalized.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return (
        [
            {
                "id": normalized.id,
                "raw_sample_id": raw.id,
                "dataset_id": raw.dataset_id,
                "dataset_row_id": raw.dataset_row_id,
                "source_timestamp": raw.source_timestamp,
                "ingest_timestamp": raw.ingest_timestamp,
                "source_value": raw.source_value,
                "source_unit": raw.source_unit,
                "timestamp": normalized.timestamp,
                "value_si": normalized.value_si,
                "si_unit": normalized.si_unit,
                "quality": normalized.quality,
                "sequence_number": raw.sequence_number,
                "processing_version": normalized.processing_version,
            }
            for normalized, raw in records
        ],
        int(total or 0),
    )


__all__ = [
    "create_measurement_tag",
    "get_measurement_tag",
    "get_time_series_import",
    "import_dataset_time_series",
    "list_measurement_tags",
    "list_normalized_samples",
]
