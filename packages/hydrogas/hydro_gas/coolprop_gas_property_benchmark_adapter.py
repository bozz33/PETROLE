"""Adaptateur P6-H pour benchmarker les propriétés gaz P6-A déjà calculées.

Cette couche lit un artefact P6-A canonique et construit des observations
comparables à des références externes explicitement fournies. Elle ne convertit
aucune unité, ne crée aucune valeur de référence et ne définit aucune tolérance.
Les critères restent soumis au protocole de benchmark pré-enregistré/APPROVED.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from hydro_gas.coolprop_gas_property_artifact import (
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
    COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION,
    CoolPropGasMixturePropertyArtifact,
)
from hydro_gas.external_benchmark import GasBenchmarkObservation


class GasMixturePropertyBenchmarkQuantity(StrEnum):
    """Grandeurs P6-A exposables à un benchmark externe sans conversion."""

    DENSITY = "density"
    COMPRESSIBILITY_FACTOR = "compressibility_factor"
    MOLAR_MASS = "molar_mass"
    SPEED_OF_SOUND = "speed_of_sound"
    GAS_CONSTANT = "gas_constant"
    EOS_PRESSURE_DENSITY_COEFFICIENT = "eos_pressure_density_coefficient"
    EOS_PRESSURE_DENSITY_SCALE = "eos_pressure_density_scale"


@dataclass(frozen=True, slots=True)
class GasMixturePropertyBenchmarkBinding:
    """Valeur externe et unité attendue pour une grandeur P6-A précise."""

    observation_id: str
    quantity: GasMixturePropertyBenchmarkQuantity
    reference_value: float
    unit: str
    reference_source_ref: str

    def __post_init__(self) -> None:
        if (
            not self.observation_id.strip()
            or not self.unit.strip()
            or not self.reference_source_ref.strip()
        ):
            raise ValueError("L'observation, son unité et sa référence externe sont obligatoires.")
        if not math.isfinite(self.reference_value):
            raise ValueError("La valeur de référence du benchmark doit être finie.")


@dataclass(frozen=True, slots=True)
class GasMixturePropertyBenchmarkObservationBundle:
    """Observations P6-H reliées à l'artefact P6-A exact."""

    property_state_ref: str
    petrole_source_ref: str
    composition_source_ref: str
    coolprop_version: str
    coolprop_gitrevision: str
    observations: tuple[GasBenchmarkObservation, ...]


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Le bloc {label} de l'artefact propriétés doit être un objet JSON.")
    return cast(dict[str, Any], value)


