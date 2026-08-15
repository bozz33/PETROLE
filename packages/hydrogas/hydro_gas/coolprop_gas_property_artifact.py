"""Artefact canonique P6-A pour un état de propriétés gaz CoolProp déjà évalué.

L'artefact fige l'état P/T, la composition, le mapping, l'identité runtime de
CoolProp et les propriétés calculées. Il ne transforme aucune propriété en
paramètre Weymouth/line-pack et ne porte aucune prétention de qualification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, cast

from hydro_gas.coolprop_gas_properties import CoolPropGasMixturePropertyResult

COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION = "phase6/coolprop-gas-mixture-properties/1"
COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID = "coolprop-explicit-mixture-properties"
COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION = "abstractstate-pt-runtime-v1"
COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX = (
    "sha256://petrole/gas/coolprop-mixture-properties/"
)


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Le bloc {label} de l'artefact propriétés doit être un objet JSON.")
    return cast(dict[str, Any], value)


@dataclass(frozen=True, slots=True)
class CoolPropGasMixturePropertyArtifact:
    """Document JSON canonique auto-vérifiable par SHA-256."""

    schema_version: str
    model_id: str
    model_version: str
    property_state_ref: str
    composition_source_ref: str
    mixture_definition_source_ref: str
    content: bytes
    sha256: str

    def __post_init__(self) -> None:
        refs = (
            self.schema_version,
            self.model_id,
            self.model_version,
            self.property_state_ref,
            self.composition_source_ref,
            self.mixture_definition_source_ref,
            self.sha256,
        )
        if any(not value.strip() for value in refs):
            raise ValueError("L'artefact de propriétés gaz doit être entièrement référencé.")
        actual_sha256 = hashlib.sha256(self.content).hexdigest()
        if actual_sha256 != self.sha256:
            raise ValueError("Le SHA-256 de l'artefact propriétés ne correspond pas au contenu.")
        try:
            decoded = json.loads(self.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("L'artefact propriétés doit contenir un JSON UTF-8 valide.") from exc
        document = _mapping(decoded, label="racine")
        exact = {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "property_state_ref": self.property_state_ref,
        }
        for field, expected in exact.items():
            if document.get(field) != expected:
                raise ValueError(f"Le champ {field} ne correspond pas à l'enveloppe de l'artefact.")
        mixture = _mapping(document.get("mixture"), label="mixture")
        if mixture.get("composition_source_ref") != self.composition_source_ref:
            raise ValueError("La provenance de composition diffère de l'enveloppe de l'artefact.")
        if mixture.get("mixture_definition_source_ref") != self.mixture_definition_source_ref:
            raise ValueError(
                "La provenance de définition mélange diffère de l'enveloppe de l'artefact."
            )
        claims = _mapping(document.get("claims"), label="claims")
        if claims.get("qualification_claim") is not False:
            raise ValueError("L'artefact P6-A ne peut pas porter de prétention de qualification.")
        if claims.get("certification_claim") is not False:
            raise ValueError("L'artefact P6-A ne peut pas porter de prétention de certification.")

    @property
    def evidence_ref(self) -> str:
        return f"{COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX}{self.sha256}"


def export_coolprop_gas_mixture_property_artifact(
    result: CoolPropGasMixturePropertyResult,
    *,
    property_state_ref: str,
) -> CoolPropGasMixturePropertyArtifact:
    """Fige un résultat P6-A déjà calculé sans le réévaluer."""

    normalized_state_ref = property_state_ref.strip()
    if not normalized_state_ref:
        raise ValueError("La référence de l'état de propriétés est obligatoire.")
    if result.qualification_claim or result.certification_claim:
        raise ValueError(
            "Un résultat portant une prétention de qualification/certification ne peut pas être exporté."
        )

    document: dict[str, Any] = {
        "schema_version": COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION,
        "model_id": COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
        "model_version": COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
        "property_state_ref": normalized_state_ref,
        "state": {
            "temperature_k": result.temperature_k,
            "pressure_pa": result.pressure_pa,
            "state_source_ref": result.state_source_ref,
            "envelope_source_ref": result.envelope_source_ref,
        },
        "mixture": {
            "fluid_name": result.fluid_name,
            "coolprop_backend": result.coolprop_backend,
            "composition_source_ref": result.composition_source_ref,
            "component_mapping_source_ref": result.component_mapping_source_ref,
            "composition_component_names": list(result.composition_component_names),
            "coolprop_component_names": list(result.coolprop_component_names),
            "mole_fractions": list(result.mole_fractions),
            "mixture_definition_source_ref": result.mixture_definition_source_ref,
        },
        "runtime": {
            "coolprop_version": result.coolprop_version,
            "coolprop_gitrevision": result.coolprop_gitrevision,
            "property_method_ref": result.property_method_ref,
        },
        "properties": {
            "density_kg_m3": result.density_kg_m3,
            "compressibility_factor": result.compressibility_factor,
            "molar_mass_kg_mol": result.molar_mass_kg_mol,
            "speed_of_sound_m_s": result.speed_of_sound_m_s,
            "gas_constant_j_mol_k": result.gas_constant_j_mol_k,
        },
        "diagnostics": {
            "declared_composition_molar_mass_kg_mol": (
                result.declared_composition_molar_mass_kg_mol
            ),
            "molar_mass_residual_kg_mol": result.molar_mass_residual_kg_mol,
            "eos_pressure_density_coefficient_m2_s2": (
                result.eos_pressure_density_coefficient_m2_s2
            ),
            "eos_pressure_density_scale_m_s": result.eos_pressure_density_scale_m_s,
            "density_from_eos_kg_m3": result.density_from_eos_kg_m3,
            "density_eos_residual_kg_m3": result.density_eos_residual_kg_m3,
        },
        "claims": {
            "qualification_claim": False,
            "certification_claim": False,
        },
    }
    content = _canonical_json(document)
    sha256 = hashlib.sha256(content).hexdigest()
    return CoolPropGasMixturePropertyArtifact(
        schema_version=COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION,
        model_id=COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
        model_version=COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
        property_state_ref=normalized_state_ref,
        composition_source_ref=result.composition_source_ref,
        mixture_definition_source_ref=result.mixture_definition_source_ref,
        content=content,
        sha256=sha256,
    )


__all__ = [
    "COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX",
    "COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID",
    "COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION",
    "COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION",
    "CoolPropGasMixturePropertyArtifact",
    "export_coolprop_gas_mixture_property_artifact",
]
