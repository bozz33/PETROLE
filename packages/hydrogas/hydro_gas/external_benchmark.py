"""Contrat P6-H de comparaison avec un solveur gaz externe.

La couche est volontairement indépendante du format interne de GasModels ou
d'un autre solveur. Elle compare uniquement des grandeurs déjà calculées dans
la même unité et conserve versions, formulation, empreintes et provenance.
Aucune tolérance scientifique ou industrielle n'est implicite.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} doit être une empreinte SHA-256 hexadécimale.")
    return normalized


@dataclass(frozen=True, slots=True)
class ExternalGasSolverEvidence:
    """Identité reproductible du solveur/cas externe utilisé comme référence."""

    solver_name: str
    solver_version: str
    formulation_ref: str
    data_format_ref: str
    input_sha256: str
    output_sha256: str
    source_ref: str

    def __post_init__(self) -> None:
        required = (
            self.solver_name,
            self.solver_version,
            self.formulation_ref,
            self.data_format_ref,
            self.source_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Solveur, version, formulation, format et provenance sont obligatoires."
            )
        object.__setattr__(self, "input_sha256", _sha256(self.input_sha256, "input_sha256"))
        object.__setattr__(self, "output_sha256", _sha256(self.output_sha256, "output_sha256"))


@dataclass(frozen=True, slots=True)
class GasBenchmarkObservation:
    """Paire PETROLE/référence pour une grandeur et une localisation précises."""

    observation_id: str
    quantity_ref: str
    location_ref: str
    unit: str
    petrole_value: float
    reference_value: float
    petrole_source_ref: str
    reference_source_ref: str

    def __post_init__(self) -> None:
        required = (
            self.observation_id,
            self.quantity_ref,
            self.location_ref,
            self.unit,
            self.petrole_source_ref,
            self.reference_source_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Identité, grandeur, localisation, unité et provenances sont obligatoires."
            )
        if not math.isfinite(self.petrole_value) or not math.isfinite(self.reference_value):
            raise ValueError("Les valeurs de benchmark doivent être finies.")


@dataclass(frozen=True, slots=True)
class GasBenchmarkCriterion:
    """Tolérance pré-enregistrée pour une observation de benchmark."""

    observation_id: str
    source_ref: str
    maximum_absolute_error: float | None = None
    maximum_relative_error_fraction: float | None = None

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.source_ref.strip():
            raise ValueError("L'observation et la provenance du critère sont obligatoires.")
        if self.maximum_absolute_error is None and self.maximum_relative_error_fraction is None:
            raise ValueError("Au moins un critère d'erreur explicite est obligatoire.")
        if self.maximum_absolute_error is not None and (
            not math.isfinite(self.maximum_absolute_error) or self.maximum_absolute_error < 0
        ):
            raise ValueError("L'erreur absolue maximale doit être finie et positive ou nulle.")
        if self.maximum_relative_error_fraction is not None and (
            not math.isfinite(self.maximum_relative_error_fraction)
            or self.maximum_relative_error_fraction < 0
        ):
            raise ValueError("L'erreur relative maximale doit être finie et positive ou nulle.")


@dataclass(frozen=True, slots=True)
class GasBenchmarkObservationAssessment:
    observation_id: str
    signed_error: float
    absolute_error: float
    relative_error_fraction: float | None
    passed: bool | None
    violations: tuple[str, ...]
    criterion_source_ref: str | None


@dataclass(frozen=True, slots=True)
class ExternalGasBenchmarkAssessment:
    """Résultat factuel de campagne, sans transformer l'absence de critère en succès."""

    campaign_ref: str
    protocol_ref: str
    petrole_engine_version: str
    external_solver: ExternalGasSolverEvidence
    observations: tuple[GasBenchmarkObservationAssessment, ...]
    all_evaluable_criteria_passed: bool | None
    has_unevaluable_criteria: bool


def assess_external_gas_benchmark(
    *,
    campaign_ref: str,
    protocol_ref: str,
    petrole_engine_version: str,
    external_solver: ExternalGasSolverEvidence,
    observations: tuple[GasBenchmarkObservation, ...],
    criteria: tuple[GasBenchmarkCriterion, ...] = (),
) -> ExternalGasBenchmarkAssessment:
    """Compare PETROLE à une référence externe avec critères explicitement fournis."""

    required = (campaign_ref, protocol_ref, petrole_engine_version)
    if any(not value.strip() for value in required):
        raise ValueError("Campagne, protocole et version moteur PETROLE sont obligatoires.")
    if not observations:
        raise ValueError("Une campagne de benchmark doit contenir au moins une observation.")

    observation_ids = tuple(observation.observation_id for observation in observations)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("Les identifiants d'observation de benchmark doivent être uniques.")

    criteria_ids = tuple(criterion.observation_id for criterion in criteria)
    if len(criteria_ids) != len(set(criteria_ids)):
        raise ValueError("Un seul critère peut être défini par observation de benchmark.")
    unknown_criteria = set(criteria_ids) - set(observation_ids)
    if unknown_criteria:
        raise ValueError("Un critère de benchmark référence une observation inconnue.")

    criteria_by_id = {criterion.observation_id: criterion for criterion in criteria}
    assessed: list[GasBenchmarkObservationAssessment] = []

    for observation in observations:
        signed_error = observation.petrole_value - observation.reference_value
        absolute_error = abs(signed_error)
        relative_error = (
            absolute_error / abs(observation.reference_value)
            if observation.reference_value != 0.0
            else None
        )
        criterion = criteria_by_id.get(observation.observation_id)
        violations: list[str] = []
        passed: bool | None = None
        criterion_source_ref: str | None = None

        if criterion is not None:
            criterion_source_ref = criterion.source_ref
            if (
                criterion.maximum_absolute_error is not None
                and absolute_error > criterion.maximum_absolute_error
            ):
                violations.append("absolute_error_above_criterion")
            if criterion.maximum_relative_error_fraction is not None:
                if relative_error is None:
                    violations.append("relative_error_undefined_reference_zero")
                elif relative_error > criterion.maximum_relative_error_fraction:
                    violations.append("relative_error_above_criterion")
            passed = not violations

        assessed.append(
            GasBenchmarkObservationAssessment(
                observation_id=observation.observation_id,
                signed_error=signed_error,
                absolute_error=absolute_error,
                relative_error_fraction=relative_error,
                passed=passed,
                violations=tuple(violations),
                criterion_source_ref=criterion_source_ref,
            )
        )

    evaluable = [item.passed for item in assessed if item.passed is not None]
    all_evaluable = all(evaluable) if evaluable else None
    has_unevaluable = any(item.passed is None for item in assessed)

    return ExternalGasBenchmarkAssessment(
        campaign_ref=campaign_ref,
        protocol_ref=protocol_ref,
        petrole_engine_version=petrole_engine_version,
        external_solver=external_solver,
        observations=tuple(assessed),
        all_evaluable_criteria_passed=all_evaluable,
        has_unevaluable_criteria=has_unevaluable,
    )


__all__ = [
    "ExternalGasBenchmarkAssessment",
    "ExternalGasSolverEvidence",
    "GasBenchmarkCriterion",
    "GasBenchmarkObservation",
    "GasBenchmarkObservationAssessment",
    "assess_external_gas_benchmark",
]