def _load_document(artifact: CoolPropGasMixturePropertyArtifact) -> dict[str, Any]:
    actual_sha256 = hashlib.sha256(artifact.content).hexdigest()
    if actual_sha256 != artifact.sha256:
        raise ValueError("Le SHA-256 de l'artefact propriétés ne correspond pas à son contenu.")
    try:
        decoded = json.loads(artifact.content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("L'artefact propriétés n'est pas un JSON UTF-8 valide.") from exc
    document = _mapping(decoded, label="racine")
    expected = {
        "schema_version": COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION,
        "model_id": COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
        "model_version": COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
        "property_state_ref": artifact.property_state_ref,
    }
    for field, expected_value in expected.items():
        if document.get(field) != expected_value:
            raise ValueError(
                f"L'artefact propriétés ne correspond pas au contrat attendu : {field}."
            )
    return document


_PROPERTY_FIELDS: dict[
    GasMixturePropertyBenchmarkQuantity,
    tuple[str, str, str],
] = {
    GasMixturePropertyBenchmarkQuantity.DENSITY: ("properties", "density_kg_m3", "kg/m3"),
    GasMixturePropertyBenchmarkQuantity.COMPRESSIBILITY_FACTOR: (
        "properties",
        "compressibility_factor",
        "1",
    ),
    GasMixturePropertyBenchmarkQuantity.MOLAR_MASS: (
        "properties",
        "molar_mass_kg_mol",
        "kg/mol",
    ),
    GasMixturePropertyBenchmarkQuantity.SPEED_OF_SOUND: (
        "properties",
        "speed_of_sound_m_s",
        "m/s",
    ),
    GasMixturePropertyBenchmarkQuantity.GAS_CONSTANT: (
        "properties",
        "gas_constant_j_mol_k",
        "J/(mol*K)",
    ),
    GasMixturePropertyBenchmarkQuantity.EOS_PRESSURE_DENSITY_COEFFICIENT: (
        "diagnostics",
        "eos_pressure_density_coefficient_m2_s2",
        "m2/s2",
    ),
    GasMixturePropertyBenchmarkQuantity.EOS_PRESSURE_DENSITY_SCALE: (
        "diagnostics",
        "eos_pressure_density_scale_m_s",
        "m/s",
    ),
}


def _petrole_value_and_unit(
    document: dict[str, Any],
    quantity: GasMixturePropertyBenchmarkQuantity,
) -> tuple[float, str]:
    section_name, field_name, unit = _PROPERTY_FIELDS[quantity]
    section = _mapping(document.get(section_name), label=section_name)
    value = section.get(field_name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"La valeur PETROLE de {quantity.value} doit être numérique.")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError(f"La valeur PETROLE de {quantity.value} doit être finie.")
    return numeric_value, unit


def build_coolprop_gas_property_benchmark_observations(
    artifact: CoolPropGasMixturePropertyArtifact,
    bindings: tuple[GasMixturePropertyBenchmarkBinding, ...],
) -> GasMixturePropertyBenchmarkObservationBundle:
    """Construit des observations sans valeur, unité ou seuil implicite."""

    if not bindings:
        raise ValueError("Au moins une référence externe de propriété gaz est requise.")
    observation_ids = tuple(binding.observation_id for binding in bindings)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("Les identifiants d'observations de propriétés doivent être uniques.")

    document = _load_document(artifact)
    mixture = _mapping(document.get("mixture"), label="mixture")
    runtime = _mapping(document.get("runtime"), label="runtime")
    if mixture.get("composition_source_ref") != artifact.composition_source_ref:
        raise ValueError("La provenance de composition diffère de l'enveloppe de l'artefact.")

    observations: list[GasBenchmarkObservation] = []
    for binding in bindings:
        petrole_value, expected_unit = _petrole_value_and_unit(document, binding.quantity)
        if binding.unit != expected_unit:
            raise ValueError(
                f"L'unité de référence pour {binding.quantity.value} doit être exactement {expected_unit}."
            )
        observations.append(
            GasBenchmarkObservation(
                observation_id=binding.observation_id,
                quantity_ref=f"quantity://gas/mixture-property/{binding.quantity.value}",
                location_ref=artifact.property_state_ref,
                unit=expected_unit,
                petrole_value=petrole_value,
                reference_value=binding.reference_value,
                petrole_source_ref=artifact.evidence_ref,
                reference_source_ref=binding.reference_source_ref,
            )
        )

    coolprop_version = runtime.get("coolprop_version")
    coolprop_gitrevision = runtime.get("coolprop_gitrevision")
    if not isinstance(coolprop_version, str) or not coolprop_version.strip():
        raise ValueError("La version CoolProp doit être présente dans l'artefact propriétés.")
    if not isinstance(coolprop_gitrevision, str) or not coolprop_gitrevision.strip():
        raise ValueError("La révision Git CoolProp doit être présente dans l'artefact propriétés.")

    return GasMixturePropertyBenchmarkObservationBundle(
        property_state_ref=artifact.property_state_ref,
        petrole_source_ref=artifact.evidence_ref,
        composition_source_ref=artifact.composition_source_ref,
        coolprop_version=coolprop_version,
        coolprop_gitrevision=coolprop_gitrevision,
        observations=tuple(observations),
    )


__all__ = [
    "GasMixturePropertyBenchmarkBinding",
    "GasMixturePropertyBenchmarkObservationBundle",
    "GasMixturePropertyBenchmarkQuantity",
    "build_coolprop_gas_property_benchmark_observations",
]
