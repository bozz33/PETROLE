"""Limites de fonctionnement d'un compresseur issues d'une source fournisseur.

La brique interpole uniquement des limites minimales/maximales de débit massique
fournies pour des vitesses données. Elle ne constitue pas un anti-surge actif,
ne commande aucun recycle et n'invente aucune marge de sûreté.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True, slots=True)
class CompressorFlowLimitPoint:
    """Limites de débit disponibles sur une ligne de vitesse fournisseur."""

    speed_rpm: float
    minimum_mass_flow_kg_s: float
    maximum_mass_flow_kg_s: float

    def __post_init__(self) -> None:
        values = (self.speed_rpm, self.minimum_mass_flow_kg_s, self.maximum_mass_flow_kg_s)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("Vitesse et limites de débit doivent être finies et positives.")
        if self.minimum_mass_flow_kg_s >= self.maximum_mass_flow_kg_s:
            raise ValueError("La limite minimale doit être inférieure à la limite maximale.")


@dataclass(frozen=True, slots=True)
class CompressorOperatingEnvelope:
    """Enveloppe versionnée séparée de la carte de performance."""

    source_ref: str
    version: str
    points: tuple[CompressorFlowLimitPoint, ...]

    def __post_init__(self) -> None:
        if not self.source_ref.strip() or not self.version.strip():
            raise ValueError("La provenance et la version de l'enveloppe sont obligatoires.")
        if not self.points:
            raise ValueError("L'enveloppe compresseur doit contenir au moins un point de vitesse.")
        speeds = [point.speed_rpm for point in self.points]
        if speeds != sorted(speeds) or len(set(speeds)) != len(speeds):
            raise ValueError("Les vitesses de l'enveloppe doivent être strictement croissantes.")


@dataclass(frozen=True, slots=True)
class CompressorEnvelopeAssessment:
    """Position d'un point par rapport aux limites publiées."""

    speed_rpm: float
    mass_flow_kg_s: float
    minimum_mass_flow_kg_s: float
    maximum_mass_flow_kg_s: float
    minimum_flow_margin_kg_s: float
    maximum_flow_margin_kg_s: float
    inside_envelope: bool
    source_ref: str
    envelope_version: str


def _limits_at_speed(
    envelope: CompressorOperatingEnvelope,
    speed_rpm: float,
) -> tuple[float, float]:
    points = envelope.points
    if speed_rpm < points[0].speed_rpm or speed_rpm > points[-1].speed_rpm:
        raise ValueError("La vitesse demandée est hors du domaine de l'enveloppe compresseur.")
    if len(points) == 1:
        if not math.isclose(speed_rpm, points[0].speed_rpm, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                "Une enveloppe à une vitesse n'autorise aucune interpolation en vitesse."
            )
        return points[0].minimum_mass_flow_kg_s, points[0].maximum_mass_flow_kg_s

    for lower, upper in pairwise(points):
        if lower.speed_rpm <= speed_rpm <= upper.speed_rpm:
            fraction = (speed_rpm - lower.speed_rpm) / (upper.speed_rpm - lower.speed_rpm)
            minimum_flow = lower.minimum_mass_flow_kg_s + fraction * (
                upper.minimum_mass_flow_kg_s - lower.minimum_mass_flow_kg_s
            )
            maximum_flow = lower.maximum_mass_flow_kg_s + fraction * (
                upper.maximum_mass_flow_kg_s - lower.maximum_mass_flow_kg_s
            )
            return minimum_flow, maximum_flow
    raise RuntimeError("La vitesse n'a pas pu être encadrée par l'enveloppe.")


def assess_compressor_envelope(
    envelope: CompressorOperatingEnvelope,
    *,
    speed_rpm: float,
    mass_flow_kg_s: float,
) -> CompressorEnvelopeAssessment:
    """Évalue le point sans seuil de marge supplémentaire ni logique de commande."""

    if not math.isfinite(speed_rpm) or speed_rpm <= 0:
        raise ValueError("La vitesse doit être finie et positive.")
    if not math.isfinite(mass_flow_kg_s) or mass_flow_kg_s <= 0:
        raise ValueError("Le débit massique doit être fini et positif.")
    minimum_flow, maximum_flow = _limits_at_speed(envelope, speed_rpm)
    return CompressorEnvelopeAssessment(
        speed_rpm=speed_rpm,
        mass_flow_kg_s=mass_flow_kg_s,
        minimum_mass_flow_kg_s=minimum_flow,
        maximum_mass_flow_kg_s=maximum_flow,
        minimum_flow_margin_kg_s=mass_flow_kg_s - minimum_flow,
        maximum_flow_margin_kg_s=maximum_flow - mass_flow_kg_s,
        inside_envelope=minimum_flow <= mass_flow_kg_s <= maximum_flow,
        source_ref=envelope.source_ref,
        envelope_version=envelope.version,
    )


__all__ = [
    "CompressorEnvelopeAssessment",
    "CompressorFlowLimitPoint",
    "CompressorOperatingEnvelope",
    "assess_compressor_envelope",
]
