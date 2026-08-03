"""Géométrie du pipeline : tronçons, accessoires et profil altimétrique.

Conventions (D07 § 2) :

- l'abscisse curviligne ``chainage_m`` croît dans le sens nominal d'écoulement ;
- l'altitude ``elevation_m`` est rapportée au datum géodésique du projet ;
- toutes les longueurs sont en mètres, les pressions en pascals **absolus**.

Le profil et la géométrie sont deux objets distincts : le profil décrit le terrain le long du
tracé, les tronçons décrivent la conduite. Un tronçon couvre un intervalle de chainage ; le
profil peut être plus finement échantillonné que le découpage en tronçons, et inversement.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from hydro_domain.enums import EquipmentStatus
from hydro_domain.interpolation import ExtrapolationPolicy, MonotoneTable
from hydro_shared.errors import ProfileError
from hydro_shared.units import Dimension, Measure

#: Rugosité absolue indicative de quelques matériaux, en mètres. Ces valeurs sont des ordres
#: de grandeur de littérature : elles servent d'aide à la saisie, jamais de valeur par défaut
#: silencieuse. La rugosité effective d'une conduite en service doit être calibrée.
TYPICAL_ROUGHNESS_M: dict[str, float] = {
    "carbon_steel_new": 4.5e-5,
    "carbon_steel_used": 2.0e-4,
    "stainless_steel": 1.5e-5,
    "cast_iron": 2.6e-4,
    "concrete": 3.0e-4,
    "hdpe": 7.0e-6,
}


@dataclass(frozen=True, slots=True)
class Fitting:
    """Accessoire générant une perte de charge singulière ``h_m = K · v²/(2g)``.

    ``k_coefficient`` est le coefficient de perte **par accessoire** ; ``quantity`` permet de
    regrouper des accessoires identiques sur un même tronçon.

    ``opening_ratio`` modélise une vanne partiellement fermée (scénario obligatoire du § 4.8) :
    le coefficient effectif est majoré par le facteur retourné par :meth:`effective_k`.
    """

    id: str
    kind: str
    k_coefficient: float
    quantity: int = 1
    chainage_m: float | None = None
    label: str | None = None
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    #: 1.0 = pleinement ouvert, 0.0 = fermé. Utilisé pour les vannes et les filtres colmatés.
    opening_ratio: float = 1.0

    def __post_init__(self) -> None:
        if self.k_coefficient < 0:
            raise ValueError(
                f"Accessoire {self.id} : le coefficient K ne peut pas être négatif "
                f"({self.k_coefficient})."
            )
        if self.quantity < 1:
            raise ValueError(f"Accessoire {self.id} : la quantité doit être au moins 1.")
        if not 0.0 <= self.opening_ratio <= 1.0:
            raise ValueError(
                f"Accessoire {self.id} : le taux d'ouverture doit appartenir à [0 ; 1] "
                f"({self.opening_ratio})."
            )

    def effective_k(self) -> float:
        """Coefficient K total de l'accessoire, ouverture partielle comprise.

        Le modèle d'obturation retenu suppose que la perte varie comme l'inverse du carré de
        la section de passage : ``K_eff = K / σ²`` avec ``σ`` le taux d'ouverture. C'est le
        comportement d'un orifice équivalent, cohérent avec la définition ``h = K v²/2g`` où
        ``v`` reste la vitesse dans la conduite pleine. Ce modèle est explicite et documenté ;
        pour une vanne réelle, une courbe ``Kv(course)`` constructeur doit lui être préférée.
        """
        if self.status is not EquipmentStatus.AVAILABLE:
            return 0.0
        if self.opening_ratio <= 0.0:
            return float("inf")
        return self.quantity * self.k_coefficient / (self.opening_ratio**2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "k_coefficient": self.k_coefficient,
            "quantity": self.quantity,
            "chainage_m": self.chainage_m,
            "status": self.status.value,
            "opening_ratio": self.opening_ratio,
        }


@dataclass(frozen=True, slots=True)
class PipeSegment:
    """Tronçon de conduite homogène (D-v2 § 4.4).

    Un tronçon est caractérisé par sa géométrie, son matériau, sa rugosité et sa pression
    maximale admissible. Les accessoires qu'il porte sont regroupés dans ``fittings``.
    """

    id: str
    sequence: int
    length_m: float
    inner_diameter_m: float
    roughness_m: float
    start_chainage_m: float = 0.0
    outer_diameter_m: float | None = None
    wall_thickness_m: float | None = None
    material: str | None = None
    #: Pression maximale admissible de service, en pascals **absolus** (contrôle C-004).
    maop_pa: float | None = None
    #: Pression minimale de service imposée par l'exploitant, en pascals absolus.
    minimum_pressure_pa: float | None = None
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    fittings: tuple[Fitting, ...] = ()
    label: str | None = None

    def __post_init__(self) -> None:
        if self.length_m <= 0:
            raise ValueError(
                f"Tronçon {self.id} : la longueur doit être strictement positive "
                f"({self.length_m} m)."
            )
        if self.inner_diameter_m <= 0:
            raise ValueError(
                f"Tronçon {self.id} : le diamètre intérieur doit être strictement positif "
                f"({self.inner_diameter_m} m)."
            )
        if self.roughness_m < 0:
            raise ValueError(
                f"Tronçon {self.id} : la rugosité absolue ne peut pas être négative "
                f"({self.roughness_m} m)."
            )
        if self.outer_diameter_m is not None and self.outer_diameter_m < self.inner_diameter_m:
            raise ValueError(
                f"Tronçon {self.id} : le diamètre extérieur ({self.outer_diameter_m} m) doit être "
                f"supérieur ou égal au diamètre intérieur ({self.inner_diameter_m} m)."
            )
        if self.wall_thickness_m is not None and self.wall_thickness_m <= 0:
            raise ValueError(
                f"Tronçon {self.id} : l'épaisseur de paroi doit être strictement positive."
            )
        if self.maop_pa is not None and self.maop_pa <= 0:
            raise ValueError(
                f"Tronçon {self.id} : la pression maximale admissible doit être strictement "
                f"positive et exprimée en pascals absolus."
            )

    @property
    def end_chainage_m(self) -> float:
        return self.start_chainage_m + self.length_m

    @property
    def area_m2(self) -> float:
        """Section de passage ``A = π D² / 4``."""
        from math import pi

        return pi * self.inner_diameter_m**2 / 4.0

    @property
    def volume_m3(self) -> float:
        """Volume interne du tronçon, utile aux bilans matière."""
        return self.area_m2 * self.length_m

    @property
    def relative_roughness(self) -> float:
        """Rugosité relative ``ε/D``, argument des corrélations de frottement."""
        return self.roughness_m / self.inner_diameter_m

    @property
    def is_in_service(self) -> bool:
        return self.status is EquipmentStatus.AVAILABLE

    def total_fitting_k(self) -> float:
        """Somme ``ΣK`` des accessoires en service portés par le tronçon."""
        return sum(f.effective_k() for f in self.fittings)

    def velocity(self, flow_m3_s: float) -> float:
        """Vitesse débitante ``v = Q / A`` en m/s."""
        return flow_m3_s / self.area_m2

    def with_status(self, status: EquipmentStatus) -> PipeSegment:
        """Copie du tronçon avec un autre état, pour l'application d'un override de scénario."""
        return PipeSegment(
            id=self.id,
            sequence=self.sequence,
            length_m=self.length_m,
            inner_diameter_m=self.inner_diameter_m,
            roughness_m=self.roughness_m,
            start_chainage_m=self.start_chainage_m,
            outer_diameter_m=self.outer_diameter_m,
            wall_thickness_m=self.wall_thickness_m,
            material=self.material,
            maop_pa=self.maop_pa,
            minimum_pressure_pa=self.minimum_pressure_pa,
            status=status,
            fittings=self.fittings,
            label=self.label,
        )

    def measures(self) -> dict[str, Measure]:
        return {
            "length": Measure.si(self.length_m, Dimension.LENGTH),
            "inner_diameter": Measure.si(self.inner_diameter_m, Dimension.DIAMETER),
            "roughness": Measure.si(self.roughness_m, Dimension.ROUGHNESS),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sequence": self.sequence,
            "label": self.label,
            "length_m": self.length_m,
            "inner_diameter_m": self.inner_diameter_m,
            "outer_diameter_m": self.outer_diameter_m,
            "wall_thickness_m": self.wall_thickness_m,
            "roughness_m": self.roughness_m,
            "material": self.material,
            "maop_pa": self.maop_pa,
            "minimum_pressure_pa": self.minimum_pressure_pa,
            "start_chainage_m": self.start_chainage_m,
            "status": self.status.value,
            "fittings": [f.as_dict() for f in self.fittings],
        }


@dataclass(frozen=True, slots=True)
class ProfilePoint:
    """Point du profil altimétrique."""

    chainage_m: float
    elevation_m: float
    latitude: float | None = None
    longitude: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "chainage_m": self.chainage_m,
            "elevation_m": self.elevation_m,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class ElevationProfile:
    """Profil altimétrique interpolable le long du tracé.

    Contrôles à la construction (FR-MOD-002, règle DQ-003) : au moins deux points, chainages
    strictement croissants, aucun doublon. Un profil non ordonné lève ``ERR_PROFILE_NOT_MONOTONIC``
    et le calcul n'est pas lancé.
    """

    __slots__ = ("_points", "_table")

    def __init__(self, points: Sequence[ProfilePoint]) -> None:
        if len(points) < 2:
            raise ProfileError(
                "Un profil altimétrique exige au moins deux points.", point_count=len(points)
            )
        ordered = list(points)
        self._points = tuple(ordered)
        self._table = MonotoneTable(
            [p.chainage_m for p in ordered],
            [p.elevation_m for p in ordered],
            extrapolation=ExtrapolationPolicy.CLAMP,
            label="profil altimétrique",
            error_type=ProfileError,
        )

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[float, float]]) -> ElevationProfile:
        """Construit un profil depuis des couples ``(chainage_m, elevation_m)``."""
        return cls([ProfilePoint(chainage_m=c, elevation_m=z) for c, z in pairs])

    @classmethod
    def from_kilometre_pairs(cls, pairs: Iterable[tuple[float, float]]) -> ElevationProfile:
        """Construit un profil depuis des couples ``(chainage_km, elevation_m)``."""
        return cls([ProfilePoint(chainage_m=c * 1000.0, elevation_m=z) for c, z in pairs])

    @property
    def points(self) -> tuple[ProfilePoint, ...]:
        return self._points

    @property
    def length_m(self) -> float:
        return self._points[-1].chainage_m - self._points[0].chainage_m

    @property
    def domain(self) -> tuple[float, float]:
        return self._table.domain

    def elevation_at(self, chainage_m: float) -> float:
        """Altitude interpolée. Hors domaine, l'altitude extrême est maintenue.

        Le maintien (plutôt que l'extrapolation linéaire) évite de fabriquer un relief
        imaginaire au-delà des points levés ; les dépassements de domaine restent détectés
        par la validation du réseau.
        """
        return self._table.evaluate(chainage_m).value

    def elevation_change(self, from_chainage_m: float, to_chainage_m: float) -> float:
        """Dénivelé ``z(to) − z(from)``, positif en montée."""
        return self.elevation_at(to_chainage_m) - self.elevation_at(from_chainage_m)

    def sample(self, step_m: float) -> list[ProfilePoint]:
        """Ré-échantillonne le profil à pas constant, points d'origine inclus.

        Les points d'origine sont conservés : le sommet d'une côte ne doit jamais disparaître
        d'un ré-échantillonnage, sous peine de masquer un point critique de pression.
        """
        if step_m <= 0:
            raise ProfileError(
                "Le pas d'échantillonnage doit être strictement positif.", step_m=step_m
            )
        start, end = self.domain
        chainages: set[float] = {p.chainage_m for p in self._points}
        current = start
        while current < end:
            chainages.add(current)
            current += step_m
        chainages.add(end)
        return [
            ProfilePoint(chainage_m=c, elevation_m=self.elevation_at(c)) for c in sorted(chainages)
        ]

    def summit_chainages(self) -> list[float]:
        """Chainages des maxima locaux du relief.

        Ces points sont les candidats naturels à une dépression : ils sont examinés en
        priorité par les contrôles C-002 (pression sous la pression de vapeur) et par la
        détection de zone gravitaire.
        """
        summits: list[float] = []
        pts = self._points
        for i in range(1, len(pts) - 1):
            if (
                pts[i].elevation_m >= pts[i - 1].elevation_m
                and pts[i].elevation_m >= pts[i + 1].elevation_m
            ):
                summits.append(pts[i].chainage_m)
        return summits

    def as_dict(self) -> dict[str, Any]:
        return {"points": [p.as_dict() for p in self._points]}

    def __len__(self) -> int:
        return len(self._points)

    def __repr__(self) -> str:  # pragma: no cover - confort de débogage
        lo, hi = self.domain
        return f"ElevationProfile({len(self)} points, {lo / 1000:.1f}–{hi / 1000:.1f} km)"


def validate_segment_chain(segments: Sequence[PipeSegment]) -> list[str]:
    """Vérifie qu'une suite de tronçons forme une chaîne continue et ordonnée.

    Retourne la liste des anomalies détectées, vide si la chaîne est cohérente. Le contrôle
    porte sur l'ordre des séquences, la continuité des chainages et l'unicité des
    identifiants (FR-MOD-008).
    """
    problems: list[str] = []
    if not segments:
        return ["Le pipeline ne comporte aucun tronçon."]

    identifiers = [s.id for s in segments]
    duplicates = {i for i in identifiers if identifiers.count(i) > 1}
    if duplicates:
        problems.append(f"Identifiants de tronçon dupliqués : {sorted(duplicates)}.")

    ordered = sorted(segments, key=lambda s: s.sequence)
    for previous, current in pairwise(ordered):
        if current.sequence == previous.sequence:
            problems.append(
                f"Deux tronçons portent le numéro de séquence {current.sequence} "
                f"({previous.id} et {current.id})."
            )
        gap = current.start_chainage_m - previous.end_chainage_m
        if abs(gap) > 1e-6:
            problems.append(
                f"Discontinuité de {gap:+.3f} m entre les tronçons {previous.id} "
                f"(fin à {previous.end_chainage_m:.3f} m) et {current.id} "
                f"(début à {current.start_chainage_m:.3f} m)."
            )
    return problems
