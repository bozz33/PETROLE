"""Pipeline liquide longue distance : assemblage tronçons + profil + stations.

Le MVP privilégie la topologie réellement exploitée sur un oléoduc : une **chaîne orientée**
de tronçons, jalonnée de stations de pompage, avec un réservoir ou une pression imposée à
chaque extrémité (D-v2 § 4.4 et § 5.1).

Les réseaux ramifiés simples nœuds–branches restent couverts par le graphe générique
(:mod:`hydro_domain.network`) et l'adaptateur pandapipes ; ils ne sont pas la topologie
principale de l'oléoduc.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from hydro_domain.enums import EquipmentStatus
from hydro_domain.geometry import ElevationProfile, PipeSegment, validate_segment_chain
from hydro_domain.stations import PumpStation
from hydro_domain.tanks import Tank
from hydro_shared.errors import TopologyError


@dataclass(frozen=True, slots=True)
class InjectionPoint:
    """Injection (+) ou soutirage (−) intermédiaire, en m³/s (FR-LIQ-006).

    Un débit positif ajoute du produit à la ligne, un débit négatif en retire. La conservation
    de masse le long du pipeline en tient compte tronçon par tronçon.
    """

    id: str
    chainage_m: float
    flow_m3_s: float
    label: str | None = None
    status: EquipmentStatus = EquipmentStatus.AVAILABLE

    @property
    def is_active(self) -> bool:
        return self.status is EquipmentStatus.AVAILABLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "chainage_m": self.chainage_m,
            "flow_m3_s": self.flow_m3_s,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class Pipeline:
    """Oléoduc complet : géométrie, relief, stations, points singuliers et bacs d'extrémité.

    Invariants garantis par :meth:`validate_topology` :

    - les tronçons forment une chaîne continue et ordonnée ;
    - le profil couvre l'intégralité du linéaire ;
    - chaque station et chaque point d'injection est situé dans le linéaire ;
    - les identifiants sont uniques.
    """

    id: str
    name: str
    segments: tuple[PipeSegment, ...]
    profile: ElevationProfile
    stations: tuple[PumpStation, ...] = ()
    injections: tuple[InjectionPoint, ...] = ()
    origin_tank: Tank | None = None
    destination_tank: Tank | None = None
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.segments:
            raise TopologyError("Un pipeline doit comporter au moins un tronçon.", pipeline=self.id)
        object.__setattr__(self, "segments", tuple(sorted(self.segments, key=lambda s: s.sequence)))
        object.__setattr__(
            self, "stations", tuple(sorted(self.stations, key=lambda s: s.chainage_m))
        )
        object.__setattr__(
            self, "injections", tuple(sorted(self.injections, key=lambda i: i.chainage_m))
        )

    # ------------------------------------------------------------------ géométrie

    @property
    def start_chainage_m(self) -> float:
        return self.segments[0].start_chainage_m

    @property
    def end_chainage_m(self) -> float:
        return self.segments[-1].end_chainage_m

    @property
    def total_length_m(self) -> float:
        return sum(s.length_m for s in self.segments)

    @property
    def total_volume_m3(self) -> float:
        """Volume interne total, utile au bilan matière et au temps de transit."""
        return sum(s.volume_m3 for s in self.segments)

    @property
    def display_name(self) -> str:
        return self.label or self.name

    def elevation_at(self, chainage_m: float) -> float:
        return self.profile.elevation_at(chainage_m)

    @property
    def static_head_m(self) -> float:
        """Dénivelé total entre l'origine et la destination, positif en montée."""
        return self.elevation_at(self.end_chainage_m) - self.elevation_at(self.start_chainage_m)

    def segment_at(self, chainage_m: float) -> PipeSegment:
        """Tronçon contenant le chainage indiqué."""
        for segment in self.segments:
            if segment.start_chainage_m <= chainage_m <= segment.end_chainage_m:
                return segment
        raise TopologyError(
            f"Aucun tronçon ne couvre le chainage {chainage_m:.3f} m.",
            pipeline=self.id,
            chainage_m=chainage_m,
        )

    def station_at(self, chainage_m: float, tolerance_m: float = 1.0) -> PumpStation | None:
        """Station située au chainage indiqué, à la tolérance près."""
        for station in self.stations:
            if abs(station.chainage_m - chainage_m) <= tolerance_m:
                return station
        return None

    # ------------------------------------------------------------------ débits

    def flow_at(self, chainage_m: float, inlet_flow_m3_s: float) -> float:
        """Débit circulant au chainage indiqué, injections et soutirages cumulés.

        Le débit d'entrée est celui de l'origine du pipeline ; chaque point actif situé en
        amont du chainage modifie le débit transporté (conservation de masse, contrôle C-001).
        """
        flow = inlet_flow_m3_s
        for injection in self.injections:
            if injection.is_active and injection.chainage_m <= chainage_m:
                flow += injection.flow_m3_s
        return flow

    @property
    def net_injection_m3_s(self) -> float:
        """Somme algébrique des injections et soutirages actifs."""
        return sum(i.flow_m3_s for i in self.injections if i.is_active)

    def outlet_flow(self, inlet_flow_m3_s: float) -> float:
        """Débit en sortie de pipeline pour un débit d'entrée donné."""
        return inlet_flow_m3_s + self.net_injection_m3_s

    # ------------------------------------------------------------------ validation

    def validate_topology(self) -> list[str]:
        """Contrôles de cohérence avant calcul (FR-MOD-008).

        Retourne la liste des anomalies ; une liste vide signifie que le pipeline est
        calculable du point de vue topologique.
        """
        problems = validate_segment_chain(self.segments)

        profile_start, profile_end = self.profile.domain
        if profile_start > self.start_chainage_m + 1e-6:
            problems.append(
                f"Le profil altimétrique commence au PK {profile_start / 1000:.3f} km alors que le "
                f"pipeline commence au PK {self.start_chainage_m / 1000:.3f} km."
            )
        if profile_end < self.end_chainage_m - 1e-6:
            problems.append(
                f"Le profil altimétrique s'arrête au PK {profile_end / 1000:.3f} km alors que le "
                f"pipeline s'achève au PK {self.end_chainage_m / 1000:.3f} km."
            )

        station_ids = [s.id for s in self.stations]
        duplicates = {i for i in station_ids if station_ids.count(i) > 1}
        if duplicates:
            problems.append(f"Identifiants de station dupliqués : {sorted(duplicates)}.")

        for station in self.stations:
            if not self.start_chainage_m - 1e-6 <= station.chainage_m <= self.end_chainage_m + 1e-6:
                problems.append(
                    f"La station « {station.name} » est située au PK "
                    f"{station.chainage_m / 1000:.3f} km, hors du linéaire du pipeline."
                )
            if not station.groups and station.status is EquipmentStatus.AVAILABLE:
                problems.append(
                    f"La station « {station.name} » est déclarée disponible mais ne contient "
                    f"aucune pompe."
                )

        for injection in self.injections:
            if (
                not self.start_chainage_m - 1e-6
                <= injection.chainage_m
                <= self.end_chainage_m + 1e-6
            ):
                problems.append(
                    f"Le point « {injection.id} » est situé au PK "
                    f"{injection.chainage_m / 1000:.3f} km, hors du linéaire du pipeline."
                )

        if all(not s.is_in_service for s in self.segments):
            problems.append(
                "Tous les tronçons sont hors service : aucun écoulement n'est possible."
            )

        return problems

    # ------------------------------------------------------------------ scénarios

    def with_stations(self, stations: Sequence[PumpStation]) -> Pipeline:
        """Copie du pipeline avec un autre jeu de stations (application d'overrides)."""
        return Pipeline(
            id=self.id,
            name=self.name,
            segments=self.segments,
            profile=self.profile,
            stations=tuple(stations),
            injections=self.injections,
            origin_tank=self.origin_tank,
            destination_tank=self.destination_tank,
            label=self.label,
            metadata=self.metadata,
        )

    def with_segments(self, segments: Sequence[PipeSegment]) -> Pipeline:
        """Copie du pipeline avec un autre jeu de tronçons."""
        return Pipeline(
            id=self.id,
            name=self.name,
            segments=tuple(segments),
            profile=self.profile,
            stations=self.stations,
            injections=self.injections,
            origin_tank=self.origin_tank,
            destination_tank=self.destination_tank,
            label=self.label,
            metadata=self.metadata,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "total_length_m": self.total_length_m,
            "segments": [s.as_dict() for s in self.segments],
            "profile": self.profile.as_dict(),
            "stations": [s.as_dict() for s in self.stations],
            "injections": [i.as_dict() for i in self.injections],
            "origin_tank": self.origin_tank.as_dict() if self.origin_tank else None,
            "destination_tank": self.destination_tank.as_dict() if self.destination_tank else None,
        }
