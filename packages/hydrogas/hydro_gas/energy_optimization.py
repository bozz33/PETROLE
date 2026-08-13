"""Sélection énergétique discrète P6-F sur candidats gaz déjà évalués.

Cette brique ne résout aucune équation de conduite, aucune carte compresseur et
aucune logique de contrôle. Elle classe seulement des plans dont l'énergie et
les preuves de contraintes ont été calculées en amont par des modèles qualifiés.
Elle constitue la fondation d'énumération filtrée prévue par D07 avant tout
NLP/MILP/MINLP couplé à un futur solveur gaz complet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class GasEnergySelectionStatus(StrEnum):
    """Statut explicite d'une recherche discrète complètement parcourue."""

    OPTIMAL_DISCRETE = "GAS_ENERGY_OPTIMAL_DISCRETE"
    INFEASIBLE = "GAS_ENERGY_INFEASIBLE"


@dataclass(frozen=True, slots=True)
class GasDispatchConstraintEvidence:
    """Preuve externe qu'une contrainte d'un candidat est satisfaite ou violée."""

    constraint_id: str
    passed: bool
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.constraint_id.strip() or not self.evidence_ref.strip():
            raise ValueError("La contrainte et sa preuve sont obligatoires.")


@dataclass(frozen=True, slots=True)
class GasEnergyDispatchCandidate:
    """Plan discret dont les grandeurs physiques ont déjà été évaluées.

    ``energy_j`` est une entrée traçable : cette couche ne la recalcule pas à
    partir du rendement, du débit ou du rapport de pression.
    """

    candidate_id: str
    station_id: str
    interval_duration_s: float
    energy_j: float
    operating_point_refs: tuple[str, ...]
    constraint_evidence: tuple[GasDispatchConstraintEvidence, ...]
    model_version: str
    source_ref: str

    def __post_init__(self) -> None:
        required = (self.candidate_id, self.station_id, self.model_version, self.source_ref)
        if any(not value.strip() for value in required):
            raise ValueError(
                "Le candidat, la station, la version de modèle et la provenance sont obligatoires."
            )
        if not math.isfinite(self.interval_duration_s) or self.interval_duration_s <= 0:
            raise ValueError("La durée du plan doit être finie et strictement positive.")
        if not math.isfinite(self.energy_j) or self.energy_j < 0:
            raise ValueError("L'énergie du plan doit être finie et positive ou nulle.")

        operating_refs = tuple(
            dict.fromkeys(value.strip() for value in self.operating_point_refs if value.strip())
        )
        if not operating_refs:
            raise ValueError("Au moins une référence de point de fonctionnement est obligatoire.")
        object.__setattr__(self, "operating_point_refs", operating_refs)

        if not self.constraint_evidence:
            raise ValueError(
                "Un candidat doit fournir au moins une preuve de contrainte ; aucune faisabilité implicite n'est admise."
            )
        constraint_ids = tuple(item.constraint_id for item in self.constraint_evidence)
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("Les identifiants de contraintes d'un candidat doivent être uniques.")

    @property
    def violation_codes(self) -> tuple[str, ...]:
        return tuple(
            evidence.constraint_id for evidence in self.constraint_evidence if not evidence.passed
        )

    @property
    def feasible(self) -> bool:
        return not self.violation_codes


@dataclass(frozen=True, slots=True)
class RankedGasEnergyCandidate:
    rank: int
    candidate_id: str
    station_id: str
    energy_j: float
    interval_duration_s: float
    operating_point_refs: tuple[str, ...]
    constraint_evidence_refs: tuple[str, ...]
    model_version: str
    source_ref: str


@dataclass(frozen=True, slots=True)
class RejectedGasEnergyCandidate:
    candidate_id: str
    violation_codes: tuple[str, ...]
    constraint_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GasEnergySelectionResult:
    """Résultat d'une énumération exhaustive sur l'ensemble fourni."""

    status: GasEnergySelectionStatus
    ranked: tuple[RankedGasEnergyCandidate, ...]
    rejected: tuple[RejectedGasEnergyCandidate, ...]
    generated_count: int
    feasible_count: int
    objective_name: str = "minimum_total_energy_j"
    complete: bool = True
    optimality_gap: float | None = 0.0

    @property
    def selected(self) -> RankedGasEnergyCandidate | None:
        return self.ranked[0] if self.ranked else None


def select_minimum_energy_dispatch(
    candidates: tuple[GasEnergyDispatchCandidate, ...],
) -> GasEnergySelectionResult:
    """Classe tous les candidats faisables par énergie totale croissante.

    Le résultat ``OPTIMAL_DISCRETE`` signifie uniquement que l'ensemble de
    candidats fourni a été parcouru complètement. Il ne prouve ni l'optimalité
    continue, ni l'optimalité du réseau gaz, ni une autorisation d'exploitation.
    Les égalités d'énergie sont départagées par ``candidate_id`` pour assurer la
    reproductibilité.
    """

    if not candidates:
        raise ValueError("Au moins un candidat énergétique gaz est requis.")

    candidate_ids = tuple(candidate.candidate_id for candidate in candidates)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Les identifiants de candidats énergétiques doivent être uniques.")

    feasible = sorted(
        (candidate for candidate in candidates if candidate.feasible),
        key=lambda candidate: (candidate.energy_j, candidate.candidate_id),
    )
    rejected_candidates = tuple(candidate for candidate in candidates if not candidate.feasible)

    ranked = tuple(
        RankedGasEnergyCandidate(
            rank=rank,
            candidate_id=candidate.candidate_id,
            station_id=candidate.station_id,
            energy_j=candidate.energy_j,
            interval_duration_s=candidate.interval_duration_s,
            operating_point_refs=candidate.operating_point_refs,
            constraint_evidence_refs=tuple(
                evidence.evidence_ref for evidence in candidate.constraint_evidence
            ),
            model_version=candidate.model_version,
            source_ref=candidate.source_ref,
        )
        for rank, candidate in enumerate(feasible, start=1)
    )
    rejected = tuple(
        RejectedGasEnergyCandidate(
            candidate_id=candidate.candidate_id,
            violation_codes=candidate.violation_codes,
            constraint_evidence_refs=tuple(
                evidence.evidence_ref for evidence in candidate.constraint_evidence
            ),
        )
        for candidate in rejected_candidates
    )

    return GasEnergySelectionResult(
        status=(
            GasEnergySelectionStatus.OPTIMAL_DISCRETE
            if ranked
            else GasEnergySelectionStatus.INFEASIBLE
        ),
        ranked=ranked,
        rejected=rejected,
        generated_count=len(candidates),
        feasible_count=len(ranked),
        optimality_gap=0.0 if ranked else None,
    )


__all__ = [
    "GasDispatchConstraintEvidence",
    "GasEnergyDispatchCandidate",
    "GasEnergySelectionResult",
    "GasEnergySelectionStatus",
    "RankedGasEnergyCandidate",
    "RejectedGasEnergyCandidate",
    "select_minimum_energy_dispatch",
]
