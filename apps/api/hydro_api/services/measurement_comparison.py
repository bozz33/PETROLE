"""Comparaison immuable entre une série de mesures et un calcul stationnaire.

V1-B ne transforme pas PETROLE en simulateur temporel. Une fenêtre de mesures
correspondant à un régime stable est comparée à la valeur constante produite par
un ``CalculationRun`` terminé. Les points, leurs exclusions et leur lignage sont
figés afin de préparer une calibration ultérieure sans en faire une implicite.
"""

from __future__ import annotations

import math
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Literal, cast

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AssetInstance,
    AuditEvent,
    CalculationRun,
    CatalogItem,
    MeasurementComparison,
    MeasurementModelMapping,
    MeasurementResidual,
    MeasurementTag,
    ModelVersion,
    NetworkEdge,
    NetworkNode,
    Organization,
    Project,
    SampleNormalized,
    SampleRaw,
)
from hydro_api.schemas.measurement_comparison import (
    ComparisonMetric,
    ComparisonTargetType,
    MeasurementComparisonCreate,
    MeasurementModelMappingCreate,
)
from hydro_api.schemas.time_series import SampleQuality
from hydro_shared.hashing import sha256_of
from hydro_shared.units import SI_UNITS, Dimension

MetricSpecification = tuple[ComparisonTargetType, Dimension, str]

# Le nom de métrique décrit la grandeur extraite, sans syntaxe de chemin JSON
# arbitraire. Ceci rend l'extraction révisable et la dimension vérifiable.
METRIC_SPECS: dict[ComparisonMetric, MetricSpecification] = {
    "pressure_pa": ("node", Dimension.PRESSURE, "pressure_pa"),
    "flow_m3_s": ("edge", Dimension.VOLUMETRIC_FLOW, "flow_m3_s"),
    "pressure_min_pa": ("edge", Dimension.PRESSURE, "min_pressure_pa"),
    "pressure_max_pa": ("edge", Dimension.PRESSURE, "max_pressure_pa"),
    "suction_pressure_pa": ("pump", Dimension.PRESSURE, "suction_pressure_pa"),
    "discharge_pressure_pa": ("pump", Dimension.PRESSURE, "discharge_pressure_pa"),
}

COMPARISON_STATUSES = frozenset({"SIM_CONVERGED", "SIM_CONVERGED_WARN"})
RESIDUAL_INSERT_BATCH_SIZE = 5_000


def _audit(
    session: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    details: dict[str, Any],
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details,
            created_at=utc_now(),
        )
    )


def _flush(session: Session, message: str) -> None:
    try:
        session.flush()
    except IntegrityError as exc:
        raise ResourceConflictError(message) from exc


def get_measurement_mapping(
    session: Session,
    mapping_id: uuid.UUID,
) -> MeasurementModelMapping:
    mapping = session.get(MeasurementModelMapping, mapping_id)
    if mapping is None:
        raise ResourceNotFoundError("Correspondance mesure-modèle", mapping_id)
    return mapping


def get_measurement_comparison(
    session: Session,
    comparison_id: uuid.UUID,
) -> MeasurementComparison:
    comparison = session.get(MeasurementComparison, comparison_id)
    if comparison is None:
        raise ResourceNotFoundError("Comparaison mesure-modèle", comparison_id)
    return comparison


