"""Adaptateur P6-F entre l'export thermo P6-G et la sélection énergétique.

La sélection énergétique ne connaît aucune limite constructeur. Elle reçoit
uniquement une preuve booléenne dérivée d'un export P6-G canonique dont
l'intégrité, le calcul source et les approvals thermo ont été vérifiés ici.
Toute évaluation thermo non évaluable est convertie en contrainte échouée
(fail-closed), jamais en faisabilité implicite.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast

from hydro_gas.energy_optimization import GasDispatchConstraintEvidence
from hydro_gas.result_export import GasResultExportArtifact
from hydro_gas.stationary_compressor_thermodynamic_limits import (
    StationaryActiveCompressorThermodynamicLimitAssessment,
)
from hydro_gas.stationary_thermodynamic_result_export import (
    STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION,
    STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION,
)

THERMODYNAMIC_LIMIT_DISPATCH_CONSTRAINT_ID = "stationary-compressor-thermodynamic-approved-limits"
THERMODYNAMIC_LIMIT_EVIDENCE_REF_PREFIX = (
    "sha256://petrole/gas/stationary-compressor-thermodynamics/"
)


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Le bloc {label} de la preuve thermodynamique doit être un objet JSON.")
    return cast(dict[str, Any], value)


def _validate_export_integrity(artifact: GasResultExportArtifact) -> dict[str, Any]:
    if artifact.media_type != "application/json":
        raise ValueError("La preuve thermodynamique P6-F doit être un export JSON canonique.")
    actual_sha256 = hashlib.sha256(artifact.content).hexdigest()
    if actual_sha256 != artifact.sha256:
        raise ValueError("Le SHA-256 de l'export thermodynamique ne correspond pas à son contenu.")
    try:
        decoded = json.loads(artifact.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("L'export thermodynamique n'est pas un JSON UTF-8 valide.") from exc
    return _mapping(decoded, label="racine")


def _validate_compressor_limit_rows(
    rows_value: Any,
    assessment: StationaryActiveCompressorThermodynamicLimitAssessment,
) -> None:
    if not isinstance(rows_value, list):
        raise ValueError("La preuve thermo doit contenir une liste de limites par compresseur.")
    rows = tuple(_mapping(row, label="limite compresseur") for row in rows_value)
    row_ids = tuple(row.get("compressor_id") for row in rows)
    if any(
        not isinstance(compressor_id, str) or not compressor_id.strip() for compressor_id in row_ids
    ):
        raise ValueError("Chaque ligne de limite thermo exportée doit identifier son compresseur.")
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("Les compresseurs de la preuve thermo exportée doivent être uniques.")

    expected_by_id = {item.compressor_id: item for item in assessment.compressors}
    if set(row_ids) != set(expected_by_id):
        raise ValueError(
            "La preuve thermo exportée doit couvrir exactement les compresseurs évalués."
        )

    for row in rows:
        compressor_id = cast(str, row["compressor_id"])
        expected = expected_by_id[compressor_id]
        exact_fields = {
            "solver_status": expected.solver_status.value,
            "limit_set_id": expected.limit_set_id,
            "limit_set_version": expected.limit_set_version,
            "all_approved_limits_passed": expected.all_approved_limits_passed,
            "source_ref": expected.source_ref,
            "registration_ref": expected.registration_ref,
            "approval_ref": expected.approval_ref,
            "qualification_claim": False,
            "certification_claim": False,
        }
        for field, expected_value in exact_fields.items():
            if row.get(field) != expected_value:
                raise ValueError(
                    f"La preuve thermo exportée ne correspond pas à l'évaluation pour {compressor_id}: {field}."
                )


def build_thermodynamic_limit_dispatch_constraint_evidence(
    assessment: StationaryActiveCompressorThermodynamicLimitAssessment,
    artifact: GasResultExportArtifact,
) -> GasDispatchConstraintEvidence:
    """Transforme une preuve P6-G vérifiée en contrainte P6-F fail-closed."""

    document = _validate_export_integrity(artifact)
    if document.get("export_version") != STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION:
        raise ValueError("L'export ne correspond pas à la version thermo P6-G attendue.")
    if document.get("model_version") != STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION:
        raise ValueError("L'export ne correspond pas au modèle thermo P6-G attendu.")
    if document.get("calculation_ref") != assessment.solve_ref:
        raise ValueError("La preuve thermo P6-G ne correspond pas au calcul évalué.")

    diagnostics = _mapping(document.get("diagnostics"), label="diagnostics")
    limits = _mapping(diagnostics.get("thermodynamic_limits"), label="thermodynamic_limits")
    if limits.get("solver_status") != assessment.solver_status.value:
        raise ValueError("Le statut solveur de la preuve thermo diffère de l'évaluation source.")
    if limits.get("all_limits_evaluable") is not assessment.all_limits_evaluable:
        raise ValueError("L'évaluabilité thermo exportée diffère de l'évaluation source.")
    if limits.get("all_approved_limits_passed") is not assessment.all_approved_limits_passed:
        raise ValueError("Le verdict thermo exporté diffère de l'évaluation source.")
    if (
        limits.get("qualification_claim") is not False
        or limits.get("certification_claim") is not False
    ):
        raise ValueError(
            "Une preuve P6-F ne peut pas porter de prétention de qualification/certification."
        )

    _validate_compressor_limit_rows(limits.get("compressors"), assessment)

    passed = assessment.all_limits_evaluable and assessment.all_approved_limits_passed is True
    return GasDispatchConstraintEvidence(
        constraint_id=THERMODYNAMIC_LIMIT_DISPATCH_CONSTRAINT_ID,
        passed=passed,
        evidence_ref=f"{THERMODYNAMIC_LIMIT_EVIDENCE_REF_PREFIX}{artifact.sha256}",
    )


__all__ = [
    "THERMODYNAMIC_LIMIT_DISPATCH_CONSTRAINT_ID",
    "THERMODYNAMIC_LIMIT_EVIDENCE_REF_PREFIX",
    "build_thermodynamic_limit_dispatch_constraint_evidence",
]
