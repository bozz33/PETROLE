"""Artefacts approuvables d'échelle et d'initialisation pour P6-B.

Aucune échelle et aucune valeur initiale ne sont déduites dans ce module. Les
valeurs sont fournies explicitement, pré-enregistrées, liées à une politique
versionnée puis approuvées. L'initialisation est en plus liée à l'empreinte
exacte du layout du problème.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from hydro_gas.stationary_candidate import (
    StationaryWeymouthUnknownState,
    materialize_stationary_weymouth_candidate,
)
from hydro_gas.stationary_numerics import StationaryWeymouthNumericalScale
from hydro_gas.stationary_problem import (
    StationaryWeymouthProblem,
    StationaryWeymouthUnknownLayout,
)
from hydro_gas.stationary_solver_governance import StationarySolverPolicyState


def stationary_weymouth_layout_sha256(layout: StationaryWeymouthUnknownLayout) -> str:
    """Calcule une empreinte canonique de l'ordre des inconnues et équations."""

    payload = {
        "connected_components": [list(component) for component in layout.connected_components],
        "fixed_pressure_node_ids": list(layout.fixed_pressure_node_ids),
        "unknown_pressure_node_ids": list(layout.unknown_pressure_node_ids),
        "pipe_flow_ids": list(layout.pipe_flow_ids),
        "slack_external_flow_node_ids": list(layout.slack_external_flow_node_ids),
        "mass_equation_node_ids": list(layout.mass_equation_node_ids),
        "pipe_equation_ids": list(layout.pipe_equation_ids),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _validate_required_references(values: tuple[str, ...], *, label: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} et toutes ses références sont obligatoires.")


def _validate_approval_state(
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
class PreRegisteredStationaryWeymouthScaleArtifact:
    """Échelles explicites pré-enregistrées avant exécution du solveur."""

    artifact_ref: str
    policy_ref: str
    policy_version: str
    source_ref: str
    registration_ref: str
    pressure_squared_scale_pa2: float
    mass_flow_scale_kg_s: float
    mass_residual_scale_kg_s: float
    pipe_residual_scale_pa2: float
    state: StationarySolverPolicyState = StationarySolverPolicyState.DRAFT
    approval_ref: str | None = None

    def __post_init__(self) -> None:
        _validate_required_references(
            (
                self.artifact_ref,
                self.policy_ref,
                self.policy_version,
                self.source_ref,
                self.registration_ref,
            ),
            label="L'artefact d'échelle",
        )
        StationaryWeymouthNumericalScale(
            pressure_squared_scale_pa2=self.pressure_squared_scale_pa2,
            mass_flow_scale_kg_s=self.mass_flow_scale_kg_s,
            mass_residual_scale_kg_s=self.mass_residual_scale_kg_s,
            pipe_residual_scale_pa2=self.pipe_residual_scale_pa2,
            source_ref=self.source_ref,
        )
        _validate_approval_state(
            state=self.state,
            approval_ref=self.approval_ref,
            label="artefact d'échelle",
        )


@dataclass(frozen=True, slots=True)
class ApprovedStationaryWeymouthScaleArtifact:
    """Échelles approuvées, liées à une politique et une preuve d'approbation."""

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

    def to_numerical_scale(self) -> StationaryWeymouthNumericalScale:
        return StationaryWeymouthNumericalScale(
            pressure_squared_scale_pa2=self.pressure_squared_scale_pa2,
            mass_flow_scale_kg_s=self.mass_flow_scale_kg_s,
            mass_residual_scale_kg_s=self.mass_residual_scale_kg_s,
            pipe_residual_scale_pa2=self.pipe_residual_scale_pa2,
            source_ref=f"{self.artifact_ref}#approved-scale",
        )


def materialize_approved_stationary_weymouth_scale(
    artifact: PreRegisteredStationaryWeymouthScaleArtifact,
) -> ApprovedStationaryWeymouthScaleArtifact:
    """Matérialise uniquement un artefact d'échelle explicitement approuvé."""

    if artifact.state is not StationarySolverPolicyState.APPROVED:
        raise PermissionError("L'artefact d'échelle n'est pas APPROVED.")
    approval_ref = artifact.approval_ref
    if approval_ref is None:
        raise RuntimeError("Un artefact d'échelle APPROVED doit porter une approbation.")
    return ApprovedStationaryWeymouthScaleArtifact(
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
    )


@dataclass(frozen=True, slots=True)
class PreRegisteredStationaryWeymouthInitialGuessArtifact:
    """État initial physique pré-enregistré pour un layout exact."""

    artifact_ref: str
    policy_ref: str
    policy_version: str
    problem_ref: str
    layout_sha256: str
    source_ref: str
    registration_ref: str
    unknown_state: StationaryWeymouthUnknownState
    state: StationarySolverPolicyState = StationarySolverPolicyState.DRAFT
    approval_ref: str | None = None

    def __post_init__(self) -> None:
        _validate_required_references(
            (
                self.artifact_ref,
                self.policy_ref,
                self.policy_version,
                self.problem_ref,
                self.layout_sha256,
                self.source_ref,
                self.registration_ref,
            ),
            label="L'artefact d'initialisation",
        )
        if not self.layout_sha256.startswith("sha256:") or len(self.layout_sha256) != 71:
            raise ValueError("L'empreinte du layout doit être une référence sha256 canonique.")
        _validate_approval_state(
            state=self.state,
            approval_ref=self.approval_ref,
            label="artefact d'initialisation",
        )


@dataclass(frozen=True, slots=True)
class ApprovedStationaryWeymouthInitialGuessArtifact:
    """État initial approuvé pour un problème et un layout exacts."""

    artifact_ref: str
    policy_ref: str
    policy_version: str
    problem_ref: str
    layout_sha256: str
    source_ref: str
    registration_ref: str
    approval_ref: str
    unknown_state: StationaryWeymouthUnknownState


def materialize_approved_stationary_weymouth_initial_guess(
    *,
    problem: StationaryWeymouthProblem,
    layout: StationaryWeymouthUnknownLayout,
    artifact: PreRegisteredStationaryWeymouthInitialGuessArtifact,
) -> ApprovedStationaryWeymouthInitialGuessArtifact:
    """Valide l'identité du problème/layout avant de libérer l'état initial."""

    if artifact.state is not StationarySolverPolicyState.APPROVED:
        raise PermissionError("L'artefact d'initialisation n'est pas APPROVED.")
    if artifact.problem_ref != problem.problem_ref:
        raise ValueError("L'artefact d'initialisation vise un autre problème stationnaire.")
    actual_layout_sha256 = stationary_weymouth_layout_sha256(layout)
    if artifact.layout_sha256 != actual_layout_sha256:
        raise ValueError("L'artefact d'initialisation vise un autre layout stationnaire.")

    materialize_stationary_weymouth_candidate(problem, layout, artifact.unknown_state)

    approval_ref = artifact.approval_ref
    if approval_ref is None:
        raise RuntimeError("Un artefact d'initialisation APPROVED doit porter une approbation.")
    return ApprovedStationaryWeymouthInitialGuessArtifact(
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
    "ApprovedStationaryWeymouthInitialGuessArtifact",
    "ApprovedStationaryWeymouthScaleArtifact",
    "PreRegisteredStationaryWeymouthInitialGuessArtifact",
    "PreRegisteredStationaryWeymouthScaleArtifact",
    "materialize_approved_stationary_weymouth_initial_guess",
    "materialize_approved_stationary_weymouth_scale",
    "stationary_weymouth_layout_sha256",
]
