"""Génération et archivage des rapports opérationnels RPT-01 et RPT-03 à RPT-06."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AuditEvent,
    CalculationRun,
    GeneratedReport,
    ModelVersion,
    Project,
    ScenarioComparison,
    ScenarioRecord,
    StoredFile,
    TransferRun,
)
from hydro_api.schemas.reports import OperationalReportCreate
from hydro_api.storage import ObjectStorage
from hydro_reporting import OperationalReportData, ReportTable, build_operational_report_pdf
from hydro_shared.hashing import sha256_of_bytes


def _report_match(
    report: GeneratedReport,
    data: OperationalReportCreate,
) -> bool:
    return (
        report.report_type == data.report_type
        and report.template_version == data.template_version
        and report.locale == data.locale
        and report.source_id == data.source_id
    )


def _project_data(
    session: Session,
    project: Project,
    data: OperationalReportCreate,
    generated_at,
) -> OperationalReportData:
    models = list(
        session.scalars(
            select(ModelVersion)
            .where(ModelVersion.project_id == project.id)
            .order_by(ModelVersion.version_number)
        )
    )
    scenario_count = int(
        session.scalar(
            select(func.count())
            .select_from(ScenarioRecord)
            .join(ModelVersion)
            .where(ModelVersion.project_id == project.id)
        )
        or 0
    )
    calculation_count = int(
        session.scalar(
            select(func.count())
            .select_from(CalculationRun)
            .join(ScenarioRecord)
            .join(ModelVersion)
            .where(ModelVersion.project_id == project.id)
        )
        or 0
    )
    return OperationalReportData(
        code="RPT-01",
        title="Fiche projet et hypothèses",
        subject="Référentiel du projet, versions disponibles et état des études.",
        generated_at=generated_at,
        reference=str(project.id),
        template_version=data.template_version or "rpt-01/1.0",
        metadata={"Projet": project.code, "Organisation": str(project.organization_id)},
        key_values=(
            ("Nom", project.name),
            ("Code", project.code),
            ("Pays", project.country_code),
            ("Statut", project.status),
            ("Versions de modèle", len(models)),
            ("Scénarios", scenario_count),
            ("Calculs archivés", calculation_count),
        ),
        tables=(
            ReportTable(
                title="Versions du modèle",
                headers=("Version", "Nom", "Statut", "Empreinte"),
                rows=tuple(
                    (
                        model.version_number,
                        model.name,
                        model.status,
                        model.content_hash,
                    )
                    for model in models
                ),
            ),
        ),
        observations=(
            "Une version approuvée est immuable ; toute évolution crée une nouvelle version.",
            "Les hypothèses détaillées restent contenues dans le paquet canonique de chaque calcul.",
        ),
    )


def _comparison_data(
    comparison: ScenarioComparison,
    data: OperationalReportCreate,
    generated_at,
) -> OperationalReportData:
    ranked = comparison.result_payload.get("ranked") or []
    rows = tuple(
        (
            item.get("rank"),
            str(item.get("calculation_id", ""))[:8],
            item.get("status"),
            item.get("flow_m3_s"),
            item.get("total_power_w"),
            item.get("violation_count"),
        )
        for item in ranked
    )
    return OperationalReportData(
        code="RPT-03",
        title="Comparaison de scénarios",
        subject="Classement multicritère des calculs archivés du même projet.",
        generated_at=generated_at,
        reference=str(comparison.id),
        template_version=data.template_version or "rpt-03/1.0",
        metadata={
            "Projet": str(comparison.project_id),
            "Empreinte": comparison.content_hash,
        },
        key_values=(
            ("Calcul de référence", comparison.result_payload.get("reference_calculation_id")),
            ("Calcul recommandé", comparison.result_payload.get("recommended_calculation_id")),
            ("Nombre de calculs", len(comparison.calculation_ids)),
        ),
        tables=(
            ReportTable(
                title="Classement",
                headers=("Rang", "Calcul", "Statut", "Débit m³/s", "Puissance W", "Violations"),
                rows=rows,
            ),
        ),
        observations=(
            "Le classement privilégie un résultat approuvable, puis la puissance absorbée.",
            "Les écarts sont calculés par rapport au premier calcul fourni.",
        ),
    )


def _station_data(
    calculation: CalculationRun,
    data: OperationalReportCreate,
    generated_at,
) -> OperationalReportData:
    result = calculation.result_payload or {}
    stations = result.get("stations") or []
    station_rows: list[tuple[Any, ...]] = []
    pump_rows: list[tuple[Any, ...]] = []
    for station in stations:
        station_rows.append(
            (
                station.get("station_id"),
                station.get("active_pump_count"),
                station.get("suction_pressure_pa"),
                station.get("discharge_pressure_pa"),
                station.get("absorbed_power_w"),
            )
        )
        for pump in station.get("pumps") or []:
            pump_rows.append(
                (
                    station.get("station_id"),
                    pump.get("pump_id"),
                    pump.get("speed_ratio"),
                    pump.get("flow_m3_s"),
                    pump.get("head_m"),
                    pump.get("absorbed_power_w"),
                )
            )
    return OperationalReportData(
        code="RPT-04",
        title="Rapport stations et pompes",
        subject="Points de fonctionnement, pressions et puissances des équipements actifs.",
        generated_at=generated_at,
        reference=str(calculation.id),
        template_version=data.template_version or "rpt-04/1.0",
        metadata={
            "Scénario": str(calculation.scenario_id),
            "Moteur": calculation.engine_version,
        },
        key_values=(
            ("Statut du calcul", calculation.status),
            ("Débit m³/s", result.get("flow_m3_s")),
            ("Pression minimale Pa", result.get("min_pressure_pa")),
            ("Pression maximale Pa", result.get("max_pressure_pa")),
            ("Puissance totale W", result.get("total_power_w")),
        ),
        tables=(
            ReportTable(
                title="Stations",
                headers=("Station", "Pompes", "Aspiration Pa", "Refoulement Pa", "Puissance W"),
                rows=tuple(station_rows),
            ),
            ReportTable(
                title="Pompes actives",
                headers=("Station", "Pompe", "Vitesse", "Débit m³/s", "Hauteur m", "Puissance W"),
                rows=tuple(pump_rows),
            ),
        ),
        observations=tuple(
            str(item.get("message"))
            for item in (result.get("violations") or []) + (result.get("warnings") or [])
        ),
    )


def _transfer_data(
    transfer: TransferRun,
    data: OperationalReportCreate,
    generated_at,
) -> OperationalReportData:
    result = transfer.result_payload
    samples = result.get("samples") or []
    selected = samples
    if len(samples) > 24:
        step = max(len(samples) // 20, 1)
        selected = samples[::step]
        if selected[-1] != samples[-1]:
            selected.append(samples[-1])
    rows = tuple(
        (
            sample.get("time_s"),
            sample.get("source_level_m"),
            sample.get("destination_level_m"),
            sample.get("flow_m3_s"),
            sample.get("cumulative_withdrawn_m3"),
            sample.get("cumulative_received_m3"),
        )
        for sample in selected
    )
    return OperationalReportData(
        code="RPT-05",
        title="Simulation de transfert",
        subject="Évolution temporelle des niveaux, volumes, débit et énergie.",
        generated_at=generated_at,
        reference=str(transfer.id),
        template_version=data.template_version or "rpt-05/1.0",
        metadata={
            "Bac source": str(transfer.source_tank_id),
            "Bac destination": str(transfer.destination_tank_id),
            "Empreinte entrée": transfer.input_hash,
        },
        key_values=(
            ("Cause d'arrêt", result.get("stop_reason")),
            ("Objectif atteint", result.get("target_reached")),
            ("Durée s", result.get("duration_s")),
            ("Volume soutiré m³", result.get("withdrawn_volume_m3")),
            ("Volume reçu m³", result.get("received_volume_m3")),
            ("Pertes m³", result.get("losses_m3")),
            ("Énergie J", result.get("energy_j")),
            ("Résidu de bilan m³", result.get("balance_residual_m3")),
        ),
        tables=(
            ReportTable(
                title="Échantillons temporels",
                headers=(
                    "Temps s",
                    "Niveau source m",
                    "Niveau destination m",
                    "Débit m³/s",
                    "Soutiré m³",
                    "Reçu m³",
                ),
                rows=rows,
            ),
        ),
        observations=tuple(result.get("messages") or []),
    )


def _balance_data(
    transfer: TransferRun,
    data: OperationalReportCreate,
    generated_at,
) -> OperationalReportData:
    balance = transfer.balance_payload
    if not balance:
        raise ResourceConflictError(
            "Le bilan matière doit être calculé avant de produire le rapport RPT-06."
        )
    return OperationalReportData(
        code="RPT-06",
        title="Bilan matière",
        subject="Rapprochement des inventaires, du compteur, des pertes et des incertitudes.",
        generated_at=generated_at,
        reference=str(transfer.id),
        template_version=data.template_version or "rpt-06/1.0",
        metadata={"Transfert": str(transfer.id), "Empreinte entrée": transfer.input_hash},
        key_values=tuple((key.replace("_", " "), value) for key, value in balance.items()),
        observations=(
            (
                "Le bilan respecte la limite d'acceptation."
                if balance.get("within_tolerance")
                else "Le bilan dépasse la limite d'acceptation et exige une investigation."
            ),
        ),
        assumptions=(
            "Les incertitudes fournies sont des incertitudes-types indépendantes.",
            "La limite retient le maximum entre tolérance absolue, relative et incertitude élargie.",
        ),
    )


def _resolve_report_data(
    session: Session,
    data: OperationalReportCreate,
    generated_at,
) -> tuple[uuid.UUID, uuid.UUID | None, str, OperationalReportData]:
    if data.report_type == "project_sheet":
        project = session.get(Project, data.source_id)
        if project is None:
            raise ResourceNotFoundError("Projet", data.source_id)
        return (
            project.organization_id,
            None,
            "project",
            _project_data(session, project, data, generated_at),
        )
    if data.report_type == "scenario_comparison":
        comparison = session.get(ScenarioComparison, data.source_id)
        if comparison is None:
            raise ResourceNotFoundError("Comparaison", data.source_id)
        return (
            comparison.organization_id,
            None,
            "comparison",
            _comparison_data(comparison, data, generated_at),
        )
    if data.report_type == "station_pumps":
        calculation = session.get(CalculationRun, data.source_id)
        if calculation is None:
            raise ResourceNotFoundError("Calcul", data.source_id)
        organization_id = calculation.scenario.model_version.project.organization_id
        return (
            organization_id,
            calculation.id,
            "calculation",
            _station_data(calculation, data, generated_at),
        )
    transfer = session.get(TransferRun, data.source_id)
    if transfer is None:
        raise ResourceNotFoundError("Transfert", data.source_id)
    report_data = (
        _transfer_data(transfer, data, generated_at)
        if data.report_type == "transfer_simulation"
        else _balance_data(transfer, data, generated_at)
    )
    return transfer.organization_id, None, "transfer", report_data


def create_operational_report(
    session: Session,
    data: OperationalReportCreate,
    *,
    idempotency_key: str,
    storage: ObjectStorage,
) -> GeneratedReport:
    """Génère, stocke et audite un rapport opérationnel depuis une source archivée."""

    existing = session.scalar(
        select(GeneratedReport).where(
            GeneratedReport.source_id == data.source_id,
            GeneratedReport.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if not _report_match(existing, data):
            raise ResourceConflictError(
                "La clé d'idempotence du rapport correspond à d'autres paramètres."
            )
        return existing

    generated_at = utc_now()
    organization_id, calculation_id, source_type, report_data = _resolve_report_data(
        session,
        data,
        generated_at,
    )
    content = build_operational_report_pdf(report_data)
    content_hash = sha256_of_bytes(content)
    report_id = uuid.uuid4()
    file_id = uuid.uuid4()
    safe_reference = re.sub(r"[^A-Za-z0-9._-]+", "-", report_data.reference).strip("-")
    filename = f"{report_data.code.lower()}-{safe_reference[:16]}.pdf"
    object_key = f"organizations/{organization_id}/reports/{report_id}/{filename}"
    storage.put_bytes(object_key, content, "application/pdf")

    stored_file = StoredFile(
        id=file_id,
        organization_id=organization_id,
        bucket=storage.bucket,
        object_key=object_key,
        filename=filename,
        media_type="application/pdf",
        size_bytes=len(content),
        content_hash=content_hash,
        created_at=generated_at,
    )
    report = GeneratedReport(
        id=report_id,
        organization_id=organization_id,
        calculation_id=calculation_id,
        source_type=source_type,
        source_id=data.source_id,
        file_id=file_id,
        idempotency_key=idempotency_key,
        report_type=data.report_type,
        template_version=data.template_version or "1.0",
        format="pdf",
        locale=data.locale,
        status="generated",
        content_hash=content_hash,
        created_at=generated_at,
    )
    session.add_all([stored_file, report])
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        storage.delete(object_key)
        duplicate = session.scalar(
            select(GeneratedReport).where(
                GeneratedReport.source_type == source_type,
                GeneratedReport.source_id == data.source_id,
                GeneratedReport.idempotency_key == idempotency_key,
            )
        )
        if duplicate is not None and _report_match(duplicate, data):
            return duplicate
        raise ResourceConflictError(
            "Le rapport entre en conflit avec une génération existante."
        ) from error

    session.add(
        AuditEvent(
            organization_id=organization_id,
            action="report.generated",
            object_type="report",
            object_id=report.id,
            details={
                "source_type": source_type,
                "source_id": str(data.source_id),
                "report_type": data.report_type,
                "content_hash": content_hash,
            },
            created_at=generated_at,
        )
    )
    session.flush()
    return report


__all__ = ["create_operational_report"]
