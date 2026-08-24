"""Fusion explicable de signaux de suspicion de fuite.

Le module agrège des preuves déjà normalisées dans [0, 1] avec des poids
explicitement fournis et une provenance obligatoire. Il ne choisit aucun seuil
d'alarme, n'exécute aucune commande et ne transforme pas le score en décision
opérationnelle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidenceSignal:
    """Signal normalisé produit par un détecteur ou un contrôle indépendant."""

    detector_id: str
    score: float
    weight: float
    source_ref: str
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.detector_id.strip():
            raise ValueError("L'identifiant du détecteur est obligatoire.")
        if not math.isfinite(self.score) or self.score < 0 or self.score > 1:
            raise ValueError("Le score de preuve doit appartenir à [0, 1].")
        if not math.isfinite(self.weight) or self.weight <= 0:
            raise ValueError("Le poids d'une preuve doit être fini et strictement positif.")
        if not self.source_ref.strip():
            raise ValueError("La provenance de la preuve est obligatoire.")
        if self.note is not None and not self.note.strip():
            raise ValueError("La note de preuve ne peut pas être vide.")


@dataclass(frozen=True, slots=True)
class EvidenceContribution:
    """Contribution normalisée d'un signal au score global."""

    detector_id: str
    normalized_weight: float
    score: float
    contribution: float
    source_ref: str


@dataclass(frozen=True, slots=True)
class EvidenceFusionResult:
    """Score agrégé et contributions, sans seuil de décision implicite."""

    score: float
    total_weight: float
    contributions: tuple[EvidenceContribution, ...]


def fuse_evidence(signals: tuple[EvidenceSignal, ...]) -> EvidenceFusionResult:
    """Calcule une moyenne pondérée et publie chaque contribution.

    Les poids doivent être définis avant l'évaluation sur le jeu de validation
    si cette fonction est utilisée dans une campagne de performance.
    """

    if not signals:
        raise ValueError("La fusion de preuves exige au moins un signal.")
    detector_ids = [signal.detector_id for signal in signals]
    if len(detector_ids) != len(set(detector_ids)):
        raise ValueError("Chaque détecteur ne peut contribuer qu'une fois à une fusion.")
    total_weight = math.fsum(signal.weight for signal in signals)
    contributions = tuple(
        EvidenceContribution(
            detector_id=signal.detector_id,
            normalized_weight=signal.weight / total_weight,
            score=signal.score,
            contribution=signal.score * signal.weight / total_weight,
            source_ref=signal.source_ref,
        )
        for signal in signals
    )
    score = math.fsum(contribution.contribution for contribution in contributions)
    return EvidenceFusionResult(
        score=score,
        total_weight=total_weight,
        contributions=contributions,
    )


__all__ = [
    "EvidenceContribution",
    "EvidenceFusionResult",
    "EvidenceSignal",
    "fuse_evidence",
]
