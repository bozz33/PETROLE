"""Persistance immuable des mesures temporelles du Pilote/V1.

Le flux initial est volontairement hors ligne : un dataset déjà normalisé par
le pipeline d'import est rattaché explicitement à un tag de site. Cela conserve
les données brutes et leurs unités tout en créant une projection numérique SI
versionnée, sans introduire de connecteur SCADA ou de calibration implicite.
"""

from __future__ import annotations

import math
import uuid
from collections import Counter
from datetime import UTC, datetime
from itertools import pairwise
from statistics import median
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
from hydro_api.schemas.time_series import MeasurementTagCreate, OutlierMethod, SampleQuality
from hydro_api.services.data_import import get_dataset
from hydro_shared.errors import DimensionalityMismatchError, UnknownUnitError
from hydro_shared.units import SI_UNITS, Dimension, to_si

INGESTION_BATCH_SIZE = 5_000
INGESTION_ERROR_LIMIT = 100
DEFAULT_ANALYSIS_QUALITIES: tuple[SampleQuality, ...] = (
    "good",
    "uncertain",
    "substituted",
    "estimated",
)


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
    if normalized_samples:
        session.execute(insert(SampleNormalized), normalized_samples)
    if raw_samples or normalized_samples:
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
    tag = session.scalar(
        select(MeasurementTag).where(MeasurementTag.id == tag_id).with_for_update()
    )
    if tag is None:
        raise ResourceNotFoundError("Tag de mesure", tag_id)
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
    existing_version = session.scalar(
        select(TimeSeriesImport).where(
            TimeSeriesImport.dataset_id == dataset.id,
            TimeSeriesImport.tag_id == tag.id,
            TimeSeriesImport.processing_version == processing_version,
        )
    )
    if existing_version is not None:
        raise ResourceConflictError(
            "Cette version de traitement existe déjà pour ce dataset et ce tag ; "
            "réutilisez sa clé d'idempotence ou créez une nouvelle version."
        )

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
        raw_created_count=0,
        raw_reused_count=0,
        errors=[],
        created_at=now,
        finished_at=None,
    )
    session.add(import_run)
    session.flush()

    value_column = dataset.mapping.get("fields", {}).get("value")
    raw_samples: list[dict[str, Any]] = []
    normalized_samples: list[dict[str, Any]] = []
    existing_raw_by_dataset_row: dict[uuid.UUID, uuid.UUID] = {
        dataset_row_id: raw_sample_id
        for dataset_row_id, raw_sample_id in session.execute(
            select(SampleRaw.dataset_row_id, SampleRaw.id).where(
                SampleRaw.tag_id == tag.id,
                SampleRaw.dataset_id == dataset.id,
                SampleRaw.dataset_row_id.is_not(None),
            )
        )
        if dataset_row_id is not None
    }
    errors: list[dict[str, Any]] = []
    row_count = 0
    accepted_count = 0
    rejected_count = 0
    raw_created_count = 0
    raw_reused_count = 0
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
        quality = row.quality
        raw_sample_id = existing_raw_by_dataset_row.get(row.id)
        if raw_sample_id is None:
            raw_sample_id = uuid.uuid4()
            existing_raw_by_dataset_row[row.id] = raw_sample_id
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
            raw_created_count += 1
        else:
            raw_reused_count += 1
        normalized_samples.append(
            {
                "id": uuid.uuid4(),
                "tag_id": tag.id,
                "raw_sample_id": raw_sample_id,
                "time_series_import_id": import_run.id,
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
    import_run.raw_created_count = raw_created_count
    import_run.raw_reused_count = raw_reused_count
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
            "raw_created_count": raw_created_count,
            "raw_reused_count": raw_reused_count,
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
    processing_version: str | None,
    qualities: list[SampleQuality] | None,
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
    if processing_version is not None:
        filters.append(SampleNormalized.processing_version == processing_version)
    if qualities is not None:
        filters.append(SampleNormalized.quality.in_(qualities))
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
                "time_series_import_id": normalized.time_series_import_id,
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


def list_processing_versions(
    session: Session,
    *,
    tag_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Expose les projections disponibles sans choisir silencieusement la plus récente."""

    get_measurement_tag(session, tag_id)
    records = session.execute(
        select(
            SampleNormalized.processing_version,
            func.count(),
            func.min(SampleNormalized.timestamp),
            func.max(SampleNormalized.timestamp),
        )
        .where(SampleNormalized.tag_id == tag_id)
        .group_by(SampleNormalized.processing_version)
        .order_by(SampleNormalized.processing_version)
    ).all()
    return [
        {
            "processing_version": processing_version,
            "sample_count": int(sample_count),
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
        }
        for processing_version, sample_count, start_timestamp, end_timestamp in records
    ]


class _RunningStatistics:
    """Statistiques population, stables numériquement, pour la série visible."""

    def __init__(self) -> None:
        self.count = 0
        self.minimum: float | None = None
        self.maximum: float | None = None
        self.mean = 0.0
        self.m2 = 0.0

    def add(self, value: float) -> None:
        self.count += 1
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)

    @property
    def stddev(self) -> float | None:
        if self.count == 0:
            return None
        return math.sqrt(self.m2 / self.count)


def _normalize_boundary(timestamp: datetime | None) -> datetime | None:
    """Le contrat des séries utilise UTC, mais accepte une borne offset-aware."""

    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        raise ResourceConflictError("Les bornes temporelles doivent inclure un fuseau horaire.")
    return timestamp.astimezone(UTC)


def _quantile_linear(values: list[float], probability: float) -> float:
    """Quantile déterministe par interpolation linéaire sur données triées."""

    if not values:
        raise ValueError("Un quantile exige au moins une valeur.")
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (position - lower) * (values[upper] - values[lower])


def _outlier_scores(
    records: list[tuple[SampleNormalized, SampleRaw]],
    *,
    method: OutlierMethod,
    zscore_threshold: float,
    iqr_multiplier: float,
) -> tuple[dict[uuid.UUID, float], float | None]:
    """Retourne uniquement les valeurs signalées ; aucun échantillon n'est altéré."""

    if method == "none" or len(records) < 2:
        return {}, None if method == "none" else (
            zscore_threshold if method == "zscore" else iqr_multiplier
        )

    values = [float(normalized.value_si) for normalized, _ in records]
    if method == "zscore":
        statistics = _RunningStatistics()
        for value in values:
            statistics.add(value)
        stddev = statistics.stddev
        if stddev is None or math.isclose(stddev, 0.0, abs_tol=1e-15):
            return {}, zscore_threshold
        return (
            {
                normalized.id: abs((float(normalized.value_si) - statistics.mean) / stddev)
                for normalized, _ in records
                if abs((float(normalized.value_si) - statistics.mean) / stddev) > zscore_threshold
            },
            zscore_threshold,
        )

    sorted_values = sorted(values)
    first_quartile = _quantile_linear(sorted_values, 0.25)
    third_quartile = _quantile_linear(sorted_values, 0.75)
    interquartile_range = third_quartile - first_quartile
    if math.isclose(interquartile_range, 0.0, abs_tol=1e-15):
        return {}, iqr_multiplier
    lower_bound = first_quartile - iqr_multiplier * interquartile_range
    upper_bound = third_quartile + iqr_multiplier * interquartile_range
    scores: dict[uuid.UUID, float] = {}
    for normalized, _ in records:
        value = float(normalized.value_si)
        if value < lower_bound:
            scores[normalized.id] = (lower_bound - value) / interquartile_range
        elif value > upper_bound:
            scores[normalized.id] = (value - upper_bound) / interquartile_range
    return scores, iqr_multiplier


def analyze_normalized_series(
    session: Session,
    *,
    tag_id: uuid.UUID,
    processing_version: str,
    start_timestamp: datetime | None,
    end_timestamp: datetime | None,
    qualities: list[SampleQuality] | None,
    reference_interval_seconds: float | None,
    gap_factor: float,
    outlier_method: OutlierMethod,
    zscore_threshold: float,
    iqr_multiplier: float,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Analyse en lecture seule d'une seule projection versionnée d'un tag.

    La détection ne supprime ni ne corrige jamais les points. Les diagnostics
    sont calculés sur la série complète filtrée dans la plage, avant pagination,
    afin qu'une page isolée ne produise pas un verdict différent.
    """

    tag = get_measurement_tag(session, tag_id)
    normalized_start = _normalize_boundary(start_timestamp)
    normalized_end = _normalize_boundary(end_timestamp)
    if (
        normalized_start is not None
        and normalized_end is not None
        and normalized_start > normalized_end
    ):
        raise ResourceConflictError("La borne de début doit précéder la borne de fin.")

    candidate_filters = [
        SampleNormalized.tag_id == tag_id,
        SampleNormalized.processing_version == processing_version,
    ]
    if normalized_start is not None:
        candidate_filters.append(SampleNormalized.timestamp >= normalized_start)
    if normalized_end is not None:
        candidate_filters.append(SampleNormalized.timestamp <= normalized_end)

    records: list[tuple[SampleNormalized, SampleRaw]] = [
        (normalized, raw)
        for normalized, raw in session.execute(
            select(SampleNormalized, SampleRaw)
            .join(SampleRaw, SampleNormalized.raw_sample_id == SampleRaw.id)
            .where(*candidate_filters)
        )
    ]
    included_qualities = list(dict.fromkeys(qualities or DEFAULT_ANALYSIS_QUALITIES))
    candidate_quality_counts: Counter[str] = Counter(
        normalized.quality for normalized, _ in records
    )
    visible_records = [record for record in records if record[0].quality in included_qualities]
    visible_quality_counts: Counter[str] = Counter(
        normalized.quality for normalized, _ in visible_records
    )

    chronological_records = sorted(
        records,
        key=lambda record: (
            record[0].timestamp,
            record[1].sequence_number is None,
            record[1].sequence_number if record[1].sequence_number is not None else 0,
            str(record[0].id),
        ),
    )
    source_order_records = sorted(
        records,
        key=lambda record: (
            record[1].sequence_number is None,
            record[1].sequence_number if record[1].sequence_number is not None else 0,
            str(record[0].id),
        ),
    )
    duplicate_timestamps = Counter(normalized.timestamp for normalized, _ in chronological_records)
    duplicate_ids = {
        normalized.id
        for normalized, _ in chronological_records
        if duplicate_timestamps[normalized.timestamp] > 1
    }
    point_ids_by_timestamp: dict[datetime, list[uuid.UUID]] = {}
    for normalized, _ in chronological_records:
        point_ids_by_timestamp.setdefault(normalized.timestamp, []).append(normalized.id)
    duplicate_timestamp_count = sum(
        count - 1 for count in duplicate_timestamps.values() if count > 1
    )
    out_of_order_count = sum(
        1
        for previous, current in pairwise(source_order_records)
        if current[0].timestamp < previous[0].timestamp
    )

    positive_intervals = [
        (current[0].timestamp - previous[0].timestamp).total_seconds()
        for previous, current in pairwise(chronological_records)
        if current[0].timestamp > previous[0].timestamp
    ]
    observed_interval_seconds = float(median(positive_intervals)) if positive_intervals else None
    effective_reference_interval = (
        reference_interval_seconds
        if reference_interval_seconds is not None
        else observed_interval_seconds
    )
    effective_gap_threshold = (
        effective_reference_interval * gap_factor
        if effective_reference_interval is not None
        else None
    )
    gap_after_seconds: dict[uuid.UUID, float] = {}
    gap_interval_count = 0
    if effective_gap_threshold is not None:
        for previous, current in pairwise(chronological_records):
            interval_seconds = (current[0].timestamp - previous[0].timestamp).total_seconds()
            if interval_seconds > effective_gap_threshold:
                gap_interval_count += 1
                # Un point bad peut partager le même horodatage qu'un point
                # visible. Le trou doit donc rester visible sur toute la
                # grappe horodatée, sans confondre un filtre qualité et une
                # disparition silencieuse du diagnostic.
                for point_id in point_ids_by_timestamp[previous[0].timestamp]:
                    gap_after_seconds[point_id] = interval_seconds

    outlier_scores, effective_outlier_threshold = _outlier_scores(
        visible_records,
        method=outlier_method,
        zscore_threshold=zscore_threshold,
        iqr_multiplier=iqr_multiplier,
    )
    statistics = _RunningStatistics()
    for normalized, _ in visible_records:
        statistics.add(float(normalized.value_si))

    issues: list[dict[str, Any]] = []
    if out_of_order_count:
        issues.append(
            {
                "code": "DQ-007",
                "severity": "warning",
                "count": out_of_order_count,
                "message": "Des horodatages sont hors ordre dans la séquence source.",
            }
        )
    bad_count = candidate_quality_counts.get("bad", 0)
    if bad_count and "bad" not in included_qualities:
        issues.append(
            {
                "code": "DQ-008",
                "severity": "warning",
                "count": bad_count,
                "message": "Les mesures bad sont exclues par le filtre par défaut, sans suppression.",
            }
        )
    if duplicate_timestamp_count:
        issues.append(
            {
                "code": "TS-DUPLICATE",
                "severity": "warning",
                "count": duplicate_timestamp_count,
                "message": "Des horodatages dupliqués restent présents dans la projection sélectionnée.",
            }
        )
    if effective_reference_interval is None and len(chronological_records) > 1:
        issues.append(
            {
                "code": "TS-CADENCE_UNAVAILABLE",
                "severity": "information",
                "count": 1,
                "message": "Aucune cadence positive ne peut être déterminée ; aucun trou n'est déclaré.",
            }
        )
    if gap_interval_count:
        issues.append(
            {
                "code": "TS-GAP",
                "severity": "warning",
                "count": gap_interval_count,
                "message": "Des intervalles dépassent la cadence de référence multipliée par le facteur déclaré.",
            }
        )
    if outlier_scores:
        issues.append(
            {
                "code": "TS-OUTLIER",
                "severity": "warning",
                "count": len(outlier_scores),
                "message": "Des points sont signalés par la méthode d'aberrants choisie, sans être supprimés.",
            }
        )

    visible_chronological_records = [
        record for record in chronological_records if record[0].quality in included_qualities
    ]
    page_records = visible_chronological_records[offset : offset + limit]
    items = [
        {
            "id": normalized.id,
            "raw_sample_id": raw.id,
            "time_series_import_id": normalized.time_series_import_id,
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
            "duplicate": normalized.id in duplicate_ids,
            "gap_after": normalized.id in gap_after_seconds,
            "gap_after_seconds": gap_after_seconds.get(normalized.id),
            "outlier": normalized.id in outlier_scores,
            "outlier_score": outlier_scores.get(normalized.id),
        }
        for normalized, raw in page_records
    ]
    return {
        "tag": tag,
        "processing_version": processing_version,
        "requested_start_timestamp": normalized_start,
        "requested_end_timestamp": normalized_end,
        "start_timestamp": chronological_records[0][0].timestamp if chronological_records else None,
        "end_timestamp": chronological_records[-1][0].timestamp if chronological_records else None,
        "included_qualities": included_qualities,
        "quality_counts": dict(sorted(candidate_quality_counts.items())),
        "visible_quality_counts": dict(sorted(visible_quality_counts.items())),
        "candidate_sample_count": len(records),
        "excluded_sample_count": len(records) - len(visible_records),
        "statistics": {
            "sample_count": statistics.count,
            "minimum_value_si": statistics.minimum,
            "maximum_value_si": statistics.maximum,
            "mean_value_si": statistics.mean if statistics.count else None,
            "stddev_value_si": statistics.stddev,
        },
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "out_of_order_count": out_of_order_count,
        "gap_count": gap_interval_count,
        "observed_interval_seconds": observed_interval_seconds,
        "reference_interval_seconds": effective_reference_interval,
        "gap_factor": gap_factor,
        "outlier_method": outlier_method,
        "outlier_threshold": effective_outlier_threshold,
        "outlier_count": len(outlier_scores),
        "issues": issues,
        "items": items,
        "total": len(visible_chronological_records),
        "limit": limit,
        "offset": offset,
    }


__all__ = [
    "analyze_normalized_series",
    "create_measurement_tag",
    "get_measurement_tag",
    "get_time_series_import",
    "import_dataset_time_series",
    "list_measurement_tags",
    "list_normalized_samples",
    "list_processing_versions",
]
