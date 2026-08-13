"""Artefacts canoniques de paramètres Weymouth-SI pour P6-B.

Le module transforme un jeu de paramètres déjà validé structurellement en JSON
canonique hashé. Il ne déduit aucun paramètre, ne charge aucune donnée externe
et ne qualifie pas le modèle scientifique.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from hydro_gas.constitutive_models import (
    GasConstitutiveQualification,
    GasPipeConstitutiveBinding,
    GasPipeConstitutiveModelDescriptor,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters

WEYMOUTH_SI_MODEL_ID = "weymouth-si"
WEYMOUTH_SI_MODEL_VERSION = "gasmodels-0.13.4-reference-v1"
WEYMOUTH_SI_PARAMETER_SCHEMA_VERSION = "phase6/weymouth-si-parameters/1"
WEYMOUTH_SI_SOURCE_COMMIT = "21422f18e7e328732ec8edd7995446d33f58e789"


@dataclass(frozen=True, slots=True)
class WeymouthSiParameterArtifact:
    """JSON canonique et empreinte d'un jeu de paramètres d'une conduite."""

    parameter_set_ref: str
    pipe_id: str
    geometry_ref: str
    gas_property_ref: str
    content: bytes
    sha256: str


def export_weymouth_si_parameter_artifact(
    parameters: WeymouthSiPipeParameters,
    *,
    parameter_set_ref: str,
    geometry_ref: str,
    gas_property_ref: str,
) -> WeymouthSiParameterArtifact:
    """Sérialise les paramètres sans conversion, arrondi ni valeur implicite."""

    references = (parameter_set_ref, geometry_ref, gas_property_ref)
    if any(not value.strip() for value in references):
        raise ValueError(
            "Les références du jeu de paramètres, de géométrie et de propriétés gaz sont obligatoires."
        )

    document = {
        "schema_version": WEYMOUTH_SI_PARAMETER_SCHEMA_VERSION,
        "unit_system": "SI",
        "pipe_id": parameters.pipe_id,
        "length_m": parameters.length_m,
        "diameter_m": parameters.diameter_m,
        "friction_factor": parameters.friction_factor,
        "sound_speed_m_s": parameters.sound_speed_m_s,
        "equation_ref": parameters.equation_ref,
        "parameter_source_ref": parameters.parameter_source_ref,
        "geometry_ref": geometry_ref,
        "gas_property_ref": gas_property_ref,
    }
    content = json.dumps(
        document,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return WeymouthSiParameterArtifact(
        parameter_set_ref=parameter_set_ref,
        pipe_id=parameters.pipe_id,
        geometry_ref=geometry_ref,
        gas_property_ref=gas_property_ref,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def build_weymouth_si_binding(
    artifact: WeymouthSiParameterArtifact,
    *,
    source_ref: str,
) -> GasPipeConstitutiveBinding:
    """Construit le binding générique sans recopier ni recalculer les paramètres."""

    if not source_ref.strip():
        raise ValueError("La provenance du binding constitutif est obligatoire.")
    return GasPipeConstitutiveBinding(
        pipe_id=artifact.pipe_id,
        model_id=WEYMOUTH_SI_MODEL_ID,
        model_version=WEYMOUTH_SI_MODEL_VERSION,
        parameter_set_ref=artifact.parameter_set_ref,
        parameter_set_sha256=artifact.sha256,
        geometry_ref=artifact.geometry_ref,
        gas_property_ref=artifact.gas_property_ref,
        source_ref=source_ref,
    )


def weymouth_si_reference_descriptor() -> GasPipeConstitutiveModelDescriptor:
    """Décrit la formulation réellement implémentée sans la déclarer benchmarked."""

    equation_ref = (
        "GasModels.jl/docs/src/math-model.md@"
        f"{WEYMOUTH_SI_SOURCE_COMMIT}#steady-state-weymouth"
    )
    return GasPipeConstitutiveModelDescriptor(
        model_id=WEYMOUTH_SI_MODEL_ID,
        version=WEYMOUTH_SI_MODEL_VERSION,
        formulation_ref=equation_ref,
        equation_ref=equation_ref,
        source_ref=f"GasModels.jl@{WEYMOUTH_SI_SOURCE_COMMIT}",
        parameter_schema_ref=(
            "docs/implementation/phase6_p6b_weymouth_parameter_artifact.md#schema-v1"
        ),
        domain_refs=(
            "docs/implementation/phase6_p6b_weymouth_si_residual.md#6-limites-et-hypotheses",
        ),
        assumptions=(
            "steady-state",
            "one-dimensional-pipe",
            "constant-cross-section",
            "constant-mass-flow-along-pipe",
            "equation-of-state-p-equals-a-squared-rho",
            "explicit-friction-factor",
        ),
        qualification=GasConstitutiveQualification.BENCHMARK_READY,
    )


__all__ = [
    "WEYMOUTH_SI_MODEL_ID",
    "WEYMOUTH_SI_MODEL_VERSION",
    "WEYMOUTH_SI_PARAMETER_SCHEMA_VERSION",
    "WeymouthSiParameterArtifact",
    "build_weymouth_si_binding",
    "export_weymouth_si_parameter_artifact",
    "weymouth_si_reference_descriptor",
]
