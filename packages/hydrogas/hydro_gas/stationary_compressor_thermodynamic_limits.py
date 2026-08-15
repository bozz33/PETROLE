"""Gouvernance P6-D des limites thermodynamiques de compresseurs.

Aucune limite de puissance ou de température n'est fournie par défaut. Une
limite ne peut être utilisée pour une évaluation qu'après pré-enregistrement,
provenance explicite et approbation. Les résultats d'un solveur non convergé
restent visibles comme diagnostics, mais ne peuvent jamais recevoir un PASS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryActiveCompressorThermodynamicAssessment,
    StationaryCompressorThermodynamicResult,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


class CompressorThermodynamicLimitState(StrEnum):
    """État documentaire d'un jeu de limites thermo constructeur/projet."""

    DRAFT = "draft"
    APPROVED = "approved"


def _validate_limits(
    *,
    maximum_shaft_power_input_w: float | None,
    maximum_actual_outlet_temperature_k: float | None,
) -> None:
    if maximum_shaft_power_input_w is None and maximum_actual_outlet_temperature_k is None:
        raise ValueError("Au moins une limite thermodynamique explicite est obligatoire.")
    if maximum_shaft_power_input_w is not None and (
        not math.isfinite(maximum_shaft_power_input_w) or maximum_shaft_power_input_w < 0.0
    ):
        raise ValueError("La puissance mécanique maximale doit être finie et positive ou nulle.")
    if maximum_actual_outlet_temperature_k is not None and (
        not math.isfinite(maximum_actual_outlet_temperature_k)
        or maximum_actual_outlet_temperature_k <= 0.0
    ):
        raise ValueError("La température de refoulement maximale doit être finie et positive.")


