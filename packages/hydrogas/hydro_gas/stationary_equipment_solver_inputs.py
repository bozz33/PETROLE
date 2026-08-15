"""Artefacts approuvables d'échelle et d'initialisation du problème gaz mixte.

Les valeurs sont explicites, versionnées et liées au layout exact. Cette couche
n'en déduit aucune et ne lance aucun solveur.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from hydro_gas.stationary_equipment_candidate import (
    StationaryActiveCompressorUnknownState,
    materialize_stationary_active_compressor_candidate,
)
from hydro_gas.stationary_equipment_numerics import StationaryActiveCompressorNumericalScale
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryActiveCompressorUnknownLayout,
)
from hydro_gas.stationary_solver_governance import StationarySolverPolicyState


def stationary_active_compressor_layout_sha256(
    layout: StationaryActiveCompressorUnknownLayout,
) -> str:
    """Empreinte canonique de l'ordre exact des inconnues et équations mixtes."""

    payload = {
        "connected_components": [list(component) for component in layout.connected_components],
        "fixed_pressure_node_ids": list(layout.fixed_pressure_node_ids),
        "unknown_pressure_node_ids": list(layout.unknown_pressure_node_ids),
        "pipe_flow_ids": list(layout.pipe_flow_ids),
        "compressor_flow_ids": list(layout.compressor_flow_ids),
        "slack_external_flow_node_ids": list(layout.slack_external_flow_node_ids),
        "mass_equation_node_ids": list(layout.mass_equation_node_ids),
        "pipe_equation_ids": list(layout.pipe_equation_ids),
        "compressor_equation_ids": list(layout.compressor_equation_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _validate_refs(values: tuple[str, ...], *, label: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} et toutes ses références sont obligatoires.")


def _validate_approval(
    *,
    state: StationarySolverPolicyState,
    approval_ref: str | None,
    label: str,
) -> None:
    if state is StationarySolverPolicyState.APPROVED:
        if approval_ref is None or not approval_ref.strip():
            raise ValueError(f"Un {label} APPROVED doit référencer son approbation.")
    elif approval_ref is not None:
        raise ValueError(f"Un {label} DRAFT ne peut pas porter une approbation active.")


@dataclass(frozen=True, slots=True)
class PreRegisteredStationaryEquipmentScaleArtifact:
    """Échelles mixtes pré-enregistrées avant toute exécution solveur."""

    artifact_ref: str
    policy_ref: str
    policy_version: str
    source_ref: str
    registration_ref: str
    pressure_squared_scale_pa2: float
    mass_flow_scale_kg_s: float
    mass_residual_scale_kg_s: float
    pipe_residual_scale_pa2: float
    compressor_residual_scale_pa: float
    state: StationarySolverPolicyState = StationarySolverPolicyState.DRAFT
    approval_ref: str | None = None

    def __post_init__(self) -> None:
        _validate_refs(
            (
                self.artifact_ref,
                self.policy_ref,
                self.policy_version,
                self.source_ref,
                self.registration_ref,
            ),
            label="L'artefact d'échelle mixte",
        )
        StationaryActiveCompressorNumericalScale(
            pressure_squared_scale_pa2=self.pressure_squared_scale_pa2,
            mass_flow_scale_kg_s=self.mass_flow_scale_kg_s,
            mass_residual_scale_kg_s=self.mass_residual_scale_kg_s,
            pipe_residual_scale_pa2=self.pipe_residual_scale_pa2,
            compressor_residual_scale_pa=self.compressor_residual_scale_pa,
            source_ref=self.source_ref,
        )
        _validate_approval(
            state=self.state,
            approval_ref=self.approval_ref,
            label="artefact d'échelle mixte",
        )


@dataclass(frozen=True, slots=True)
class ApprovedStationaryEquipmentScaleArtifact:
    """Échelles mixtes approuvées avec preuve documentaire."""

    artifact_ref: str
    policy_ref: str
    policy_version: str
    source_ref: str
    registration_ref: str
    approval_ref: str
    pressure_squared_scale_pa2: float
    mass_flow_scale_kg_s: float
    mass_residual_scale_kg_s: float
    pipe_residual_scale_pa2: float
    compressor_residual_scale_pa: float

    def to_numerical_scale(self) -> StationaryActiveCompressorNumericalScale:
        return StationaryActiveCompressorNumericalScale(
            pressure_squared_scale_pa2=self.pressure_squared_scale_pa2,
            mass_flow_scale_kg_s=self.mass_flow_scale_kg_s,
            mass_residual_scale_kg_s=self.mass_residual_scale_kg_s,
            pipe_residual_scale_pa2=self.pipe_residual_scale_pa2,
            compressor_residual_scale_pa=self.compressor_residual_scale_pa,
            source_ref=f"{self.artifact_ref}#approved-scale",
        )


def materialize_approved_stationary_equipment_scale(
    artifact: PreRegisteredStationaryEquipmentScaleArtifact,
) -> ApprovedStationaryEquipmentScaleArtifact:
    """Matérialise seulement un jeu d'échelles explicitement APPROVED."""

    if artifact.state is not StationarySolverPolicyState.APPROVED:
        raise PermissionError("L'artefact d'échelle mixte n'est pas APPROVED.")
    approval_ref = artifact.approval_ref
    if approval_ref is None:
        raise RuntimeError("Un artefact d'échelle mixte APPROVED doit porter une approbation.")
    return ApprovedStationaryEquipmentScaleArtifact(
        artifact_ref=artifact.artifact_ref,
        policy_ref=artifact.policy_ref,
        policy_version=artifact.policy_version,
        source_ref=artifact.source_ref,
        registration_ref=artifact.registration_ref,
        approval_ref=approval_ref,
        pressure_squared_scale_pa2=artifact.pressure_squared_scale_pa2,
        mass_flow_scale_kg_s=artifact.mass_flow_scale_kg_s,
        mass_residual_scale_kg_s=artifact.mass_residual_scale_kg_s,
        pipe_residual_scale_pa2=artifact.pipe_residual_scale_pa2,
        compressor_residual_scale_pa=artifact.compressor_residual_scale_pa,
    )


@dataclass(frozen=True, slots=True)
class PreRegisteredStationaryEquipmentInitialGuessArtifact:
    """État initial mixte pré-enregistré pour un problème/layout exact."""

    artifact_ref: str
    policy_ref: str
    policy_version: str
    problem_ref: str
    layout_sha256: str
    source_ref: str
    registration_ref: str
    unknown_state: StationaryActiveCompressorUnknownState
    state: StationarySolverPolicyState = StationarySolverPolicyState.DRAFT
    approval_ref: str | None = None

    def __post_init__(self) -> None:
        _validate_refs(
            (
                self.artifact_ref,
                self.policy_ref,
                self.policy_version,
                self.problem_ref,
                self.layout_sha256,
                self.source_ref,
                self.registration_ref,
            ),
            label="L'artefact d'initialisation mixte",
        )
        if not self.layout_sha256.startswith("sha256:") or len(self.layout_sha256) != 71:
            raise ValueError("L'empreinte du layout mixte doit être une référence sha256 canonique.")
        _validate_approval(
            state=self.state,
            approval_ref=self.approval_ref,
            label="artefact d'initialisation mixte",
        )


@dataclass(frozen=True, slots=True)
class ApprovedStationaryEquipmentInitialGuessArtifact:
    """État initial mixte approuvé pour un problème/layout exact."""

    artifact_ref: str
    policy_ref: str
    policy_version: str
    problem_ref: str
    layout_sha256: str
    source_ref: str
    registration_ref: str
    approval_ref: str
    unknown_state: StationaryActiveCompressorUnknownState


def materialize_approved_stationary_equipment_initial_guess(
    *,
    problem: StationaryActiveCompressorProblem,
    layout: StationaryActiveCompressorUnknownLayout,
    artifact: PreRegisteredStationaryEquipmentInitialGuessArtifact,
) -> ApprovedStationaryEquipmentInitialGuessArtifact:
    """Valide problème, layout et état initial avant de libérer l'artefact."""

    if artifact.state is not StationarySolverPolicyState.APPROVED:
        raise PermissionError("L'artefact d'initialisation mixte n'est pas APPROVED.")
    if artifact.problem_ref != problem.problem_ref:
        raise ValueError("L'artefact d'initialisation mixte vise un autre problème.")
    actual_layout_sha256 = stationary_active_compressor_layout_sha256(layout)
    if artifact.layout_sha256 != actual_layout_sha256:
        raise ValueError("L'artefact d'initialisation mixte vise un autre layout.")

    materialize_stationary_active_compressor_candidate(
        problem,
        layout,
        artifact.unknown_state,
    )
    approval_ref = artifact.approval_ref
    if approval_ref is None:
        raise RuntimeError("Un artefact d'initialisation mixte APPROVED doit porter une approbation.")
    return ApprovedStationaryEquipmentInitialGuessArtifact(
        artifact_ref=artifact.artifact_ref,
        policy_ref=artifact.policy_ref,
        policy_version=artifact.policy_version,
        problem_ref=artifact.problem_ref,
        layout_sha256=artifact.layout_sha256,
        source_ref=artifact.source_ref,
        registration_ref=artifact.registration_ref,
        approval_ref=approval_ref,
        unknown_state=artifact.unknown_state,
    )


__all__ = [
    "ApprovedStationaryEquipmentInitialGuessArtifact",
    "ApprovedStationaryEquipmentScaleArtifact",
    "PreRegisteredStationaryEquipmentInitialGuessArtifact",
    "PreRegisteredStationaryEquipmentScaleArtifact",
    "materialize_approved_stationary_equipment_initial_guess",
    "materialize_approved_stationary_equipment_scale",
    "stationary_active_compressor_layout_sha256",
]
