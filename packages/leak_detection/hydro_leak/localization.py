"""Contrat de résultat pour la localisation d'une suspicion de fuite.

La Phase 7 exige une localisation accompagnée d'incertitude. Ce module ne
choisit aucun algorithme : il valide et versionne uniquement un résultat produit
par une méthode explicitement identifiée.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LeakLocationEstimate:
    """Estimation de chaînage et intervalle associé sur un axe de conduite."""

    pipeline_ref: str
    pipeline_length_m: float
    estimated_chainage_m: float
    lower_chainage_m: float
    upper_chainage_m: float
    method_ref: str
    model_version: str
    evidence_ref: str

    def __post_init__(self) -> None:
        references = (
            self.pipeline_ref,
            self.method_ref,
            self.model_version,
            self.evidence_ref,
        )
        if any(not value.strip() for value in references):
            raise ValueError("Conduite, méthode, version de modèle et preuve sont obligatoires.")
        numeric = (
            self.pipeline_length_m,
            self.estimated_chainage_m,
            self.lower_chainage_m,
            self.upper_chainage_m,
        )
        if any(not math.isfinite(value) for value in numeric):
            raise ValueError("Les chaînages de localisation doivent être finis.")
        if self.pipeline_length_m <= 0:
            raise ValueError("La longueur de conduite doit être strictement positive.")
        if not 0 <= self.lower_chainage_m <= self.upper_chainage_m <= self.pipeline_length_m:
            raise ValueError("L'intervalle de localisation doit rester dans la conduite.")
        if not self.lower_chainage_m <= self.estimated_chainage_m <= self.upper_chainage_m:
            raise ValueError("Le chaînage estimé doit appartenir à son intervalle d'incertitude.")

    @property
    def uncertainty_width_m(self) -> float:
        return self.upper_chainage_m - self.lower_chainage_m

    @property
    def lower_margin_m(self) -> float:
        return self.estimated_chainage_m - self.lower_chainage_m

    @property
    def upper_margin_m(self) -> float:
        return self.upper_chainage_m - self.estimated_chainage_m


__all__ = ["LeakLocationEstimate"]
