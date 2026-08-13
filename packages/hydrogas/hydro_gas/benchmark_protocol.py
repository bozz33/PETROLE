"""Pré-enregistrement des critères de benchmark gaz P6-H.

Cette couche prouve qu'un critère appartient à un protocole/version/cas précis
et qu'il a été approuvé avant d'être matérialisé pour la comparaison. Elle ne
définit aucune tolérance par défaut et ne transforme jamais un brouillon en
critère exécutable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from hydro_gas.external_benchmark import GasBenchmarkCriterion, GasBenchmarkObservation


class GasBenchmarkCriterionState(StrEnum):
    """État documentaire d'un critère de benchmark."""

    DRAFT = "draft"
    APPROVED = "approved"


@dataclass(frozen=True, slots=True)
class PreRegisteredGasBenchmarkCriterion:
    """Critère versionné et rattaché à un contexte scientifique explicite."""

    criterion_id: str
    criterion_version: str
    protocol_ref: str
    model_id: str
    model_version: str
    formulation_ref: str
    case_ref: str
    observation_id: str
    quantity_ref: str
    unit: str
    source_ref: str
    registration_ref: str
    state: GasBenchmarkCriterionState = GasBenchmarkCriterionState.DRAFT
    approval_ref: str | None = None
    maximum_absolute_error: float | None = None
    maximum_relative_error_fraction: float | None = None

    def __post_init__(self) -> None:
        required = (
            self.criterion_id,
            self.criterion_version,
            self.protocol_ref,
            self.model_id,
            self.model_version,
            self.formulation_ref,
            self.case_ref,
            self.observation_id,
            self.quantity_ref,
            self.unit,
            self.source_ref,
            self.registration_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Le critère pré-enregistré et toutes ses références sont obligatoires.")
        if self.maximum_absolute_error is None and self.maximum_relative_error_fraction is None:
            raise ValueError("Un critère doit définir au moins une limite explicite.")
        for value in (self.maximum_absolute_error, self.maximum_relative_error_fraction):
            if value is not None and (not math.isfinite(value) or value < 0.0):
                raise ValueError("Les limites de benchmark doivent être finies et positives ou nulles.")

        if self.state is GasBenchmarkCriterionState.APPROVED:
            if self.approval_ref is None or not self.approval_ref.strip():
                raise ValueError("Un critère APPROVED doit référencer son approbation.")
        elif self.approval_ref is not None:
            raise ValueError("Un critère DRAFT ne peut pas porter une approbation active.")


@dataclass(frozen=True, slots=True)
class GasBenchmarkProtocolContext:
    """Contexte exact auquel un ensemble de critères peut être appliqué."""

    protocol_ref: str
    model_id: str
    model_version: str
    formulation_ref: str
    case_ref: str

    def __post_init__(self) -> None:
        values = (
            self.protocol_ref,
            self.model_id,
            self.model_version,
            self.formulation_ref,
            self.case_ref,
        )
        if any(not value.strip() for value in values):
            raise ValueError("Le contexte de protocole doit être entièrement référencé.")


@dataclass(frozen=True, slots=True)
class ApprovedGasBenchmarkCriteria:
    """Critères bas niveau accompagnés de leurs preuves d'approbation."""

    criteria: tuple[GasBenchmarkCriterion, ...]
    criterion_ids: tuple[str, ...]
    approval_refs: tuple[str, ...]
    registration_refs: tuple[str, ...]
    protocol_ref: str


def materialize_approved_gas_benchmark_criteria(
    *,
    context: GasBenchmarkProtocolContext,
    criteria: tuple[PreRegisteredGasBenchmarkCriterion, ...],
    observations: tuple[GasBenchmarkObservation, ...],
) -> ApprovedGasBenchmarkCriteria:
    """Matérialise uniquement des critères approuvés et exactement compatibles.

    La fonction échoue fermée : brouillon, doublon, observation absente,
    contexte différent, grandeur différente ou unité différente empêchent la
    création de critères bas niveau. Aucune tolérance n'est créée ici.
    """

    if not criteria:
        raise ValueError("Au moins un critère pré-enregistré est requis.")

    criterion_ids = tuple(criterion.criterion_id for criterion in criteria)
    if len(criterion_ids) != len(set(criterion_ids)):
        raise ValueError("Les identifiants de critères doivent être uniques.")
    observation_ids = tuple(criterion.observation_id for criterion in criteria)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("Une observation ne peut recevoir qu'un critère dans un protocole.")

    observations_by_id = {observation.observation_id: observation for observation in observations}
    runtime: list[GasBenchmarkCriterion] = []
    approvals: list[str] = []
    registrations: list[str] = []

    for criterion in criteria:
        if criterion.state is not GasBenchmarkCriterionState.APPROVED:
            raise PermissionError(
                f"Le critère {criterion.criterion_id} n'est pas APPROVED et ne peut pas être exécuté."
            )
        expected_context = (
            context.protocol_ref,
            context.model_id,
            context.model_version,
            context.formulation_ref,
            context.case_ref,
        )
        actual_context = (
            criterion.protocol_ref,
            criterion.model_id,
            criterion.model_version,
            criterion.formulation_ref,
            criterion.case_ref,
        )
        if actual_context != expected_context:
            raise ValueError(
                f"Le critère {criterion.criterion_id} ne correspond pas au contexte de benchmark."
            )

        observation = observations_by_id.get(criterion.observation_id)
        if observation is None:
            raise ValueError(
                f"Le critère {criterion.criterion_id} vise une observation absente du benchmark."
            )
        if observation.quantity_ref != criterion.quantity_ref:
            raise ValueError(
                f"Le critère {criterion.criterion_id} vise une autre grandeur que l'observation."
            )
        if observation.unit != criterion.unit:
            raise ValueError(
                f"Le critère {criterion.criterion_id} utilise une autre unité que l'observation."
            )

        runtime.append(
            GasBenchmarkCriterion(
                observation_id=criterion.observation_id,
                maximum_absolute_error=criterion.maximum_absolute_error,
                maximum_relative_error_fraction=criterion.maximum_relative_error_fraction,
                source_ref=criterion.source_ref,
            )
        )
        approvals.append(criterion.approval_ref or "")
        registrations.append(criterion.registration_ref)

    return ApprovedGasBenchmarkCriteria(
        criteria=tuple(runtime),
        criterion_ids=criterion_ids,
        approval_refs=tuple(approvals),
        registration_refs=tuple(registrations),
        protocol_ref=context.protocol_ref,
    )


__all__ = [
    "ApprovedGasBenchmarkCriteria",
    "GasBenchmarkCriterionState",
    "GasBenchmarkProtocolContext",
    "PreRegisteredGasBenchmarkCriterion",
    "materialize_approved_gas_benchmark_criteria",
]
