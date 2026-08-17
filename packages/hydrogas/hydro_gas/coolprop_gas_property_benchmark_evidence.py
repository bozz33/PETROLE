"""Artefact canonique P6-H pour la chaîne de preuve des propriétés gaz P6-A.

Cette couche fige les identités, hashes, observations et critères APPROVED d'un
benchmark de propriétés déjà préparé. Elle ne calcule aucune propriété, ne
compare aucune valeur, ne crée aucune tolérance et ne décide jamais PASS/FAIL.
"""

from __future__ import annotations

import hashlib
import json
import string
from dataclasses import dataclass
from typing import Any, cast

from hydro_gas.benchmark_protocol import ApprovedGasBenchmarkCriteria, GasBenchmarkProtocolContext
from hydro_gas.coolprop_gas_property_artifact import (
    COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
)
from hydro_gas.coolprop_gas_property_benchmark_adapter import (
    GasMixturePropertyBenchmarkObservationBundle,
)

COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION = (
    "phase6/coolprop-gas-property-benchmark-evidence/1"
)
COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_REF_PREFIX = (
    "sha256://petrole/gas/coolprop-mixture-property-benchmark-evidence/"
)


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"Le bloc {label} de la preuve benchmark propriétés doit être un objet JSON."
        )
    return cast(dict[str, Any], value)


def _validate_sha256(value: str, *, label: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in string.hexdigits for character in normalized):
        raise ValueError(f"{label} doit être un SHA-256 hexadécimal de 64 caractères.")
    return normalized


@dataclass(frozen=True, slots=True)
class CoolPropGasPropertyBenchmarkEvidenceArtifact:
    """Document canonique auto-vérifiable de la chaîne de preuve P6-A/P6-H."""

    schema_version: str
    content: bytes
    sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("Version de schéma de preuve benchmark propriétés non supportée.")
        if hashlib.sha256(self.content).hexdigest() != self.sha256:
            raise ValueError(
                "L'empreinte de la preuve benchmark propriétés ne correspond pas au contenu."
            )
        try:
            decoded = json.loads(self.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "La preuve benchmark propriétés doit contenir un JSON UTF-8 valide."
            ) from exc
        document = _mapping(decoded, label="racine")
        if document.get("schema_version") != self.schema_version:
            raise ValueError("Le schéma interne de la preuve benchmark propriétés est incohérent.")
        claims = _mapping(document.get("claims"), label="claims")
        if claims.get("qualification_claim") is not False:
            raise ValueError("La preuve benchmark propriétés ne peut pas qualifier le modèle.")
        if claims.get("certification_claim") is not False:
            raise ValueError("La preuve benchmark propriétés ne peut pas certifier le modèle.")

    @property
    def evidence_ref(self) -> str:
        return f"{COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_REF_PREFIX}{self.sha256}"


def _property_artifact_sha256(bundle: GasMixturePropertyBenchmarkObservationBundle) -> str:
    if not bundle.petrole_source_ref.startswith(COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX):
        raise ValueError(
            "La source PETROLE du benchmark propriétés doit référencer l'artefact P6-A canonique."
        )
    value = bundle.petrole_source_ref.removeprefix(
        COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX
    )
    return _validate_sha256(value, label="Le hash de l'artefact propriétés PETROLE")


