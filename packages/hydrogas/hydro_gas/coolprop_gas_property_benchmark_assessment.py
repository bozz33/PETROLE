"""Évaluation P6-H gouvernée des benchmarks de propriétés gaz P6-A.

Cette couche n'invente aucun critère. Elle vérifie qu'une preuve canonique P6-H
correspond exactement au bundle d'observations, au contexte APPROVED et à la
référence externe fournis, puis délègue le calcul des erreurs au comparateur
P6-H générique. Un échec de critère reste un résultat factuel, jamais une
exception de gouvernance ni une qualification du modèle.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, cast

from hydro_gas.benchmark_protocol import ApprovedGasBenchmarkCriteria, GasBenchmarkProtocolContext
from hydro_gas.coolprop_gas_property_benchmark_adapter import (
    GasMixturePropertyBenchmarkObservationBundle,
)
from hydro_gas.coolprop_gas_property_benchmark_evidence import (
    COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
    CoolPropGasPropertyBenchmarkEvidenceArtifact,
)
from hydro_gas.external_benchmark import (
    ExternalGasBenchmarkAssessment,
    ExternalGasSolverEvidence,
    assess_external_gas_benchmark,
)


@dataclass(frozen=True, slots=True)
class CoolPropGasPropertyBenchmarkAssessmentResult:
    """Résultat quantitatif relié à la preuve et aux approvals exacts."""

    benchmark_evidence_ref: str
    context: GasBenchmarkProtocolContext
    criterion_ids: tuple[str, ...]
    approval_refs: tuple[str, ...]
    registration_refs: tuple[str, ...]
    assessment: ExternalGasBenchmarkAssessment
    qualification_claim: bool = False
    certification_claim: bool = False

    def __post_init__(self) -> None:
        if not self.benchmark_evidence_ref.strip():
            raise ValueError("La référence de preuve benchmark est obligatoire.")
        if self.qualification_claim or self.certification_claim:
            raise ValueError(
                "Une évaluation P6-H factuelle ne peut pas porter de prétention de qualification/certification."
            )


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Le bloc {label} de la preuve benchmark doit être un objet JSON.")
    return cast(dict[str, Any], value)


def _sequence(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"Le bloc {label} de la preuve benchmark doit être une liste JSON.")
    return value


def _load_evidence_document(
    artifact: CoolPropGasPropertyBenchmarkEvidenceArtifact,
) -> dict[str, Any]:
    if hashlib.sha256(artifact.content).hexdigest() != artifact.sha256:
        raise ValueError("Le SHA-256 de la preuve benchmark propriétés est invalide.")
    try:
        decoded = json.loads(artifact.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("La preuve benchmark propriétés n'est pas un JSON UTF-8 valide.") from exc
    document = _mapping(decoded, label="racine")
    if document.get("schema_version") != COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("La preuve benchmark propriétés utilise un schéma inattendu.")
    claims = _mapping(document.get("claims"), label="claims")
    if (
        claims.get("qualification_claim") is not False
        or claims.get("certification_claim") is not False
    ):
        raise ValueError("La preuve benchmark ne peut pas porter de qualification/certification.")
    return document


def _validate_context(
    document: dict[str, Any],
    context: GasBenchmarkProtocolContext,
    approved_criteria: ApprovedGasBenchmarkCriteria,
) -> None:
    if approved_criteria.context != context:
        raise ValueError("Les critères APPROVED ne correspondent pas au contexte demandé.")
    protocol = _mapping(document.get("protocol"), label="protocol")
    expected = {
        "protocol_ref": context.protocol_ref,
        "model_id": context.model_id,
        "model_version": context.model_version,
        "formulation_ref": context.formulation_ref,
        "case_ref": context.case_ref,
    }
    if protocol != expected:
        raise ValueError("La preuve benchmark ne correspond pas au contexte APPROVED exact.")


def _validate_petrole_bundle(
    document: dict[str, Any],
    bundle: GasMixturePropertyBenchmarkObservationBundle,
) -> None:
    petrole = _mapping(document.get("petrole"), label="petrole")
    expected_fields = {
        "property_state_ref": bundle.property_state_ref,
        "source_ref": bundle.petrole_source_ref,
        "composition_source_ref": bundle.composition_source_ref,
        "coolprop_version": bundle.coolprop_version,
        "coolprop_gitrevision": bundle.coolprop_gitrevision,
    }
    for field, expected_value in expected_fields.items():
        if petrole.get(field) != expected_value:
            raise ValueError(f"La preuve benchmark ne correspond pas au bundle PETROLE : {field}.")

    rows = _sequence(document.get("observations"), label="observations")
    if len(rows) != len(bundle.observations):
        raise ValueError("La preuve benchmark ne couvre pas exactement les observations runtime.")
    for row_value, observation in zip(rows, bundle.observations, strict=True):
        row = _mapping(row_value, label="observation")
        expected_row = {
            "observation_id": observation.observation_id,
            "quantity_ref": observation.quantity_ref,
            "location_ref": observation.location_ref,
            "unit": observation.unit,
            "petrole_value": observation.petrole_value,
            "reference_value": observation.reference_value,
            "petrole_source_ref": observation.petrole_source_ref,
            "reference_source_ref": observation.reference_source_ref,
        }
        if row != expected_row:
            raise ValueError(
                f"La preuve benchmark diffère de l'observation runtime {observation.observation_id}."
            )


def _validate_approved_criteria(
    document: dict[str, Any],
    approved_criteria: ApprovedGasBenchmarkCriteria,
) -> None:
    rows = _sequence(document.get("criteria"), label="criteria")
    if len(rows) != len(approved_criteria.criteria):
        raise ValueError("La preuve benchmark ne couvre pas exactement les critères APPROVED.")
    if not (
        len(approved_criteria.criteria)
        == len(approved_criteria.criterion_ids)
        == len(approved_criteria.approval_refs)
        == len(approved_criteria.registration_refs)
    ):
        raise ValueError("Les preuves des critères APPROVED sont désalignées.")

    for row_value, criterion_id, criterion, approval_ref, registration_ref in zip(
        rows,
        approved_criteria.criterion_ids,
        approved_criteria.criteria,
        approved_criteria.approval_refs,
        approved_criteria.registration_refs,
        strict=True,
    ):
        row = _mapping(row_value, label="criterion")
        expected_row = {
            "criterion_id": criterion_id,
            "observation_id": criterion.observation_id,
            "maximum_absolute_error": criterion.maximum_absolute_error,
            "maximum_relative_error_fraction": criterion.maximum_relative_error_fraction,
            "criterion_source_ref": criterion.source_ref,
            "approval_ref": approval_ref,
            "registration_ref": registration_ref,
        }
        if row != expected_row:
            raise ValueError(f"La preuve benchmark diffère du critère APPROVED {criterion_id}.")


def _validate_external_reference(
    document: dict[str, Any],
    external_solver: ExternalGasSolverEvidence,
) -> None:
    reference = _mapping(document.get("reference"), label="reference")
    if reference.get("system_ref") != external_solver.source_ref:
        raise ValueError("La preuve benchmark ne correspond pas à la référence externe fournie.")
    if reference.get("input_sha256") != external_solver.input_sha256:
        raise ValueError("Le hash d'entrée de la référence externe diffère de la preuve.")
    if reference.get("output_sha256") != external_solver.output_sha256:
        raise ValueError("Le hash de sortie de la référence externe diffère de la preuve.")


def assess_coolprop_gas_property_benchmark_evidence(
    artifact: CoolPropGasPropertyBenchmarkEvidenceArtifact,
    bundle: GasMixturePropertyBenchmarkObservationBundle,
    approved_criteria: ApprovedGasBenchmarkCriteria,
    context: GasBenchmarkProtocolContext,
    *,
    campaign_ref: str,
    petrole_engine_version: str,
    external_solver: ExternalGasSolverEvidence,
) -> CoolPropGasPropertyBenchmarkAssessmentResult:
    """Évalue uniquement une chaîne de preuve P6-H intégralement cohérente."""

    document = _load_evidence_document(artifact)
    _validate_context(document, context, approved_criteria)
    _validate_petrole_bundle(document, bundle)
    _validate_approved_criteria(document, approved_criteria)
    _validate_external_reference(document, external_solver)

    assessment = assess_external_gas_benchmark(
        campaign_ref=campaign_ref,
        protocol_ref=context.protocol_ref,
        petrole_engine_version=petrole_engine_version,
        external_solver=external_solver,
        observations=bundle.observations,
        criteria=approved_criteria.criteria,
    )
    return CoolPropGasPropertyBenchmarkAssessmentResult(
        benchmark_evidence_ref=artifact.evidence_ref,
        context=context,
        criterion_ids=approved_criteria.criterion_ids,
        approval_refs=approved_criteria.approval_refs,
        registration_refs=approved_criteria.registration_refs,
        assessment=assessment,
    )


__all__ = [
    "CoolPropGasPropertyBenchmarkAssessmentResult",
    "assess_coolprop_gas_property_benchmark_evidence",
]
