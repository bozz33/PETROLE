"""Évaluation de santé d'un connecteur industriel en lecture seule.

Les objectifs sont fournis par le protocole de déploiement. Le module ne crée
aucune alarme procédé et n'invente pas de seuil OT générique.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectorHealthObjectives:
    """Objectifs de qualité de liaison approuvés pour un connecteur."""

    maximum_source_age_s: float
    maximum_gap_count: int
    maximum_bad_quality_fraction: float
    maximum_reconnect_count: int

    def __post_init__(self) -> None:
        if not math.isfinite(self.maximum_source_age_s) or self.maximum_source_age_s < 0:
            raise ValueError("L'âge source maximal doit être fini et positif ou nul.")
        if self.maximum_gap_count < 0 or self.maximum_reconnect_count < 0:
            raise ValueError("Les nombres maximaux de trous/reconnexions doivent être positifs.")
        if (
            not math.isfinite(self.maximum_bad_quality_fraction)
            or self.maximum_bad_quality_fraction < 0
            or self.maximum_bad_quality_fraction > 1
        ):
            raise ValueError("La fraction Bad maximale doit appartenir à [0, 1].")


@dataclass(frozen=True, slots=True)
class ConnectorHealthEvidence:
    """Mesures observées sur une fenêtre de supervision."""

    source_age_s: float
    gap_count: int
    sample_count: int
    bad_quality_count: int
    reconnect_count: int

    def __post_init__(self) -> None:
        if not math.isfinite(self.source_age_s) or self.source_age_s < 0:
            raise ValueError("L'âge source observé doit être fini et positif ou nul.")
        counts = (self.gap_count, self.sample_count, self.bad_quality_count, self.reconnect_count)
        if any(value < 0 for value in counts):
            raise ValueError("Les compteurs de santé connecteur doivent être positifs ou nuls.")
        if self.bad_quality_count > self.sample_count:
            raise ValueError(
                "Le nombre de valeurs Bad ne peut pas dépasser le nombre d'échantillons."
            )

    @property
    def bad_quality_fraction(self) -> float:
        return self.bad_quality_count / self.sample_count if self.sample_count else 0.0


@dataclass(frozen=True, slots=True)
class ConnectorHealthAssessment:
    """Verdict analytique du connecteur, sans effet sur la conduite."""

    healthy: bool
    bad_quality_fraction: float
    violations: tuple[str, ...]


def assess_connector_health(
    objectives: ConnectorHealthObjectives,
    evidence: ConnectorHealthEvidence,
) -> ConnectorHealthAssessment:
    """Compare les mesures aux objectifs fournis sans marge implicite."""

    violations: list[str] = []
    if evidence.source_age_s > objectives.maximum_source_age_s:
        violations.append("source_age_above_objective")
    if evidence.gap_count > objectives.maximum_gap_count:
        violations.append("sequence_gaps_above_objective")
    if evidence.bad_quality_fraction > objectives.maximum_bad_quality_fraction:
        violations.append("bad_quality_fraction_above_objective")
    if evidence.reconnect_count > objectives.maximum_reconnect_count:
        violations.append("reconnect_count_above_objective")
    return ConnectorHealthAssessment(
        healthy=not violations,
        bad_quality_fraction=evidence.bad_quality_fraction,
        violations=tuple(violations),
    )


__all__ = [
    "ConnectorHealthAssessment",
    "ConnectorHealthEvidence",
    "ConnectorHealthObjectives",
    "assess_connector_health",
]