def export_coolprop_gas_property_benchmark_evidence(
    bundle: GasMixturePropertyBenchmarkObservationBundle,
    approved_criteria: ApprovedGasBenchmarkCriteria,
    context: GasBenchmarkProtocolContext,
    *,
    reference_system_ref: str,
    reference_input_sha256: str,
    reference_output_sha256: str,
    evidence_source_ref: str,
    review_ref: str | None = None,
) -> CoolPropGasPropertyBenchmarkEvidenceArtifact:
    """Fige une comparaison préparée sans recalcul ni verdict scientifique."""

    required_refs = (
        context.protocol_ref,
        context.model_id,
        context.model_version,
        context.formulation_ref,
        context.case_ref,
        bundle.property_state_ref,
        bundle.petrole_source_ref,
        bundle.composition_source_ref,
        bundle.coolprop_version,
        bundle.coolprop_gitrevision,
        reference_system_ref,
        evidence_source_ref,
    )
    if any(not value.strip() for value in required_refs):
        raise ValueError(
            "Toutes les références de la preuve benchmark propriétés sont obligatoires."
        )
    if review_ref is not None and not review_ref.strip():
        raise ValueError("Une référence de revue fournie ne peut pas être vide.")
    if context.protocol_ref != approved_criteria.protocol_ref:
        raise ValueError("Les critères APPROVED ne correspondent pas au protocole demandé.")
    if context.model_id != COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID:
        raise ValueError("Le contexte de benchmark ne correspond pas au modèle de propriétés P6-A.")
    if context.model_version != COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION:
        raise ValueError("Le contexte de benchmark ne correspond pas à la version du modèle P6-A.")
    if approved_criteria.context != context:
        raise ValueError(
            "Les critères APPROVED ne correspondent pas au contexte complet du benchmark."
        )

    property_artifact_sha256 = _property_artifact_sha256(bundle)
    observation_ids = tuple(item.observation_id for item in bundle.observations)
    if not observation_ids:
        raise ValueError("La preuve benchmark propriétés exige au moins une observation.")
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("Les observations de la preuve benchmark propriétés doivent être uniques.")
    for observation in bundle.observations:
        if observation.location_ref != bundle.property_state_ref:
            raise ValueError("Une observation ne correspond pas à l'état de propriétés du bundle.")
        if observation.petrole_source_ref != bundle.petrole_source_ref:
            raise ValueError("Une observation ne correspond pas à l'artefact PETROLE du bundle.")

    criterion_observation_ids = tuple(
        criterion.observation_id for criterion in approved_criteria.criteria
    )
    if len(criterion_observation_ids) != len(set(criterion_observation_ids)):
        raise ValueError("Les critères APPROVED doivent viser des observations uniques.")
    if set(criterion_observation_ids) != set(observation_ids):
        raise ValueError(
            "Les critères APPROVED doivent couvrir exactement les observations de propriétés."
        )
    criterion_count = len(approved_criteria.criterion_ids)
    if not (
        criterion_count
        == len(approved_criteria.approval_refs)
        == len(approved_criteria.registration_refs)
        == len(approved_criteria.criteria)
    ):
        raise ValueError("Les preuves de critères APPROVED sont incomplètes ou désalignées.")

    document: dict[str, Any] = {
        "schema_version": COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
        "protocol": {
            "protocol_ref": context.protocol_ref,
            "model_id": context.model_id,
            "model_version": context.model_version,
            "formulation_ref": context.formulation_ref,
            "case_ref": context.case_ref,
        },
        "petrole": {
            "property_state_ref": bundle.property_state_ref,
            "source_ref": bundle.petrole_source_ref,
            "property_artifact_sha256": property_artifact_sha256,
            "composition_source_ref": bundle.composition_source_ref,
            "coolprop_version": bundle.coolprop_version,
            "coolprop_gitrevision": bundle.coolprop_gitrevision,
        },
        "reference": {
            "system_ref": reference_system_ref.strip(),
            "input_sha256": _validate_sha256(
                reference_input_sha256,
                label="Le hash d'entrée de la référence externe",
            ),
            "output_sha256": _validate_sha256(
                reference_output_sha256,
                label="Le hash de sortie de la référence externe",
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
        "claims": {
            "qualification_claim": False,
            "certification_claim": False,
        },
    }
    content = json.dumps(
        document,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return CoolPropGasPropertyBenchmarkEvidenceArtifact(
        schema_version=COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


__all__ = [
    "COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_REF_PREFIX",
    "COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION",
    "CoolPropGasPropertyBenchmarkEvidenceArtifact",
    "export_coolprop_gas_property_benchmark_evidence",
]
