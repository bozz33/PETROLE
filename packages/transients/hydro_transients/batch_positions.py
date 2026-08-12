"""Position spatiale idéale des interfaces multiproduits par volume déplacé.

Cette brique transforme un volume de déplacement explicitement fourni en
abscisse le long d'une conduite dont la géométrie interne est connue. Le modèle
est volontairement un déplacement piston idéal : aucune dispersion, largeur
d'interface, contamination, diffusion ou correction thermophysique n'est
ajoutée implicitement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from hydro_transients.multiproduct import BatchSequence


@dataclass(frozen=True, slots=True)
class PipelineVolumeSegment:
    """Segment géométrique utilisé uniquement pour convertir volume en distance."""

    segment_id: str
    length_m: float
    internal_area_m2: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.segment_id.strip() or not self.source_ref.strip():
            raise ValueError("Le segment et sa provenance sont obligatoires.")
        if not math.isfinite(self.length_m) or self.length_m <= 0:
            raise ValueError("La longueur du segment doit être finie et strictement positive.")
        if not math.isfinite(self.internal_area_m2) or self.internal_area_m2 <= 0:
            raise ValueError("La section interne doit être finie et strictement positive.")

    @property
    def internal_volume_m3(self) -> float:
        return self.length_m * self.internal_area_m2


@dataclass(frozen=True, slots=True)
class PipelineVolumeProfile:
    """Profil orienté inlet→outlet et capacité géométrique totale."""

    segments: tuple[PipelineVolumeSegment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("Le profil volumique doit contenir au moins un segment.")
        segment_ids = tuple(segment.segment_id for segment in self.segments)
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("Les identifiants de segments doivent être uniques.")

    @property
    def total_length_m(self) -> float:
        return math.fsum(segment.length_m for segment in self.segments)

    @property
    def total_internal_volume_m3(self) -> float:
        return math.fsum(segment.internal_volume_m3 for segment in self.segments)


class InterfaceSpatialStatus(StrEnum):
    """État géométrique d'une interface dans le déplacement piston idéal."""

    PENDING = "pending"
    IN_PIPELINE = "in_pipeline"
    EXITED = "exited"


@dataclass(frozen=True, slots=True)
class SpatialProductInterface:
    upstream_batch_id: str
    downstream_batch_id: str
    injected_interface_volume_m3: float
    travelled_volume_m3: float
    status: InterfaceSpatialStatus
    x_m: float | None
    segment_id: str | None


def _locate_volume_in_profile(
    profile: PipelineVolumeProfile,
    travelled_volume_m3: float,
) -> tuple[float, str]:
    remaining = travelled_volume_m3
    cumulative_length = 0.0
    for segment in profile.segments:
        segment_volume = segment.internal_volume_m3
        if remaining <= segment_volume:
            x_m = cumulative_length + remaining / segment.internal_area_m2
            return x_m, segment.segment_id
        remaining -= segment_volume
        cumulative_length += segment.length_m
    # L'appelant filtre les volumes strictement supérieurs à la capacité.
    return profile.total_length_m, profile.segments[-1].segment_id


def locate_batch_interfaces(
    sequence: BatchSequence,
    profile: PipelineVolumeProfile,
    *,
    cumulative_displaced_volume_m3: float,
) -> tuple[SpatialProductInterface, ...]:
    """Projette les interfaces logiques sur l'axe spatial de la conduite.

    Pour une interface créée après ``V_interface`` de volume injecté, le volume
    parcouru dans la conduite vaut ``V_déplacé - V_interface``. Une valeur
    négative signifie que cette interface n'a pas encore été injectée. Une
    valeur supérieure à la capacité interne signifie qu'elle a quitté la ligne.
    """

    if (
        not math.isfinite(cumulative_displaced_volume_m3)
        or cumulative_displaced_volume_m3 < 0
    ):
        raise ValueError("Le volume déplacé cumulé doit être fini et positif ou nul.")

    capacity = profile.total_internal_volume_m3
    positions: list[SpatialProductInterface] = []
    for interface in sequence.interfaces:
        travelled = cumulative_displaced_volume_m3 - interface.cumulative_volume_m3
        if travelled < 0:
            positions.append(
                SpatialProductInterface(
                    upstream_batch_id=interface.upstream_batch_id,
                    downstream_batch_id=interface.downstream_batch_id,
                    injected_interface_volume_m3=interface.cumulative_volume_m3,
                    travelled_volume_m3=travelled,
                    status=InterfaceSpatialStatus.PENDING,
                    x_m=None,
                    segment_id=None,
                )
            )
            continue
        if travelled > capacity:
            positions.append(
                SpatialProductInterface(
                    upstream_batch_id=interface.upstream_batch_id,
                    downstream_batch_id=interface.downstream_batch_id,
                    injected_interface_volume_m3=interface.cumulative_volume_m3,
                    travelled_volume_m3=travelled,
                    status=InterfaceSpatialStatus.EXITED,
                    x_m=None,
                    segment_id=None,
                )
            )
            continue

        x_m, segment_id = _locate_volume_in_profile(profile, travelled)
        positions.append(
            SpatialProductInterface(
                upstream_batch_id=interface.upstream_batch_id,
                downstream_batch_id=interface.downstream_batch_id,
                injected_interface_volume_m3=interface.cumulative_volume_m3,
                travelled_volume_m3=travelled,
                status=InterfaceSpatialStatus.IN_PIPELINE,
                x_m=x_m,
                segment_id=segment_id,
            )
        )
    return tuple(positions)


__all__ = [
    "InterfaceSpatialStatus",
    "PipelineVolumeProfile",
    "PipelineVolumeSegment",
    "SpatialProductInterface",
    "locate_batch_interfaces",
]