def _project_and_tag(
    session: Session,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> tuple[Project, MeasurementTag]:
    if session.get(Organization, organization_id) is None:
        raise ResourceNotFoundError("Organisation", organization_id)
    project = session.get(Project, project_id)
    if project is None:
        raise ResourceNotFoundError("Projet", project_id)
    tag = session.get(MeasurementTag, tag_id)
    if tag is None:
        raise ResourceNotFoundError("Tag de mesure", tag_id)
    if project.organization_id != organization_id or tag.organization_id != organization_id:
        raise ResourceConflictError(
            "Le projet et le tag doivent appartenir à l'organisation de la correspondance."
        )
    if project.site_id is None or project.site_id != tag.site_id:
        raise ResourceConflictError(
            "Le projet et le tag doivent être rattachés au même site logique."
        )
    return project, tag


def _target_for_mapping(
    session: Session,
    *,
    target_type: ComparisonTargetType,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
) -> NetworkNode | NetworkEdge | AssetInstance:
    """Résout une cible et impose sa filiation au projet concerné."""

    target: NetworkNode | NetworkEdge | AssetInstance | None
    if target_type == "node":
        target = session.get(NetworkNode, target_id)
        resource_name = "Nœud"
    elif target_type == "edge":
        target = session.get(NetworkEdge, target_id)
        resource_name = "Tronçon"
    else:
        target = session.get(AssetInstance, target_id)
        resource_name = "Pompe"
    if target is None:
        raise ResourceNotFoundError(resource_name, target_id)

    model = session.get(ModelVersion, target.model_version_id)
    if model is None or model.project_id != project_id:
        raise ResourceConflictError(
            "La cible calculée doit appartenir à une version du projet de la correspondance."
        )
    if isinstance(target, NetworkNode) and target.kind == "station":
        raise ResourceConflictError(
            "Un nœud station ne porte pas une pression unique ; utilisez une métrique de pompe "
            "d'aspiration ou de refoulement."
        )
    if isinstance(target, AssetInstance):
        catalog_item = session.get(CatalogItem, target.catalog_item_id)
        node = session.get(NetworkNode, target.node_id) if target.node_id is not None else None
        if (
            catalog_item is None
            or catalog_item.kind != "pump"
            or node is None
            or node.kind != "station"
        ):
            raise ResourceConflictError(
                "La cible de type pump doit être une pompe placée sur un nœud station."
            )
    return target


def create_measurement_mapping(
    session: Session,
    data: MeasurementModelMappingCreate,
    *,
    actor_id: uuid.UUID | None,
) -> MeasurementModelMapping:
    """Crée une version brouillon d'une correspondance explicitement désignée."""

    project, tag = _project_and_tag(
        session,
        organization_id=data.organization_id,
        project_id=data.project_id,
        tag_id=data.tag_id,
    )
    expected_target, expected_dimension, _ = METRIC_SPECS[data.metric]
    if expected_target != data.target_type:
        raise ResourceConflictError(
            "Cette métrique n'est pas compatible avec le type de cible indiqué."
        )
    if tag.dimension != expected_dimension.value or tag.si_unit != SI_UNITS[expected_dimension]:
        raise ResourceConflictError(
            "La dimension et l'unité SI du tag sont incompatibles avec la métrique calculée."
        )
    target = _target_for_mapping(
        session,
        target_type=data.target_type,
        target_id=data.target_id,
        project_id=project.id,
    )
    version_number = (
        int(
            session.scalar(
                select(func.coalesce(func.max(MeasurementModelMapping.version_number), 0)).where(
                    MeasurementModelMapping.tag_id == tag.id
                )
            )
            or 0
        )
        + 1
    )
    mapping = MeasurementModelMapping(
        organization_id=data.organization_id,
        project_id=project.id,
        model_version_id=target.model_version_id,
        tag_id=tag.id,
        version_number=version_number,
        target_type=data.target_type,
        target_id=data.target_id,
        metric=data.metric,
        dimension=expected_dimension.value,
        si_unit=SI_UNITS[expected_dimension],
        status="draft",
        source_ref=data.source_ref,
        created_by=actor_id,
        approved_by=None,
        approved_at=None,
    )
    session.add(mapping)
    _flush(session, "Cette version de correspondance entre en conflit avec une version existante.")
    _audit(
        session,
        organization_id=mapping.organization_id,
        actor_id=actor_id,
        action="measurement_mapping.created",
        object_type="measurement_model_mapping",
        object_id=mapping.id,
        details={
            "project_id": str(mapping.project_id),
            "model_version_id": str(mapping.model_version_id),
            "tag_id": str(mapping.tag_id),
            "version_number": mapping.version_number,
            "target_type": mapping.target_type,
            "target_id": str(mapping.target_id),
            "metric": mapping.metric,
        },
    )
    return mapping


def approve_measurement_mapping(
    session: Session,
    mapping_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None,
    comment: str | None,
) -> MeasurementModelMapping:
    """Fige une correspondance après une décision humaine traçable."""

    mapping = get_measurement_mapping(session, mapping_id)
    if mapping.status != "draft":
        raise ResourceConflictError("Seule une correspondance brouillon peut être approuvée.")
    # La cible est relue au moment de l'approbation pour éviter qu'un modèle
    # archivé ou une filiation modifiée ne soit approuvé par accident.
    _project_and_tag(
        session,
        organization_id=mapping.organization_id,
        project_id=mapping.project_id,
        tag_id=mapping.tag_id,
    )
    _target_for_mapping(
        session,
        target_type=cast(ComparisonTargetType, mapping.target_type),
        target_id=mapping.target_id,
        project_id=mapping.project_id,
    )
    mapping.status = "approved"
    mapping.approved_by = actor_id
    mapping.approved_at = utc_now()
    _flush(session, "Impossible d'approuver la correspondance mesure-modèle.")
    _audit(
        session,
        organization_id=mapping.organization_id,
        actor_id=actor_id,
        action="measurement_mapping.approved",
        object_type="measurement_model_mapping",
        object_id=mapping.id,
        details={"comment": comment, "version_number": mapping.version_number},
    )
    return mapping


def list_measurement_mappings(
    session: Session,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID | None,
    tag_id: uuid.UUID | None,
    status: Literal["draft", "approved", "archived"] | None,
    limit: int,
    offset: int,
) -> tuple[list[MeasurementModelMapping], int]:
    """Liste des correspondances sans sélectionner implicitement une version."""

    filters = [MeasurementModelMapping.organization_id == organization_id]
    if project_id is not None:
        filters.append(MeasurementModelMapping.project_id == project_id)
    if tag_id is not None:
        filters.append(MeasurementModelMapping.tag_id == tag_id)
    if status is not None:
        filters.append(MeasurementModelMapping.status == status)
    total = session.scalar(
        select(func.count()).select_from(MeasurementModelMapping).where(*filters)
    )
    items = list(
        session.scalars(
            select(MeasurementModelMapping)
            .where(*filters)
            .order_by(
                MeasurementModelMapping.tag_id,
                MeasurementModelMapping.version_number.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return items, int(total or 0)


def _normalize_boundary(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        raise ResourceConflictError("Les bornes temporelles doivent inclure un fuseau horaire.")
    return timestamp.astimezone(UTC)


def _calculation_and_mapping(
    session: Session,
    *,
    data: MeasurementComparisonCreate,
) -> tuple[MeasurementModelMapping, MeasurementTag, CalculationRun, ModelVersion]:
    mapping = get_measurement_mapping(session, data.mapping_id)
    if mapping.organization_id != data.organization_id:
        raise ResourceConflictError(
            "L'organisation demandée ne correspond pas à la correspondance."
        )
    if mapping.status != "approved":
        raise ResourceConflictError(
            "La correspondance doit être explicitement approuvée avant toute comparaison."
        )
    tag = session.get(MeasurementTag, mapping.tag_id)
    if tag is None:
        raise ResourceNotFoundError("Tag de mesure", mapping.tag_id)
    calculation = session.get(CalculationRun, data.calculation_id)
    if calculation is None:
        raise ResourceNotFoundError("Calcul", data.calculation_id)
    if calculation.status not in COMPARISON_STATUSES or calculation.result_payload is None:
        raise ResourceConflictError(
            "La comparaison exige un calcul stationnaire terminé avec un résultat convergé."
        )
    scenario = calculation.scenario
    model = session.get(ModelVersion, scenario.model_version_id)
    if model is None or model.project_id != mapping.project_id:
        raise ResourceConflictError(
            "Le calcul source doit appartenir au projet de la correspondance approuvée."
        )
    _target_for_mapping(
        session,
        target_type=cast(ComparisonTargetType, mapping.target_type),
        target_id=mapping.target_id,
        project_id=mapping.project_id,
    )
    target_model_id = _target_model_id(
        session,
        target_type=cast(ComparisonTargetType, mapping.target_type),
        target_id=mapping.target_id,
    )
    if target_model_id != mapping.model_version_id or mapping.model_version_id != model.id:
        raise ResourceConflictError(
            "La cible de la correspondance doit appartenir à la même version de modèle que le calcul."
        )
    return mapping, tag, calculation, model


def _target_model_id(
    session: Session,
    *,
    target_type: ComparisonTargetType,
    target_id: uuid.UUID,
) -> uuid.UUID:
    target: NetworkNode | NetworkEdge | AssetInstance | None
    if target_type == "node":
        target = session.get(NetworkNode, target_id)
    elif target_type == "edge":
        target = session.get(NetworkEdge, target_id)
    else:
        target = session.get(AssetInstance, target_id)
    if target is None:  # La validation précédente assure ce cas ; défense supplémentaire.
        raise ResourceConflictError("La cible de la correspondance n'existe plus.")
    return target.model_version_id


def _required_number(value: Any, *, metric: str) -> float:
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        raise ResourceConflictError(
            f"Le calcul source ne fournit pas de valeur numérique finie pour {metric}."
        )
    return float(value)


def _node_chainage(session: Session, *, model_id: uuid.UUID, node_id: uuid.UUID) -> float:
    """Reconstruit le chainage topologique d'un nœud du réseau linéaire MVP."""

    edges = list(
        session.scalars(
            select(NetworkEdge)
            .where(NetworkEdge.model_version_id == model_id)
            .order_by(NetworkEdge.sequence)
        )
    )
    chainages: dict[uuid.UUID, float] = {}
    current = 0.0
    for edge in edges:
        chainages.setdefault(edge.from_node_id, current)
        current += edge.length_m
        chainages[edge.to_node_id] = current
    try:
        return chainages[node_id]
    except KeyError as exc:
        raise ResourceConflictError("Le nœud cible n'appartient pas au chemin calculé.") from exc


def _matching_item(items: Any, *, key: str, expected: str, metric: str) -> dict[str, Any]:
    if not isinstance(items, list):
        raise ResourceConflictError(
            f"Le calcul source ne contient pas la section requise pour {metric}."
        )
    matches = [item for item in items if isinstance(item, dict) and item.get(key) == expected]
    if len(matches) != 1:
        raise ResourceConflictError(
            f"Le calcul source ne contient pas une cible unique pour {metric}."
        )
    return matches[0]


def extract_simulated_value(
    session: Session,
    *,
    mapping: MeasurementModelMapping,
    calculation: CalculationRun,
    model: ModelVersion,
) -> float:
    """Extrait une seule grandeur autorisée depuis le résultat archivé du moteur."""

    result = calculation.result_payload
    if not isinstance(result, dict):
        raise ResourceConflictError("Le calcul source ne contient aucun résultat exploitable.")
    target_type = cast(ComparisonTargetType, mapping.target_type)
    target = _target_for_mapping(
        session,
        target_type=target_type,
        target_id=mapping.target_id,
        project_id=mapping.project_id,
    )
    if target_type == "edge":
        edge = cast(NetworkEdge, target)
        segment = _matching_item(
            result.get("segments"),
            key="segment_id",
            expected=edge.code,
            metric=mapping.metric,
        )
        metric_key = METRIC_SPECS[cast(ComparisonMetric, mapping.metric)][2]
        return _required_number(segment.get(metric_key), metric=mapping.metric)

    if target_type == "pump":
        pump = cast(AssetInstance, target)
        pump_row: dict[str, Any] | None = None
        station_row: dict[str, Any] | None = None
        stations = result.get("stations")
        if not isinstance(stations, list):
            raise ResourceConflictError("Le calcul source ne contient aucun résultat de station.")
        for candidate_station in stations:
            if not isinstance(candidate_station, dict):
                continue
            for candidate_pump in candidate_station.get("pumps") or []:
                if isinstance(candidate_pump, dict) and candidate_pump.get("pump_id") == pump.code:
                    if pump_row is not None:
                        raise ResourceConflictError(
                            "La pompe cible apparaît plusieurs fois dans le calcul."
                        )
                    pump_row = candidate_pump
                    station_row = candidate_station
        if pump_row is None or station_row is None:
            raise ResourceConflictError("Le calcul source ne contient pas la pompe cible.")
        if mapping.metric == "flow_m3_s":
            return _required_number(pump_row.get("flow_m3_s"), metric=mapping.metric)
        if mapping.metric == "suction_pressure_pa":
            return _required_number(station_row.get("suction_pressure_pa"), metric=mapping.metric)
        return _required_number(station_row.get("discharge_pressure_pa"), metric=mapping.metric)

    node = cast(NetworkNode, target)
    chainage_m = _node_chainage(session, model_id=model.id, node_id=node.id)
    profile = result.get("profile")
    if not isinstance(profile, list):
        raise ResourceConflictError(
            "Le calcul source ne contient pas le profil hydraulique requis."
        )
    tolerance = max(1.0e-6, chainage_m * 1.0e-9)
    candidates = [
        item
        for item in profile
        if isinstance(item, dict)
        and isinstance(item.get("chainage_m"), int | float)
        and math.isclose(float(item["chainage_m"]), chainage_m, abs_tol=tolerance)
    ]
    if not candidates:
        raise ResourceConflictError(
            "Le profil du calcul ne contient pas le point hydraulique du nœud cible."
        )
    pressures = [
        _required_number(item.get("pressure_pa"), metric=mapping.metric) for item in candidates
    ]
    if any(not math.isclose(value, pressures[0], abs_tol=1.0e-6) for value in pressures[1:]):
        raise ResourceConflictError(
            "Le profil associe plusieurs pressions au nœud cible ; créez une métrique pompe explicite."
        )
    return pressures[0]


def _comparison_rows(
    session: Session,
    *,
    tag_id: uuid.UUID,
    processing_version: str,
    start_timestamp: datetime,
    end_timestamp: datetime,
) -> list[tuple[SampleNormalized, SampleRaw]]:
    records = session.execute(
        select(SampleNormalized, SampleRaw)
        .join(SampleRaw, SampleNormalized.raw_sample_id == SampleRaw.id)
        .where(
            SampleNormalized.tag_id == tag_id,
            SampleNormalized.processing_version == processing_version,
            SampleNormalized.timestamp >= start_timestamp,
            SampleNormalized.timestamp <= end_timestamp,
        )
        .order_by(SampleNormalized.timestamp, SampleRaw.sequence_number, SampleNormalized.id)
    ).all()
    return [(normalized, raw) for normalized, raw in records]


def _comparison_input_hash(
    *,
    mapping: MeasurementModelMapping,
    calculation: CalculationRun,
    processing_version: str,
    start_timestamp: datetime,
    end_timestamp: datetime,
    included_qualities: list[SampleQuality],
    records: list[tuple[SampleNormalized, SampleRaw]],
) -> str:
    """Empreinte toutes les sources sans dépendre d'un ordre de requête implicite."""

    return sha256_of(
        {
            "contract": "pilot-v1-b1",
            "mapping": {
                "id": mapping.id,
                "version_number": mapping.version_number,
                "model_version_id": mapping.model_version_id,
                "target_type": mapping.target_type,
                "target_id": mapping.target_id,
                "metric": mapping.metric,
                "dimension": mapping.dimension,
                "si_unit": mapping.si_unit,
            },
            "calculation": {
                "id": calculation.id,
                "input_hash": calculation.input_hash,
                "engine": calculation.engine,
                "engine_version": calculation.engine_version,
            },
            "series": {
                "tag_id": mapping.tag_id,
                "processing_version": processing_version,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "included_qualities": included_qualities,
                "samples": [
                    {
                        "normalized_sample_id": normalized.id,
                        "raw_sample_id": raw.id,
                        "timestamp": normalized.timestamp,
                        "value_si": normalized.value_si,
                        "quality": normalized.quality,
                    }
                    for normalized, raw in records
                ],
            },
        }
    )


def _kpis(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "n_compared": 0,
            "bias_si": None,
            "mae_si": None,
            "rmse_si": None,
            "min_residual_si": None,
            "max_residual_si": None,
        }
    count = len(values)
    return {
        "n_compared": count,
        "bias_si": sum(values) / count,
        "mae_si": sum(abs(value) for value in values) / count,
        "rmse_si": math.sqrt(sum(value * value for value in values) / count),
        "min_residual_si": min(values),
        "max_residual_si": max(values),
    }


def create_measurement_comparison(
    session: Session,
    data: MeasurementComparisonCreate,
    *,
    actor_id: uuid.UUID | None,
) -> MeasurementComparison:
    """Archive les résidus d'une fenêtre sans changer mesure ni calcul source."""

    mapping, tag, calculation, model = _calculation_and_mapping(session, data=data)
    start_timestamp = _normalize_boundary(data.start_timestamp)
    end_timestamp = _normalize_boundary(data.end_timestamp)
    records = _comparison_rows(
        session,
        tag_id=tag.id,
        processing_version=data.processing_version,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    if not records:
        raise ResourceConflictError(
            "Aucun échantillon de la version de traitement demandée ne se trouve dans cette fenêtre."
        )
    simulated_value_si = extract_simulated_value(
        session,
        mapping=mapping,
        calculation=calculation,
        model=model,
    )
    input_hash = _comparison_input_hash(
        mapping=mapping,
        calculation=calculation,
        processing_version=data.processing_version,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        included_qualities=data.included_qualities,
        records=records,
    )
    existing = session.scalar(
        select(MeasurementComparison).where(
            MeasurementComparison.organization_id == data.organization_id,
            MeasurementComparison.input_hash == input_hash,
        )
    )
    if existing is not None:
        return existing

    included_qualities = set(data.included_qualities)
    quality_counts = Counter(normalized.quality for normalized, _ in records)
    timestamp_counts = Counter(normalized.timestamp for normalized, _ in records)
    duplicate_timestamp_count = sum(count - 1 for count in timestamp_counts.values() if count > 1)
    residual_rows: list[dict[str, Any]] = []
    residuals_for_kpi: list[float] = []
    exclusion_counts: Counter[str] = Counter()
    comparison_id = uuid.uuid4()
    for normalized, raw in records:
        included = normalized.quality in included_qualities
        exclusion_reason = None if included else f"quality:{normalized.quality}"
        if exclusion_reason is not None:
            exclusion_counts[exclusion_reason] += 1
        residual = float(normalized.value_si) - simulated_value_si
        if included:
            residuals_for_kpi.append(residual)
        residual_rows.append(
            {
                "id": uuid.uuid4(),
                "comparison_id": comparison_id,
                "normalized_sample_id": normalized.id,
                "raw_sample_id": raw.id,
                "dataset_id": raw.dataset_id,
                "dataset_row_id": raw.dataset_row_id,
                "timestamp": normalized.timestamp,
                "measured_value_si": float(normalized.value_si),
                "simulated_value_si": simulated_value_si,
                "residual_si": residual,
                "quality": normalized.quality,
                "included_in_kpi": included,
                "exclusion_reason": exclusion_reason,
            }
        )
    if not residuals_for_kpi:
        raise ResourceConflictError(
            "La politique qualité exclut tous les échantillons ; aucun KPI ne peut être calculé."
        )

    kpis = _kpis(residuals_for_kpi)
    exclusions = {
        "n_candidates": len(records),
        "n_excluded_quality": len(records) - len(residuals_for_kpi),
        "n_excluded_outlier": 0,
        "quality_counts": dict(sorted(quality_counts.items())),
        "exclusion_counts": dict(sorted(exclusion_counts.items())),
        "duplicate_timestamp_count": duplicate_timestamp_count,
    }
    result_payload = {
        "contract_version": "pilot-v1-b1",
        "mapping_snapshot": {
            "id": str(mapping.id),
            "version_number": mapping.version_number,
            "model_version_id": str(mapping.model_version_id),
            "target_type": mapping.target_type,
            "target_id": str(mapping.target_id),
            "metric": mapping.metric,
            "dimension": mapping.dimension,
            "si_unit": mapping.si_unit,
            "source_ref": mapping.source_ref,
        },
        "kpis": kpis,
        "exclusions": exclusions,
        "outlier_policy": {"mode": "annotate_only", "excluded": False},
    }
    comparison = MeasurementComparison(
        id=comparison_id,
        organization_id=data.organization_id,
        project_id=mapping.project_id,
        mapping_id=mapping.id,
        calculation_id=calculation.id,
        tag_id=tag.id,
        processing_version=data.processing_version,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        included_qualities=list(data.included_qualities),
        input_hash=input_hash,
        calculation_input_hash=calculation.input_hash,
        engine=calculation.engine,
        engine_version=calculation.engine_version,
        simulated_value_si=simulated_value_si,
        si_unit=mapping.si_unit,
        status="completed",
        result_payload=result_payload,
        created_by=actor_id,
        created_at=utc_now(),
    )
    session.add(comparison)
    _flush(session, "Une comparaison identique existe déjà pour ces entrées immuables.")
    for index in range(0, len(residual_rows), RESIDUAL_INSERT_BATCH_SIZE):
        session.execute(
            insert(MeasurementResidual), residual_rows[index : index + RESIDUAL_INSERT_BATCH_SIZE]
        )
    _audit(
        session,
        organization_id=comparison.organization_id,
        actor_id=actor_id,
        action="measurement_comparison.created",
        object_type="measurement_comparison",
        object_id=comparison.id,
        details={
            "mapping_id": str(mapping.id),
            "calculation_id": str(calculation.id),
            "processing_version": data.processing_version,
            "input_hash": input_hash,
            "n_compared": kpis["n_compared"],
            "n_excluded_quality": exclusions["n_excluded_quality"],
        },
    )
    return comparison


def comparison_payload(session: Session, comparison: MeasurementComparison) -> dict[str, Any]:
    """Prépare la vue API sans exposer une comparaison comme une calibration."""

    mapping = get_measurement_mapping(session, comparison.mapping_id)
    result = comparison.result_payload
    return {
        "id": comparison.id,
        "organization_id": comparison.organization_id,
        "project_id": comparison.project_id,
        "model_version_id": mapping.model_version_id,
        "mapping_id": comparison.mapping_id,
        "calculation_id": comparison.calculation_id,
        "tag_id": comparison.tag_id,
        "processing_version": comparison.processing_version,
        "start_timestamp": comparison.start_timestamp,
        "end_timestamp": comparison.end_timestamp,
        "included_qualities": comparison.included_qualities,
        "input_hash": comparison.input_hash,
        "calculation_input_hash": comparison.calculation_input_hash,
        "engine": comparison.engine,
        "engine_version": comparison.engine_version,
        "simulated_value_si": comparison.simulated_value_si,
        "si_unit": comparison.si_unit,
        "status": comparison.status,
        "kpis": result["kpis"],
        "exclusions": result["exclusions"],
        "mapping": mapping,
        "created_by": comparison.created_by,
        "created_at": comparison.created_at,
    }


def list_measurement_residuals(
    session: Session,
    *,
    comparison_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Retourne les résidus, y compris les ``bad`` exclus des seuls KPI."""

    get_measurement_comparison(session, comparison_id)
    filters = [MeasurementResidual.comparison_id == comparison_id]
    total = session.scalar(select(func.count()).select_from(MeasurementResidual).where(*filters))
    rows = session.execute(
        select(MeasurementResidual, SampleNormalized, SampleRaw)
        .join(SampleNormalized, MeasurementResidual.normalized_sample_id == SampleNormalized.id)
        .join(SampleRaw, MeasurementResidual.raw_sample_id == SampleRaw.id)
        .where(*filters)
        .order_by(MeasurementResidual.timestamp, MeasurementResidual.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return (
        [
            {
                "id": residual.id,
                "comparison_id": residual.comparison_id,
                "normalized_sample_id": residual.normalized_sample_id,
                "raw_sample_id": residual.raw_sample_id,
                "dataset_id": residual.dataset_id,
                "dataset_row_id": residual.dataset_row_id,
                "timestamp": residual.timestamp,
                "measured_value_si": residual.measured_value_si,
                "simulated_value_si": residual.simulated_value_si,
                "residual_si": residual.residual_si,
                "quality": residual.quality,
                "included_in_kpi": residual.included_in_kpi,
                "exclusion_reason": residual.exclusion_reason,
                "source_timestamp": raw.source_timestamp,
                "ingest_timestamp": raw.ingest_timestamp,
                "source_value": raw.source_value,
                "source_unit": raw.source_unit,
                "processing_version": normalized.processing_version,
            }
            for residual, normalized, raw in rows
        ],
        int(total or 0),
    )


__all__ = [
    "approve_measurement_mapping",
    "comparison_payload",
    "create_measurement_comparison",
    "create_measurement_mapping",
    "extract_simulated_value",
    "get_measurement_comparison",
    "get_measurement_mapping",
    "list_measurement_mappings",
    "list_measurement_residuals",
]
