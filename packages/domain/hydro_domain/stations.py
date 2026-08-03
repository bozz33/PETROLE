"""Stations de pompage : montage des pompes, limites de pression et NPSH.

Une station regroupe un nombre configurable de pompes (FR-GEN-001 : aucun nombre fixe n'est
codé en dur). Le montage retenu au MVP couvre les trois cas d'exploitation courants :

- **série** : les hauteurs s'additionnent au même débit ;
- **parallèle** : les débits s'additionnent à la même hauteur ;
- **groupes série-parallèle simples** : plusieurs groupes en parallèle, chaque groupe étant
  une file de pompes en série.

La combinaison en parallèle de pompes **différentes** exige de résoudre le partage de débit ;
c'est le rôle de :meth:`PumpStation.combined_head`, qui résout l'équilibre par dichotomie sur
la hauteur commune (cas de validation VAL-PMP-005).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from hydro_domain.enums import EquipmentStatus, PumpArrangement
from hydro_domain.pumps import CurveEvaluation, G, PumpInstance
from hydro_shared.errors import InvalidInputError

#: Tolérance de la dichotomie de partage de débit en parallèle, en m³/s.
PARALLEL_SHARING_TOLERANCE_M3_S = 1e-10
#: Nombre maximal d'itérations de la dichotomie de partage.
PARALLEL_SHARING_MAX_ITERATIONS = 200


@dataclass(frozen=True, slots=True)
class PumpGroup:
    """File de pompes en série formant une branche du collecteur de la station."""

    id: str
    pumps: tuple[PumpInstance, ...]
    label: str | None = None

    @property
    def active_pumps(self) -> tuple[PumpInstance, ...]:
        return tuple(p for p in self.pumps if p.is_active)

    @property
    def is_active(self) -> bool:
        return bool(self.active_pumps)

    def head(self, flow_m3_s: float) -> float:
        """Hauteur du groupe : somme des hauteurs des pompes actives au débit commun."""
        return sum(p.head(flow_m3_s) for p in self.active_pumps)

    def max_head(self) -> float:
        """Hauteur à débit nul du groupe, borne supérieure de sa caractéristique."""
        return self.head(0.0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "pumps": [p.as_dict() for p in self.pumps],
        }


@dataclass(frozen=True, slots=True)
class StationEvaluation:
    """Point de fonctionnement d'une station à un débit donné."""

    head_m: float
    hydraulic_power_w: float
    absorbed_power_w: float | None
    efficiency: float | None
    active_pump_count: int
    #: Débit traversant chaque pompe active, indexé par identifiant de pompe.
    flow_per_pump_m3_s: dict[str, float] = field(default_factory=dict)
    #: Évaluation détaillée de chaque pompe active.
    pump_evaluations: dict[str, CurveEvaluation] = field(default_factory=dict)
    extrapolated: bool = False
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "head_m": self.head_m,
            "hydraulic_power_w": self.hydraulic_power_w,
            "absorbed_power_w": self.absorbed_power_w,
            "efficiency": self.efficiency,
            "active_pump_count": self.active_pump_count,
            "flow_per_pump_m3_s": dict(self.flow_per_pump_m3_s),
            "pump_evaluations": {k: v.as_dict() for k, v in self.pump_evaluations.items()},
            "extrapolated": self.extrapolated,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class PumpStation:
    """Station de pompage située à un chainage donné du tracé.

    Les limites ``suction_pressure_min_pa`` et ``discharge_pressure_max_pa`` sont exprimées en
    pascals **absolus** et alimentent les contrôles C-004 et le contrôle de pression
    d'aspiration.

    ``bypass_k`` décrit les pertes du chemin de contournement lorsque la station est bypassée
    (scénario obligatoire « Bypass » du § 4.8) : le fluide traverse alors la station sans
    recevoir d'énergie, mais en subissant la perte du collecteur de contournement.
    """

    id: str
    name: str
    chainage_m: float
    elevation_m: float
    groups: tuple[PumpGroup, ...] = ()
    arrangement: PumpArrangement = PumpArrangement.SERIES
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    #: Pression minimale admissible à l'aspiration du collecteur, en Pa absolus.
    suction_pressure_min_pa: float | None = None
    #: Pression maximale admissible au refoulement, en Pa absolus (contrôle C-004).
    discharge_pressure_max_pa: float | None = None
    #: Coefficient de perte du collecteur d'aspiration, appliqué au calcul du NPSH disponible.
    suction_line_k: float = 0.0
    #: Coefficient de perte du chemin de bypass.
    bypass_k: float = 0.0
    #: Rendement du moteur et de la transmission, appliqué à la puissance absorbée.
    drive_efficiency: float = 1.0
    label: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.drive_efficiency <= 1.0:
            raise InvalidInputError(
                f"Station {self.name} : le rendement d'entraînement doit appartenir à ]0 ; 1].",
                drive_efficiency=self.drive_efficiency,
            )
        if (
            self.suction_pressure_min_pa is not None
            and self.discharge_pressure_max_pa is not None
            and self.discharge_pressure_max_pa <= self.suction_pressure_min_pa
        ):
            raise InvalidInputError(
                f"Station {self.name} : la pression maximale de refoulement doit être supérieure "
                f"à la pression minimale d'aspiration.",
                suction_min=self.suction_pressure_min_pa,
                discharge_max=self.discharge_pressure_max_pa,
            )
        identifiers = [p.id for group in self.groups for p in group.pumps]
        duplicates = {i for i in identifiers if identifiers.count(i) > 1}
        if duplicates:
            raise InvalidInputError(
                f"Station {self.name} : identifiants de pompe dupliqués {sorted(duplicates)}.",
                station_id=self.id,
            )

    # ------------------------------------------------------------------ inventaire

    @property
    def pumps(self) -> tuple[PumpInstance, ...]:
        return tuple(p for group in self.groups for p in group.pumps)

    @property
    def active_pumps(self) -> tuple[PumpInstance, ...]:
        if not self.is_in_service:
            return ()
        return tuple(p for group in self.groups for p in group.active_pumps)

    @property
    def active_groups(self) -> tuple[PumpGroup, ...]:
        if not self.is_in_service:
            return ()
        return tuple(g for g in self.groups if g.is_active)

    @property
    def is_in_service(self) -> bool:
        """Vrai si la station peut fournir de l'énergie au fluide."""
        return self.status is EquipmentStatus.AVAILABLE

    @property
    def is_bypassed(self) -> bool:
        return self.status is EquipmentStatus.BYPASSED

    @property
    def display_name(self) -> str:
        return self.label or self.name

    # ------------------------------------------------------------------ hydraulique

    def combined_head(self, flow_m3_s: float) -> float:
        """Hauteur fournie par la station au débit total traversant, en mètres.

        En montage **série**, tous les groupes voient le même débit et leurs hauteurs
        s'additionnent. En montage **parallèle**, la hauteur est commune à tous les groupes et
        le débit total se répartit entre eux ; le partage est résolu par dichotomie.
        """
        if not self.is_in_service or flow_m3_s < 0:
            return 0.0
        groups = self.active_groups
        if not groups:
            return 0.0
        if self.arrangement is PumpArrangement.SERIES or len(groups) == 1:
            return sum(g.head(flow_m3_s) for g in groups)
        return self._parallel_head(flow_m3_s, groups)

    def _parallel_head(self, total_flow_m3_s: float, groups: tuple[PumpGroup, ...]) -> float:
        """Résout la hauteur commune ``H`` telle que ``Σ Q_i(H) = Q_total``.

        Chaque groupe possède une caractéristique ``H_i(Q)`` strictement décroissante ; la
        somme des débits ``Σ Q_i(H)`` est donc strictement décroissante en ``H``. La
        dichotomie converge sur ``[0 ; max_i H_i(0)]``.

        Un groupe dont la hauteur à débit nul est inférieure à ``H`` ne refoule pas : sa
        contribution est nulle, ce qui traduit le fait qu'une pompe faible en parallèle avec
        une pompe forte peut être refoulée (et devrait être protégée par un clapet).
        """
        head_high = max(g.max_head() for g in groups)
        if head_high <= 0.0:
            return 0.0
        if total_flow_m3_s <= 0.0:
            return head_high

        def total_flow_at(head: float) -> float:
            return sum(self._group_flow_at_head(g, head) for g in groups)

        low, high = 0.0, head_high
        if total_flow_at(low) < total_flow_m3_s:
            # Le débit demandé dépasse la capacité de la station à hauteur nulle : la
            # caractéristique est prolongée par l'extrapolation des courbes, ce qui reste
            # signalé par l'évaluation détaillée de chaque pompe.
            return 0.0

        for _ in range(PARALLEL_SHARING_MAX_ITERATIONS):
            middle = 0.5 * (low + high)
            if total_flow_at(middle) > total_flow_m3_s:
                low = middle
            else:
                high = middle
            if high - low < 1e-9:
                break
        return 0.5 * (low + high)

    @staticmethod
    def _group_flow_at_head(group: PumpGroup, head_m: float) -> float:
        """Débit d'un groupe pour une hauteur imposée, par dichotomie sur sa caractéristique."""
        if head_m >= group.max_head():
            return 0.0
        low, high = 0.0, 1.0
        # Recherche d'une borne supérieure encadrant la solution.
        while group.head(high) > head_m and high < 1e6:
            high *= 2.0
        for _ in range(PARALLEL_SHARING_MAX_ITERATIONS):
            middle = 0.5 * (low + high)
            if group.head(middle) > head_m:
                low = middle
            else:
                high = middle
            if high - low < PARALLEL_SHARING_TOLERANCE_M3_S:
                break
        return 0.5 * (low + high)

    def flow_distribution(self, total_flow_m3_s: float) -> dict[str, float]:
        """Débit traversant chaque pompe active, en m³/s.

        En série, chaque pompe voit le débit total. En parallèle, la répartition découle de la
        hauteur commune ; à l'intérieur d'un groupe en série, toutes les pompes voient le
        débit du groupe.
        """
        groups = self.active_groups
        if not groups:
            return {}
        if self.arrangement is PumpArrangement.SERIES or len(groups) == 1:
            return {p.id: total_flow_m3_s for g in groups for p in g.active_pumps}

        head = self._parallel_head(total_flow_m3_s, groups)
        distribution: dict[str, float] = {}
        raw = {g.id: self._group_flow_at_head(g, head) for g in groups}
        total_raw = sum(raw.values())
        # Correction proportionnelle : la dichotomie converge à la tolérance près, cette
        # normalisation garantit la conservation exacte du débit total (contrôle C-001).
        scale = (total_flow_m3_s / total_raw) if total_raw > 0 else 0.0
        for group in groups:
            group_flow = raw[group.id] * scale
            for pump in group.active_pumps:
                distribution[pump.id] = group_flow
        return distribution

    def evaluate(self, flow_m3_s: float, density_kg_m3: float) -> StationEvaluation:
        """Point de fonctionnement complet : hauteur, puissances, rendement et détail par pompe."""
        if not self.is_in_service or not self.active_pumps:
            return StationEvaluation(
                head_m=0.0,
                hydraulic_power_w=0.0,
                absorbed_power_w=0.0,
                efficiency=None,
                active_pump_count=0,
                detail=("Station bypassée." if self.is_bypassed else "Aucune pompe active."),
            )

        head = self.combined_head(flow_m3_s)
        distribution = self.flow_distribution(flow_m3_s)
        evaluations: dict[str, CurveEvaluation] = {}
        absorbed_total = 0.0
        absorbed_known = True
        extrapolated = False
        details: list[str] = []

        for pump in self.active_pumps:
            pump_flow = distribution.get(pump.id, 0.0)
            evaluation = pump.evaluate(pump_flow)
            evaluations[pump.id] = evaluation
            extrapolated = extrapolated or evaluation.extrapolated
            if evaluation.detail:
                details.append(f"{pump.display_name} : {evaluation.detail}")

            if evaluation.power_w is not None:
                absorbed_total += evaluation.power_w
            elif evaluation.efficiency is not None and evaluation.efficiency > 0:
                pump_hydraulic = density_kg_m3 * G * pump_flow * evaluation.head_m
                absorbed_total += pump_hydraulic / evaluation.efficiency
            else:
                absorbed_known = False

        hydraulic = density_kg_m3 * G * flow_m3_s * head
        absorbed: float | None = None
        efficiency: float | None = None
        if absorbed_known and absorbed_total > 0:
            absorbed = absorbed_total / self.drive_efficiency
            efficiency = hydraulic / absorbed if absorbed > 0 else None
        elif not absorbed_known:
            details.append(
                "Puissance absorbée indisponible : ni courbe P(Q) ni rendement fourni pour au "
                "moins une pompe."
            )

        return StationEvaluation(
            head_m=head,
            hydraulic_power_w=hydraulic,
            absorbed_power_w=absorbed,
            efficiency=efficiency,
            active_pump_count=len(self.active_pumps),
            flow_per_pump_m3_s=distribution,
            pump_evaluations=evaluations,
            extrapolated=extrapolated,
            detail=" ".join(details) if details else None,
        )

    def npsh_available_m(
        self,
        suction_pressure_pa: float,
        vapor_pressure_pa: float,
        density_kg_m3: float,
        velocity_head_m: float = 0.0,
    ) -> float:
        """NPSH disponible à l'aspiration, en mètres de colonne de fluide.

        .. math::

            \\mathrm{NPSH}_a = \\frac{p_{asp} - p_v}{\\rho g} + \\frac{v^2}{2g}

        ``suction_pressure_pa`` est la pression **absolue** mesurée au niveau de la bride
        d'aspiration, pertes du collecteur déjà déduites. La convention retenue est celle du
        D07 § 6 ; elle est rappelée dans chaque note de calcul afin qu'aucune comparaison avec
        une donnée constructeur ne soit faite sur une base différente.
        """
        return (suction_pressure_pa - vapor_pressure_pa) / (density_kg_m3 * G) + velocity_head_m

    def with_status(self, status: EquipmentStatus) -> PumpStation:
        """Copie de la station avec un autre état."""
        return PumpStation(
            id=self.id,
            name=self.name,
            chainage_m=self.chainage_m,
            elevation_m=self.elevation_m,
            groups=self.groups,
            arrangement=self.arrangement,
            status=status,
            suction_pressure_min_pa=self.suction_pressure_min_pa,
            discharge_pressure_max_pa=self.discharge_pressure_max_pa,
            suction_line_k=self.suction_line_k,
            bypass_k=self.bypass_k,
            drive_efficiency=self.drive_efficiency,
            label=self.label,
        )

    def with_pumps(self, pumps: dict[str, PumpInstance]) -> PumpStation:
        """Copie de la station en remplaçant certaines pompes par identifiant."""
        new_groups = tuple(
            PumpGroup(
                id=group.id,
                pumps=tuple(pumps.get(p.id, p) for p in group.pumps),
                label=group.label,
            )
            for group in self.groups
        )
        return PumpStation(
            id=self.id,
            name=self.name,
            chainage_m=self.chainage_m,
            elevation_m=self.elevation_m,
            groups=new_groups,
            arrangement=self.arrangement,
            status=self.status,
            suction_pressure_min_pa=self.suction_pressure_min_pa,
            discharge_pressure_max_pa=self.discharge_pressure_max_pa,
            suction_line_k=self.suction_line_k,
            bypass_k=self.bypass_k,
            drive_efficiency=self.drive_efficiency,
            label=self.label,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "chainage_m": self.chainage_m,
            "elevation_m": self.elevation_m,
            "arrangement": self.arrangement.value,
            "status": self.status.value,
            "suction_pressure_min_pa": self.suction_pressure_min_pa,
            "discharge_pressure_max_pa": self.discharge_pressure_max_pa,
            "suction_line_k": self.suction_line_k,
            "bypass_k": self.bypass_k,
            "drive_efficiency": self.drive_efficiency,
            "groups": [g.as_dict() for g in self.groups],
        }