@dataclass(frozen=True, slots=True)
class PreRegisteredCompressorThermodynamicLimits:
    """Jeu de limites pré-enregistré sans valeur implicite."""

    limit_set_id: str
    limit_set_version: str
    compressor_id: str
    source_ref: str
    registration_ref: str
    state: CompressorThermodynamicLimitState = CompressorThermodynamicLimitState.DRAFT
    approval_ref: str | None = None
    maximum_shaft_power_input_w: float | None = None
    maximum_actual_outlet_temperature_k: float | None = None

    def __post_init__(self) -> None:
        required = (
            self.limit_set_id,
            self.limit_set_version,
            self.compressor_id,
            self.source_ref,
            self.registration_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Le jeu de limites thermo et toutes ses références sont obligatoires.")
        _validate_limits(
            maximum_shaft_power_input_w=self.maximum_shaft_power_input_w,
            maximum_actual_outlet_temperature_k=self.maximum_actual_outlet_temperature_k,
        )
        if self.state is CompressorThermodynamicLimitState.APPROVED:
            if self.approval_ref is None or not self.approval_ref.strip():
                raise ValueError("Un jeu de limites thermo APPROVED doit référencer son approbation.")
        elif self.approval_ref is not None:
            raise ValueError("Un jeu de limites thermo DRAFT ne peut pas porter une approbation active.")


@dataclass(frozen=True, slots=True)
class ApprovedCompressorThermodynamicLimits:
    """Limites thermodynamiques approuvées pour un compresseur exact."""

    limit_set_id: str
    limit_set_version: str
    compressor_id: str
    source_ref: str
    registration_ref: str
    approval_ref: str
    maximum_shaft_power_input_w: float | None
    maximum_actual_outlet_temperature_k: float | None

    def __post_init__(self) -> None:
        required = (
            self.limit_set_id,
            self.limit_set_version,
            self.compressor_id,
            self.source_ref,
            self.registration_ref,
            self.approval_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Les limites thermo approuvées doivent être entièrement référencées.")
        _validate_limits(
            maximum_shaft_power_input_w=self.maximum_shaft_power_input_w,
            maximum_actual_outlet_temperature_k=self.maximum_actual_outlet_temperature_k,
        )


def materialize_approved_compressor_thermodynamic_limits(
    limits: PreRegisteredCompressorThermodynamicLimits,
) -> ApprovedCompressorThermodynamicLimits:
    """Matérialise uniquement un jeu explicitement approuvé."""

    if limits.state is not CompressorThermodynamicLimitState.APPROVED:
        raise PermissionError(
            f"Le jeu de limites {limits.limit_set_id} n'est pas APPROVED et ne peut pas être utilisé."
        )
    approval_ref = limits.approval_ref
    if approval_ref is None:
        raise RuntimeError("Un jeu APPROVED doit déjà posséder une référence d'approbation.")
    return ApprovedCompressorThermodynamicLimits(
        limit_set_id=limits.limit_set_id,
        limit_set_version=limits.limit_set_version,
        compressor_id=limits.compressor_id,
        source_ref=limits.source_ref,
        registration_ref=limits.registration_ref,
        approval_ref=approval_ref,
        maximum_shaft_power_input_w=limits.maximum_shaft_power_input_w,
        maximum_actual_outlet_temperature_k=limits.maximum_actual_outlet_temperature_k,
    )


@dataclass(frozen=True, slots=True)
class CompressorThermodynamicLimitAssessment:
    """Évaluation factuelle d'un compresseur contre un jeu APPROVED."""

    compressor_id: str
    solver_status: StationaryWeymouthSolverStatus
    limit_set_id: str
    limit_set_version: str
    observed_shaft_power_input_w: float
    maximum_shaft_power_input_w: float | None
    shaft_power_margin_w: float | None
    shaft_power_within_limit: bool | None
    observed_actual_outlet_temperature_k: float
    maximum_actual_outlet_temperature_k: float | None
    outlet_temperature_margin_k: float | None
    outlet_temperature_within_limit: bool | None
    all_approved_limits_passed: bool | None
    evaluation_reason: str | None
    non_positive_shaft_power_observed: bool
    source_ref: str
    registration_ref: str
    approval_ref: str
    qualification_claim: bool = False
    certification_claim: bool = False


def assess_compressor_thermodynamic_limits(
    result: StationaryCompressorThermodynamicResult,
    limits: ApprovedCompressorThermodynamicLimits,
) -> CompressorThermodynamicLimitAssessment:
    """Compare sans tolérance cachée et refuse tout PASS si le solveur n'a pas convergé."""

    if result.compressor_id != limits.compressor_id:
        raise ValueError("Les limites thermo ne correspondent pas au compresseur évalué.")

    shaft_power = result.energy_balance.shaft_power_input_w
    outlet_temperature = result.property_state.actual_outlet_temperature_k
    if not math.isfinite(shaft_power):
        raise ValueError("La puissance mécanique observée doit être finie.")
    if not math.isfinite(outlet_temperature) or outlet_temperature <= 0.0:
        raise ValueError("La température de refoulement observée doit être finie et positive.")

    if result.solver_status is not StationaryWeymouthSolverStatus.CONVERGED:
        return CompressorThermodynamicLimitAssessment(
            compressor_id=result.compressor_id,
            solver_status=result.solver_status,
            limit_set_id=limits.limit_set_id,
            limit_set_version=limits.limit_set_version,
            observed_shaft_power_input_w=shaft_power,
            maximum_shaft_power_input_w=limits.maximum_shaft_power_input_w,
            shaft_power_margin_w=None,
            shaft_power_within_limit=None,
            observed_actual_outlet_temperature_k=outlet_temperature,
            maximum_actual_outlet_temperature_k=limits.maximum_actual_outlet_temperature_k,
            outlet_temperature_margin_k=None,
            outlet_temperature_within_limit=None,
            all_approved_limits_passed=None,
            evaluation_reason=f"source_solver_status:{result.solver_status.value}",
            non_positive_shaft_power_observed=shaft_power <= 0.0,
            source_ref=limits.source_ref,
            registration_ref=limits.registration_ref,
            approval_ref=limits.approval_ref,
        )

    power_margin = None
    power_passed = None
    if limits.maximum_shaft_power_input_w is not None:
        power_margin = limits.maximum_shaft_power_input_w - shaft_power
        power_passed = shaft_power <= limits.maximum_shaft_power_input_w

    temperature_margin = None
    temperature_passed = None
    if limits.maximum_actual_outlet_temperature_k is not None:
        temperature_margin = limits.maximum_actual_outlet_temperature_k - outlet_temperature
        temperature_passed = outlet_temperature <= limits.maximum_actual_outlet_temperature_k

    explicit_checks = tuple(
        value for value in (power_passed, temperature_passed) if value is not None
    )
    return CompressorThermodynamicLimitAssessment(
        compressor_id=result.compressor_id,
        solver_status=result.solver_status,
        limit_set_id=limits.limit_set_id,
        limit_set_version=limits.limit_set_version,
        observed_shaft_power_input_w=shaft_power,
        maximum_shaft_power_input_w=limits.maximum_shaft_power_input_w,
        shaft_power_margin_w=power_margin,
        shaft_power_within_limit=power_passed,
        observed_actual_outlet_temperature_k=outlet_temperature,
        maximum_actual_outlet_temperature_k=limits.maximum_actual_outlet_temperature_k,
        outlet_temperature_margin_k=temperature_margin,
        outlet_temperature_within_limit=temperature_passed,
        all_approved_limits_passed=all(explicit_checks),
        evaluation_reason=None,
        non_positive_shaft_power_observed=shaft_power <= 0.0,
        source_ref=limits.source_ref,
        registration_ref=limits.registration_ref,
        approval_ref=limits.approval_ref,
    )


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorThermodynamicLimitAssessment:
    """Évaluation complète avec couverture exacte des compresseurs actifs."""

    solve_ref: str
    solver_status: StationaryWeymouthSolverStatus
    compressors: tuple[CompressorThermodynamicLimitAssessment, ...]
    all_limits_evaluable: bool
    all_approved_limits_passed: bool | None
    qualification_claim: bool = False
    certification_claim: bool = False


def assess_stationary_active_compressor_thermodynamic_limits(
    assessment: StationaryActiveCompressorThermodynamicAssessment,
    approved_limits: tuple[ApprovedCompressorThermodynamicLimits, ...],
) -> StationaryActiveCompressorThermodynamicLimitAssessment:
    """Exige une limite APPROVED par compresseur actif avant l'évaluation globale."""

    if not assessment.compressors:
        raise ValueError("L'évaluation thermo exige au moins un compresseur.")
    if not approved_limits:
        raise ValueError("Des limites thermo APPROVED sont obligatoires pour chaque compresseur.")

    compressor_ids = tuple(item.compressor_id for item in assessment.compressors)
    if len(compressor_ids) != len(set(compressor_ids)):
        raise ValueError("Les résultats thermodynamiques doivent avoir des identifiants uniques.")
    limit_ids = tuple(item.compressor_id for item in approved_limits)
    if len(limit_ids) != len(set(limit_ids)):
        raise ValueError("Un seul jeu de limites thermo APPROVED est admis par compresseur.")
    if set(limit_ids) != set(compressor_ids):
        raise ValueError(
            "Les limites thermo APPROVED doivent couvrir exactement les compresseurs actifs."
        )

    limits_by_id = {item.compressor_id: item for item in approved_limits}
    evaluated = tuple(
        assess_compressor_thermodynamic_limits(item, limits_by_id[item.compressor_id])
        for item in assessment.compressors
    )
    all_limits_evaluable = all(item.all_approved_limits_passed is not None for item in evaluated)
    all_passed = (
        all(bool(item.all_approved_limits_passed) for item in evaluated)
        if all_limits_evaluable
        else None
    )
    return StationaryActiveCompressorThermodynamicLimitAssessment(
        solve_ref=assessment.solve_ref,
        solver_status=assessment.solver_status,
        compressors=evaluated,
        all_limits_evaluable=all_limits_evaluable,
        all_approved_limits_passed=all_passed,
    )


__all__ = [
    "ApprovedCompressorThermodynamicLimits",
    "CompressorThermodynamicLimitAssessment",
    "CompressorThermodynamicLimitState",
    "PreRegisteredCompressorThermodynamicLimits",
    "StationaryActiveCompressorThermodynamicLimitAssessment",
    "assess_compressor_thermodynamic_limits",
    "assess_stationary_active_compressor_thermodynamic_limits",
    "materialize_approved_compressor_thermodynamic_limits",
]
