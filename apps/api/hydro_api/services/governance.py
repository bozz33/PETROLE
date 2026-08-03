"""Services de gouvernance, de conformité et de traçabilité."""

from __future__ import annotations

import uuid
from datetime import datetime
from math import isclose
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AuditEvent,
    CalculationRun,
    Organization,
    RuleDefinition,
    RuleEvaluation,
    RuleSet,
    RuleSetStandard,
    StandardReference,
)
from hydro_api.schemas.governance import (
    RuleCreate,
    RuleSetCreate,
    StandardCreate,
    StandardUpdate,
)
from hydro_shared.errors import InvalidInputError
from hydro_shared.hashing import sha256_of


def _flush(session: Session, message: str) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ResourceConflictError(message) from error


def _audit(
    session: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details or {},
            created_at=utc_now(),
        )
    )


def _standard_hash(item: StandardReference) -> str:
    return sha256_of(
        {
            "organization_id": item.organization_id,
            "parent_id": item.parent_id,
            "code": item.code,
            "title": item.title,
            "issuing_body": item.issuing_body,
            "edition": item.edition,
            "publication_date": item.publication_date,
            "effective_date": item.effective_date,
            "licensed_copy_ref": item.licensed_copy_ref,
            "source_url": item.source_url,
        }
    )


def get_standard(session: Session, standard_id: uuid.UUID) -> StandardReference:
    item = session.get(StandardReference, standard_id)
    if item is None:
        raise ResourceNotFoundError("Référence normative", standard_id)
    return item


def create_standard(
    session: Session,
    data: StandardCreate,
    *,
    actor_id: uuid.UUID | None,
) -> StandardReference:
    """Crée une référence bibliographique sans stocker le texte protégé."""

    if session.get(Organization, data.organization_id) is None:
        raise ResourceNotFoundError("Organisation", data.organization_id)
    if data.parent_id is not None:
        parent = get_standard(session, data.parent_id)
        if parent.organization_id != data.organization_id or parent.code != data.code:
            raise ResourceConflictError(
                "L'édition parente doit appartenir à la même organisation et porter le même code."
            )
    values = data.model_dump()
    values["source_url"] = str(data.source_url) if data.source_url is not None else None
    item = StandardReference(
        **values,
        status="draft",
        content_hash="",
    )
    item.content_hash = _standard_hash(item)
    session.add(item)
    _flush(session, "Cette édition normative est déjà enregistrée.")
    _audit(
        session,
        organization_id=item.organization_id,
        actor_id=actor_id,
        action="standard.created",
        object_type="standard",
        object_id=item.id,
        details={"code": item.code, "edition": item.edition},
    )
    return item


def list_standards(
    session: Session,
    organization_id: uuid.UUID,
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[StandardReference], int]:
    conditions = [StandardReference.organization_id == organization_id]
    if status is not None:
        conditions.append(StandardReference.status == status)
    total = (
        session.scalar(select(func.count()).select_from(StandardReference).where(*conditions)) or 0
    )
    items = session.scalars(
        select(StandardReference)
        .where(*conditions)
        .order_by(StandardReference.code, StandardReference.edition.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), int(total)


def update_standard(
    session: Session,
    standard_id: uuid.UUID,
    data: StandardUpdate,
    *,
    actor_id: uuid.UUID | None,
) -> StandardReference:
    item = get_standard(session, standard_id)
    changes = data.model_dump(exclude_unset=True)
    if "source_url" in changes and changes["source_url"] is not None:
        changes["source_url"] = str(changes["source_url"])
    if item.status == "active":
        if set(changes) != {"status"} or changes["status"] not in {"withdrawn", "archived"}:
            raise ResourceConflictError(
                "Une édition active est immuable ; seule son retrait ou son archivage est permis."
            )
    elif item.status in {"withdrawn", "archived"}:
        raise ResourceConflictError("Une édition retirée ou archivée est immuable.")
    for field, value in changes.items():
        setattr(item, field, value)
    item.content_hash = _standard_hash(item)
    _audit(
        session,
        organization_id=item.organization_id,
        actor_id=actor_id,
        action="standard.updated",
        object_type="standard",
        object_id=item.id,
        details={"fields": sorted(changes)},
    )
    session.flush()
    return item


def approve_standard(
    session: Session,
    standard_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None,
) -> StandardReference:
    item = get_standard(session, standard_id)
    if item.status != "draft":
        raise ResourceConflictError("Seule une édition en brouillon peut être activée.")
    item.status = "active"
    item.approved_at = utc_now()
    _audit(
        session,
        organization_id=item.organization_id,
        actor_id=actor_id,
        action="standard.approved",
        object_type="standard",
        object_id=item.id,
        details={"content_hash": item.content_hash},
    )
    session.flush()
    return item


def get_rule_set(session: Session, rule_set_id: uuid.UUID) -> RuleSet:
    item = session.get(RuleSet, rule_set_id)
    if item is None:
        raise ResourceNotFoundError("Jeu de règles", rule_set_id)
    return item


def _rule_set_standard_ids(session: Session, rule_set_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(RuleSetStandard.standard_id)
            .where(RuleSetStandard.rule_set_id == rule_set_id)
            .order_by(RuleSetStandard.standard_id)
        )
    )