def build_series_station(
    id: str,
    name: str,
    chainage_m: float,
    elevation_m: float,
    pumps: tuple[PumpInstance, ...],
    **kwargs: Any,
) -> PumpStation:
    """Raccourci : station dont toutes les pompes sont montées en série sur une seule file."""
    return PumpStation(
        id=id,
        name=name,
        chainage_m=chainage_m,
        elevation_m=elevation_m,
        groups=(PumpGroup(id=f"{id}-G1", pumps=pumps),),
        arrangement=PumpArrangement.SERIES,
        **kwargs,
    )


def build_parallel_station(
    id: str,
    name: str,
    chainage_m: float,
    elevation_m: float,
    pumps: tuple[PumpInstance, ...],
    **kwargs: Any,
) -> PumpStation:
    """Raccourci : station dont chaque pompe forme une branche parallèle indépendante."""
    groups = tuple(
        PumpGroup(id=f"{id}-G{index + 1}", pumps=(pump,)) for index, pump in enumerate(pumps)
    )
    return PumpStation(
        id=id,
        name=name,
        chainage_m=chainage_m,
        elevation_m=elevation_m,
        groups=groups,
        arrangement=PumpArrangement.PARALLEL,
        **kwargs,
    )


def velocity_head_m(velocity_m_s: float) -> float:
    """Hauteur cinétique ``v²/(2g)``, en mètres."""
    return velocity_m_s * velocity_m_s / (2.0 * G)


def pressure_to_head_m(pressure_pa: float, density_kg_m3: float) -> float:
    """Convertit une pression en hauteur de colonne de fluide."""
    return pressure_pa / (density_kg_m3 * G)


def head_to_pressure_pa(head_m: float, density_kg_m3: float) -> float:
    """Convertit une hauteur de colonne de fluide en pression."""
    return head_m * density_kg_m3 * G


def is_finite_positive(value: float) -> bool:
    """Utilitaire de garde numérique employé par les validations."""
    return math.isfinite(value) and value > 0.0
