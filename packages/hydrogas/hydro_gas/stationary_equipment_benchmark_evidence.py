"""Artefact canonique P6-H reliant les preuves du benchmark gaz mixte.

L'artefact établit une chaîne de traçabilité entre un résultat PETROLE, un run
externe et les critères explicitement approuvés. Il n'évalue pas les erreurs,
ne décide pas PASS/FAIL et ne transforme jamais une preuve en qualification.
"""

from __future__ import annotations

import hashlib
import json
import string
from dataclasses import dataclass

from hydro_gas.benchmark_protocol import ApprovedGasBenchmarkCriteria
from hydro_gas.stationary_equipment_benchmark_adapter import (
    StationaryEquipmentBenchmarkObservationBundle,
)

STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION = (
    "phase6/stationary-equipment-benchmark-evidence/3"
)


@dataclass(frozen=True, slots=True)
class StationaryEquipmentBenchmarkEvidenceArtifact:
    """JSON canonique et empreinte de la chaîne de preuve du benchmark mixte."""

    schema_version: str
    content: bytes
    sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("Version de schéma de preuve benchmark mixte non supportée.")
        if hashlib.sha256(self.content).hexdigest() != self.sha256:
            raise ValueError(
                "L'empreinte de la preuve benchmark mixte ne correspond pas au contenu."
            )
        try:
            document = json.loads(self.content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "La preuve benchmark mixte doit contenir un objet JSON valide."
            ) from exc
        if not isinstance(document, dict):
            raise ValueError("La preuve benchmark mixte doit contenir un objet JSON.")
        if document.get("schema_version") != self.schema_version:
            raise ValueError("Le schéma interne de la preuve benchmark mixte est incohérent.")


def _validate_sha256(value: str, *, label: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in string.hexdigits for character in normalized):
        raise ValueError(f"{label} doit être un SHA-256 hexadécimal de 64 caractères.")
    return normalized


def export_stationary_equipment_benchmark_evidence(
    bundle: StationaryEquipmentBenchmarkObservationBundle,
    approved_criteria: ApprovedGasBenchmarkCriteria,
    *,
    case_ref: str,
    formulation_ref: str,
    petrole_result_sha256: str,
    external_solver_ref: str,
    external_input_sha256: str,
    external_output_sha256: str,
    evidence_source_ref: str,
    review_ref: str | None = None,
) -> StationaryEquipmentBenchmarkEvidenceArtifact:
    """Fige les identités de comparaison sans recalculer les résultats."""

    required_refs = (
        case_ref,
        formulation_ref,
        external_solver_ref,
        evidence_source_ref,
        approved_criteria.protocol_ref,
        approved_criteria.model_id,
        approved_criteria.model_version,
        approved_criteria.case_ref,
        approved_criteria.formulation_ref,
        bundle.solve_ref,
        bundle.petrole_source_ref,
    )
    if any(not value.strip() for value in required_refs):
        raise ValueError("Toutes les références de la preuve benchmark mixte sont obligatoires.")
    if review_ref is not None and not review_ref.strip():
        raise ValueError("Une référence de revue fournie ne peut pas être vide.")
    if case_ref.strip() != approved_criteria.case_ref:
        raise ValueError("Le cas du benchmark ne correspond pas au contexte APPROVED.")
    if formulation_ref.strip() != approved_criteria.formulation_ref:
        raise ValueError("La formulation du benchmark ne correspond pas au contexte APPROVED.")

    observation_ids = tuple(item.observation_id for item in bundle.observations)
    if not observation_ids:
        raise ValueError("La preuve benchmark mixte exige au moins une observation.")
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("Les observations de la preuve benchmark mixte doivent être uniques.")

    criterion_observation_ids = tuple(
        criterion.observation_id for criterion in approved_criteria.criteria
    )
    if len(criterion_observation_ids) != len(set(criterion_observation_ids)):
        raise ValueError("Les critères approuvés doivent viser des observations uniques.")
    if set(criterion_observation_ids) != set(observation_ids):
        raise ValueError(
            "Les critères APPROVED doivent couvrir exactement les observations du benchmark mixte."
        )

    criterion_count = len(approved_criteria.criterion_ids)
    if not (
        criterion_count
        == len(approved_criteria.approval_refs)
        == len(approved_criteria.registration_refs)
        == len(approved_criteria.criteria)
    ):
        raise ValueError("Les preuves de critères APPROVED sont incomplètes ou désalignées.")

    document = {
        "schema_version": STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
        "protocol_ref": approved_criteria.protocol_ref,
        "model_id": approved_criteria.model_id,
        "model_version": approved_criteria.model_version,
        "case_ref": approved_criteria.case_ref,
        "formulation_ref": approved_criteria.formulation_ref,
        "petrole": {
            "solve_ref": bundle.solve_ref,
            "solver_status": bundle.solver_status.value,
            "source_ref": bundle.petrole_source_ref,
            "result_sha256": _validate_sha256(
                petrole_result_sha256,
                label="Le hash du résultat PETROLE",
            ),
        },
        "external": {
            "solver_ref": external_solver_ref.strip(),
            "input_sha256": _validate_sha256(
                external_input_sha256,
                label="Le hash d'entrée du solveur externe",
            ),
            "output_sha256": _validate_sha256(
                external_output_sha256,
                label="Le hash de sortie du solveur externe",
            ),
        },
        "observations": [
            {
                "observation_id": item.observation_id,
                "quantity_ref": item.quantity_ref,
                "location_ref": item.location_ref,
                "unit": item.unit,
                "petrole_value": item.petrole_value,
                "reference_value": item.reference_value,
                "petrole_source_ref": item.petrole_source_ref,
                "reference_source_ref": item.reference_source_ref,
            }
            for item in bundle.observations
        ],
        "criteria": [
            {
                "criterion_id": criterion_id,
                "observation_id": runtime_criterion.observation_id,
                "maximum_absolute_error": runtime_criterion.maximum_absolute_error,
                "maximum_relative_error_fraction": (
                    runtime_criterion.maximum_relative_error_fraction
                ),
                "criterion_source_ref": runtime_criterion.source_ref,
                "approval_ref": approval_ref,
                "registration_ref": registration_ref,
            }
            for criterion_id, runtime_criterion, approval_ref, registration_ref in zip(
                approved_criteria.criterion_ids,
                approved_criteria.criteria,
                approved_criteria.approval_refs,
                approved_criteria.registration_refs,
                strict=True,
            )
        ],
        "review_ref": review_ref.strip() if review_ref is not None else None,
        "evidence_source_ref": evidence_source_ref.strip(),
        "qualification_claim": False,
        "certification_claim": False,
    }
    content = json.dumps(
        document,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return StationaryEquipmentBenchmarkEvidenceArtifact(
        schema_version=STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


__all__ = [
    "STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION",
    "StationaryEquipmentBenchmarkEvidenceArtifact",
    "export_stationary_equipment_benchmark_evidence",
]