def serialize_rule_set(session: Session, item: RuleSet) -> dict[str, Any]:
    """Produit le contrat public avec les références normatives explicites."""

    return {
        "id": item.id,
        "organization_id": item.organization_id,
        "parent_id": item.parent_id,
        "code": item.code,
        "title": item.title,
        "country_code": item.country_code,
        "domain": item.domain,
        "version_number": item.version_number,
        "description": item.description,
        "status": item.status,
        "standard_ids": _rule_set_standard_ids(session, item.id),
        "content_hash": item.content_hash,
        "approved_at": item.approved_at,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def refresh_rule_set_hash(session: Session, item: RuleSet) -> str:
    rules = session.scalars(
        select(RuleDefinition)
        .where(RuleDefinition.rule_set_id == item.id)
        .order_by(RuleDefinition.code)
    ).all()
    item.content_hash = sha256_of(
        {
            "organization_id": item.organization_id,
            "parent_id": item.parent_id,
            "code": item.code,
            "title": item.title,
            "country_code": item.country_code,
            "domain": item.domain,
            "version_number": item.version_number,
            "description": item.description,
            "standard_ids": _rule_set_standard_ids(session, item.id),
            "rules": [
                {
                    "code": rule.code,
                    "standard_id": rule.standard_id,
                    "title": rule.title,
                    "severity": rule.severity,
                    "domain": rule.domain,
                    "metric_path": rule.metric_path,
                    "operator": rule.operator,
                    "limit_value": rule.limit_value,
                    "upper_limit_value": rule.upper_limit_value,
                    "unit": rule.unit,
                    "applicability": rule.applicability,
                    "parameters": rule.parameters,
                    "message": rule.message,
                    "source_clause_ref": rule.source_clause_ref,
                    "status": rule.status,
                }
                for rule in rules
            ],
        }
    )
    session.flush()
    return item.content_hash


def create_rule_set(
    session: Session,
    data: RuleSetCreate,
    *,
    actor_id: uuid.UUID | None,
) -> RuleSet:
    if session.get(Organization, data.organization_id) is None:
        raise ResourceNotFoundError("Organisation", data.organization_id)
    standards = [get_standard(session, identifier) for identifier in data.standard_ids]
    if any(item.organization_id != data.organization_id for item in standards):
        raise ResourceConflictError("Toutes les normes doivent appartenir à la même organisation.")
    if any(item.status != "active" for item in standards):
        raise ResourceConflictError("Toutes les éditions référencées doivent être actives.")
    if data.parent_id is not None:
        parent = get_rule_set(session, data.parent_id)
        if parent.organization_id != data.organization_id or parent.code != data.code:
            raise ResourceConflictError(
                "Le jeu parent doit appartenir à la même organisation et porter le même code."
            )
    latest = session.scalar(
        select(func.max(RuleSet.version_number)).where(
            RuleSet.organization_id == data.organization_id,
            RuleSet.code == data.code,
        )
    )
    item = RuleSet(
        organization_id=data.organization_id,
        parent_id=data.parent_id,
        code=data.code,
        title=data.title,
        country_code=data.country_code,
        domain=data.domain,
        version_number=int(latest or 0) + 1,
        description=data.description,
        status="draft",
        content_hash="",
    )
    session.add(item)
    _flush(session, "Cette version du jeu de règles existe déjà.")
    session.add_all(
        [RuleSetStandard(rule_set_id=item.id, standard_id=standard.id) for standard in standards]
    )
    session.flush()
    refresh_rule_set_hash(session, item)
    _audit(
        session,
        organization_id=item.organization_id,
        actor_id=actor_id,
        action="rule_set.created",
        object_type="rule_set",
        object_id=item.id,
        details={"code": item.code, "version": item.version_number},
    )
    return item


def list_rule_sets(
    session: Session,
    organization_id: uuid.UUID,
    *,
    status: str | None,
    domain: str | None,
    limit: int,
    offset: int,
) -> tuple[list[RuleSet], int]:
    conditions = [RuleSet.organization_id == organization_id]
    if status is not None:
        conditions.append(RuleSet.status == status)
    if domain is not None:
        conditions.append(RuleSet.domain == domain)
    total = session.scalar(select(func.count()).select_from(RuleSet).where(*conditions)) or 0
    items = session.scalars(
        select(RuleSet)
        .where(*conditions)
        .order_by(RuleSet.code, RuleSet.version_number.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), int(total)


def create_rule(
    session: Session,
    rule_set_id: uuid.UUID,
    data: RuleCreate,
    *,
    actor_id: uuid.UUID | None,
) -> RuleDefinition:
    rule_set = get_rule_set(session, rule_set_id)
    if rule_set.status != "draft":
        raise ResourceConflictError("Un jeu approuvé ou archivé est immuable.")
    standard_ids = set(_rule_set_standard_ids(session, rule_set.id))
    if data.standard_id is not None and data.standard_id not in standard_ids:
        raise ResourceConflictError("La règle doit référencer une norme liée à ce jeu.")
    rule = RuleDefinition(rule_set_id=rule_set.id, status="draft", **data.model_dump())
    session.add(rule)
    _flush(session, f"Le code de règle « {data.code} » existe déjà dans ce jeu.")
    refresh_rule_set_hash(session, rule_set)
    _audit(
        session,
        organization_id=rule_set.organization_id,
        actor_id=actor_id,
        action="rule.created",
        object_type="rule",
        object_id=rule.id,
        details={"rule_set_id": str(rule_set.id), "code": rule.code},
    )
    return rule


def get_rule(session: Session, rule_id: uuid.UUID) -> RuleDefinition:
    item = session.get(RuleDefinition, rule_id)
    if item is None:
        raise ResourceNotFoundError("Règle", rule_id)
    return item


def list_rules(session: Session, rule_set_id: uuid.UUID) -> list[RuleDefinition]:
    get_rule_set(session, rule_set_id)
    return list(
        session.scalars(
            select(RuleDefinition)
            .where(RuleDefinition.rule_set_id == rule_set_id)
            .order_by(RuleDefinition.code)
        )
    )


def approve_rule(
    session: Session,
    rule_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None,
) -> RuleDefinition:
    rule = get_rule(session, rule_id)
    rule_set = get_rule_set(session, rule.rule_set_id)
    if rule_set.status != "draft" or rule.status != "draft":
        raise ResourceConflictError(
            "Seule une règle en brouillon d'un jeu en brouillon est approuvable."
        )
    rule.status = "approved"
    rule.approved_at = utc_now()
    session.flush()
    refresh_rule_set_hash(session, rule_set)
    _audit(
        session,
        organization_id=rule_set.organization_id,
        actor_id=actor_id,
        action="rule.approved",
        object_type="rule",
        object_id=rule.id,
        details={"rule_set_id": str(rule_set.id)},
    )
    return rule


def approve_rule_set(
    session: Session,
    rule_set_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None,
) -> RuleSet:
    item = get_rule_set(session, rule_set_id)
    if item.status != "draft":
        raise ResourceConflictError("Seul un jeu de règles en brouillon peut être approuvé.")
    rules = list_rules(session, item.id)
    if not rules:
        raise ResourceConflictError("Le jeu doit contenir au moins une règle approuvée.")
    if any(rule.status != "approved" for rule in rules):
        raise ResourceConflictError("Toutes les règles doivent être approuvées par un expert.")
    standards = [
        get_standard(session, identifier) for identifier in _rule_set_standard_ids(session, item.id)
    ]
    if any(standard.status != "active" for standard in standards):
        raise ResourceConflictError("Les éditions normatives du jeu doivent rester actives.")
    item.status = "approved"
    item.approved_at = utc_now()
    refresh_rule_set_hash(session, item)
    _audit(
        session,
        organization_id=item.organization_id,
        actor_id=actor_id,
        action="rule_set.approved",
        object_type="rule_set",
        object_id=item.id,
        details={"content_hash": item.content_hash, "rule_count": len(rules)},
    )
    return item


def validate_rule_sets_for_calculation(
    session: Session,
    organization_id: uuid.UUID,
    rule_set_ids: tuple[str, ...],
) -> list[RuleSet]:
    """Exige des jeux approuvés et privés du tenant avant la mise en file."""

    resolved: list[RuleSet] = []
    for raw_identifier in rule_set_ids:
        try:
            identifier = uuid.UUID(raw_identifier)
        except ValueError as error:
            raise InvalidInputError(
                "Un identifiant de jeu de règles n'est pas un UUID valide.",
                rule_set_id=raw_identifier,
            ) from error
        item = session.get(RuleSet, identifier)
        if item is None or item.organization_id != organization_id:
            raise InvalidInputError(
                "Le jeu de règles demandé est introuvable dans cette organisation.",
                rule_set_id=raw_identifier,
            )
        if item.status != "approved":
            raise InvalidInputError(
                "Le jeu de règles doit être approuvé avant tout calcul.",
                rule_set_id=raw_identifier,
                status=item.status,
            )
        resolved.append(item)
    return resolved


def freeze_rule_sets(
    session: Session,
    rule_sets: list[RuleSet],
) -> list[dict[str, Any]]:
    """Fige éditions et seuils applicables dans le paquet canonique du calcul."""

    manifest: list[dict[str, Any]] = []
    for rule_set in sorted(rule_sets, key=lambda item: (item.code, item.version_number)):
        standard_ids = _rule_set_standard_ids(session, rule_set.id)
        standards = [get_standard(session, identifier) for identifier in standard_ids]
        rules = session.scalars(
            select(RuleDefinition)
            .where(
                RuleDefinition.rule_set_id == rule_set.id,
                RuleDefinition.status == "approved",
            )
            .order_by(RuleDefinition.code)
        ).all()
        manifest.append(
            {
                "rule_set_id": str(rule_set.id),
                "code": rule_set.code,
                "title": rule_set.title,
                "domain": rule_set.domain,
                "country_code": rule_set.country_code,
                "version_number": rule_set.version_number,
                "content_hash": rule_set.content_hash,
                "standards": [
                    {
                        "standard_id": str(standard.id),
                        "code": standard.code,
                        "title": standard.title,
                        "issuing_body": standard.issuing_body,
                        "edition": standard.edition,
                        "publication_date": (
                            standard.publication_date.isoformat()
                            if standard.publication_date is not None
                            else None
                        ),
                        "effective_date": (
                            standard.effective_date.isoformat()
                            if standard.effective_date is not None
                            else None
                        ),
                        "licensed_copy_ref": standard.licensed_copy_ref,
                        "source_url": standard.source_url,
                        "content_hash": standard.content_hash,
                    }
                    for standard in standards
                ],
                "rules": [
                    {
                        "rule_id": str(rule.id),
                        "code": rule.code,
                        "standard_id": str(rule.standard_id) if rule.standard_id else None,
                        "title": rule.title,
                        "severity": rule.severity,
                        "domain": rule.domain,
                        "metric_path": rule.metric_path,
                        "operator": rule.operator,
                        "limit_value": rule.limit_value,
                        "upper_limit_value": rule.upper_limit_value,
                        "unit": rule.unit,
                        "applicability": rule.applicability,
                        "parameters": rule.parameters,
                        "message": rule.message,
                        "source_clause_ref": rule.source_clause_ref,
                        "status": rule.status,
                    }
                    for rule in rules
                ],
            }
        )
    return manifest


def _metric_value(result: dict[str, Any], path: str) -> float:
    current: Any = result
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    if isinstance(current, bool) or not isinstance(current, int | float):
        raise TypeError(path)
    return float(current)


def _evaluate_threshold(
    *,
    operator: str,
    limit_value: float | None,
    upper_limit_value: float | None,
    measured: float,
) -> tuple[bool, float]:
    if limit_value is None:
        raise ValueError("La règle approuvée ne porte aucune limite.")
    limit = limit_value
    if operator == "le":
        return measured <= limit, limit - measured
    if operator == "lt":
        return measured < limit, limit - measured
    if operator == "ge":
        return measured >= limit, measured - limit
    if operator == "gt":
        return measured > limit, measured - limit
    if operator == "eq":
        difference = abs(measured - limit)
        return isclose(measured, limit, rel_tol=1.0e-9, abs_tol=1.0e-12), -difference
    if operator == "between" and upper_limit_value is not None:
        return (
            limit <= measured <= upper_limit_value,
            min(measured - limit, upper_limit_value - measured),
        )
    raise ValueError("L'opérateur approuvé est incomplet ou inconnu.")


def evaluate_calculation_rules(
    session: Session,
    calculation: CalculationRun,
    result_payload: dict[str, Any],
) -> list[RuleEvaluation]:
    """Évalue les seuils approuvés sans interpréter d'expression exécutable."""

    existing = list(
        session.scalars(
            select(RuleEvaluation)
            .where(RuleEvaluation.calculation_id == calculation.id)
            .order_by(RuleEvaluation.rule_id)
        )
    )
    if existing:
        return existing
    rules_section = calculation.input_payload.get("rules", {})
    raw_ids = rules_section.get("rule_set_ids", []) if isinstance(rules_section, dict) else []
    frozen_manifest = rules_section.get("manifest", []) if isinstance(rules_section, dict) else []
    frozen_rules: list[dict[str, Any]] = []
    if isinstance(frozen_manifest, list) and frozen_manifest:
        for rule_set_entry in frozen_manifest:
            if not isinstance(rule_set_entry, dict):
                continue
            for rule_entry in rule_set_entry.get("rules", []):
                if not isinstance(rule_entry, dict) or rule_entry.get("status") != "approved":
                    continue
                frozen_rules.append(
                    {
                        **rule_entry,
                        "rule_set_id": rule_set_entry.get("rule_set_id"),
                        "rule_set_hash": rule_set_entry.get("content_hash"),
                    }
                )
    else:
        # Compatibilité des tâches mises en file avant ajout du manifeste figé.
        for raw_identifier in raw_ids:
            try:
                identifier = uuid.UUID(str(raw_identifier))
            except ValueError:
                continue
            item = session.get(RuleSet, identifier)
            if item is None or item.status not in {"approved", "archived"}:
                continue
            rules = session.scalars(
                select(RuleDefinition)
                .where(
                    RuleDefinition.rule_set_id == item.id,
                    RuleDefinition.status == "approved",
                )
                .order_by(RuleDefinition.code)
            ).all()
            frozen_rules.extend(
                {
                    "rule_set_id": str(item.id),
                    "rule_set_hash": item.content_hash,
                    "rule_id": str(rule.id),
                    "code": rule.code,
                    "severity": rule.severity,
                    "metric_path": rule.metric_path,
                    "operator": rule.operator,
                    "limit_value": rule.limit_value,
                    "upper_limit_value": rule.upper_limit_value,
                    "unit": rule.unit,
                    "message": rule.message,
                    "source_clause_ref": rule.source_clause_ref,
                    "status": rule.status,
                }
                for rule in rules
            )
    organization_id = calculation.scenario.model_version.project.organization_id
    evaluations: list[RuleEvaluation] = []
    for rule in frozen_rules:
        try:
            rule_set_id = uuid.UUID(str(rule["rule_set_id"]))
            rule_id = uuid.UUID(str(rule["rule_id"]))
            metric_path = str(rule["metric_path"])
            operator = str(rule["operator"])
            measured = _metric_value(result_payload, metric_path)
            compliant, margin = _evaluate_threshold(
                operator=operator,
                limit_value=rule.get("limit_value"),
                upper_limit_value=rule.get("upper_limit_value"),
                measured=measured,
            )
            evaluation_status = "compliant" if compliant else "non_compliant"
            message = "Contrôle conforme." if compliant else str(rule["message"])
            details: dict[str, Any] = {
                "rule_code": rule.get("code"),
                "rule_set_hash": rule.get("rule_set_hash"),
                "metric_path": metric_path,
                "operator": operator,
                "upper_limit_value": rule.get("upper_limit_value"),
                "severity": rule.get("severity"),
                "source_clause_ref": rule.get("source_clause_ref"),
            }
        except (KeyError, TypeError, ValueError) as error:
            try:
                rule_set_id = uuid.UUID(str(rule["rule_set_id"]))
                rule_id = uuid.UUID(str(rule["rule_id"]))
            except (KeyError, ValueError):
                continue
            measured = None
            margin = None
            evaluation_status = "error"
            message = "La métrique requise par la règle est absente ou invalide."
            details = {
                "rule_code": rule.get("code"),
                "rule_set_hash": rule.get("rule_set_hash"),
                "metric_path": rule.get("metric_path"),
                "error_type": type(error).__name__,
                "severity": rule.get("severity"),
                "source_clause_ref": rule.get("source_clause_ref"),
            }
        evaluation = RuleEvaluation(
            organization_id=organization_id,
            calculation_id=calculation.id,
            rule_set_id=rule_set_id,
            rule_id=rule_id,
            object_type="calculation",
            object_id=calculation.id,
            status=evaluation_status,
            measured_value=measured,
            limit_value=rule.get("limit_value"),
            margin=margin,
            unit=rule.get("unit"),
            message=message,
            details=details,
            created_at=utc_now(),
        )
        session.add(evaluation)
        evaluations.append(evaluation)
    session.flush()
    if evaluations:
        _audit(
            session,
            organization_id=organization_id,
            actor_id=None,
            action="rule_evaluation.completed",
            object_type="calculation",
            object_id=calculation.id,
            details={
                "count": len(evaluations),
                "non_compliant": sum(item.status == "non_compliant" for item in evaluations),
                "errors": sum(item.status == "error" for item in evaluations),
            },
        )
    return evaluations


def summarize_rule_evaluations(
    evaluations: list[RuleEvaluation],
) -> dict[str, Any]:
    """Produit un verdict normatif distinct du résultat physique du moteur.

    Une absence de règles n'est jamais assimilée à une conformité. Une erreur
    d'évaluation rend le verdict indéterminé. Seules les règles de sévérité
    ``blocking`` rendent directement le résultat non conforme et bloquant.
    """

    counts = {
        "total": len(evaluations),
        "compliant": sum(item.status == "compliant" for item in evaluations),
        "non_compliant": sum(item.status == "non_compliant" for item in evaluations),
        "not_applicable": sum(item.status == "not_applicable" for item in evaluations),
        "errors": sum(item.status == "error" for item in evaluations),
    }
    blocking_failures = [
        item
        for item in evaluations
        if item.details.get("severity") == "blocking" and item.status in {"non_compliant", "error"}
    ]
    reservations = [
        item
        for item in evaluations
        if item.status == "non_compliant" and item not in blocking_failures
    ]

    if not evaluations:
        status = "not_evaluated"
    elif blocking_failures:
        status = "non_compliant"
    elif counts["errors"]:
        status = "indeterminate"
    elif reservations:
        status = "compliant_with_reservations"
    else:
        status = "compliant"

    return {
        "status": status,
        "counts": counts,
        "blocking_failure_count": len(blocking_failures),
        "reservation_count": len(reservations),
        "blocking_rule_ids": [str(item.rule_id) for item in blocking_failures],
    }


def list_rule_evaluations(
    session: Session,
    organization_id: uuid.UUID,
    *,
    calculation_id: uuid.UUID | None,
    rule_set_id: uuid.UUID | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[RuleEvaluation], int]:
    conditions = [RuleEvaluation.organization_id == organization_id]
    if calculation_id is not None:
        conditions.append(RuleEvaluation.calculation_id == calculation_id)
    if rule_set_id is not None:
        conditions.append(RuleEvaluation.rule_set_id == rule_set_id)
    if status is not None:
        conditions.append(RuleEvaluation.status == status)
    total = session.scalar(select(func.count()).select_from(RuleEvaluation).where(*conditions)) or 0
    items = session.scalars(
        select(RuleEvaluation)
        .where(*conditions)
        .order_by(RuleEvaluation.created_at.desc(), RuleEvaluation.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), int(total)


def list_audit_events(
    session: Session,
    organization_id: uuid.UUID,
    *,
    action: str | None,
    object_type: str | None,
    object_id: uuid.UUID | None,
    correlation_id: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[AuditEvent], int]:
    """Filtre le journal append-only d'une organisation dans un ordre stable."""

    if session.get(Organization, organization_id) is None:
        raise ResourceNotFoundError("Organisation", organization_id)
    conditions = [AuditEvent.organization_id == organization_id]
    if action is not None:
        conditions.append(AuditEvent.action == action)
    if object_type is not None:
        conditions.append(AuditEvent.object_type == object_type)
    if object_id is not None:
        conditions.append(AuditEvent.object_id == object_id)
    if correlation_id is not None:
        conditions.append(AuditEvent.correlation_id == correlation_id)
    if created_from is not None:
        conditions.append(AuditEvent.created_at >= created_from)
    if created_to is not None:
        conditions.append(AuditEvent.created_at <= created_to)
    total = session.scalar(select(func.count()).select_from(AuditEvent).where(*conditions)) or 0
    items = session.scalars(
        select(AuditEvent)
        .where(*conditions)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), int(total)
