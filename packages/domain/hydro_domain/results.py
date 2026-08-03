"""Structures de résultats d'une simulation stationnaire.

Un résultat est **immuable** et porte tout ce qui permet de le rejouer et de l'expliquer
(D-v2 § 4.9) : hydraulique par tronçon, point de fonctionnement par station, profil le long du
tracé, contraintes localisées, diagnostics numériques et empreinte de l'environnement.

Un résultat sans violation critique et dont le bilan de masse et la convergence sont sous
tolérance est approuvable ; sinon il reste consultable mais ne peut pas être approuvé
(NFR-SCI-005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hydro_shared.codes import SimulationStatus
from hydro_shared.diagnostics import Diagnostic, Severity, SolverDiagnostics, Violation
from hydro_shared.versioning import ENGINE_VERSION


@dataclass(frozen=True, slots=True)
class ProfilePointResult:
    """État hydraulique en un point du tracé."""

    chainage_m: float
    elevation_m: float
    pressure_pa: float
    #: Ligne piézométrique ``H = z + p/(ρg)``, en mètres.
    hydraulic_grade_m: float
    flow_m3_s: float
    velocity_m_s: float
    #: Vrai si la pression y est inférieure ou égale à la pression de vapeur du produit.
    below_vapor_pressure: bool = False
    #: Vrai si ce point appartient à une zone susceptible d'être gravitaire (PHY-GRV-01).
    gravity_zone: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "chainage_m": self.chainage_m,
            "elevation_m": self.elevation_m,
            "pressure_pa": self.pressure_pa,
            "hydraulic_grade_m": self.hydraulic_grade_m,
            "flow_m3_s": self.flow_m3_s,
            "velocity_m_s": self.velocity_m_s,
            "below_vapor_pressure": self.below_vapor_pressure,
            "gravity_zone": self.gravity_zone,
        }


@dataclass(frozen=True, slots=True)
class SegmentResult:
    """Bilan hydraulique d'un tronçon (D09 § 9, ``EdgeResult``)."""

    segment_id: str
    label: str | None
    flow_m3_s: float
    velocity_m_s: float
    reynolds: float
    friction_factor: float
    friction_model: str
    #: Perte de charge linéaire, en mètres de colonne de fluide.
    friction_head_loss_m: float
    #: Perte de charge singulière cumulée des accessoires, en mètres.
    minor_head_loss_m: float
    #: Variation d'altitude entre l'entrée et la sortie du tronçon, en mètres.
    elevation_change_m: float
    inlet_pressure_pa: float
    outlet_pressure_pa: float
    min_pressure_pa: float
    max_pressure_pa: float
    #: Marge à la pression maximale admissible, en pascals. ``None`` si non renseignée.
    maop_margin_pa: float | None = None

    @property
    def total_head_loss_m(self) -> float:
        return self.friction_head_loss_m + self.minor_head_loss_m

    @property
    def flow_regime(self) -> str:
        """Régime d'écoulement selon le nombre de Reynolds.

        Les bornes 2 000 et 4 000 sont les valeurs conventionnelles de la zone de transition ;
        elles sont explicitées ici pour que la note de calcul puisse les citer.
        """
        if self.reynolds < 2000.0:
            return "laminaire"
        if self.reynolds < 4000.0:
            return "transition"
        return "turbulent"

    def as_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "label": self.label,
            "flow_m3_s": self.flow_m3_s,
            "velocity_m_s": self.velocity_m_s,
            "reynolds": self.reynolds,
            "flow_regime": self.flow_regime,
            "friction_factor": self.friction_factor,
            "friction_model": self.friction_model,
            "friction_head_loss_m": self.friction_head_loss_m,
            "minor_head_loss_m": self.minor_head_loss_m,
            "total_head_loss_m": self.total_head_loss_m,
            "elevation_change_m": self.elevation_change_m,
            "inlet_pressure_pa": self.inlet_pressure_pa,
            "outlet_pressure_pa": self.outlet_pressure_pa,
            "min_pressure_pa": self.min_pressure_pa,
            "max_pressure_pa": self.max_pressure_pa,
            "maop_margin_pa": self.maop_margin_pa,
        }


@dataclass(frozen=True, slots=True)
class PumpResult:
    """Point de fonctionnement d'une pompe (D09 § 9, ``PumpResult``)."""

    pump_id: str
    label: str
    station_id: str
    running: bool
    flow_m3_s: float
    head_m: float
    speed_ratio: float
    efficiency: float | None = None
    hydraulic_power_w: float | None = None
    absorbed_power_w: float | None = None
    npsh_required_m: float | None = None
    npsh_available_m: float | None = None
    #: Marge NPSH = NPSHa − NPSHr − marge de projet, en mètres (contrôle C-003).
    npsh_margin_m: float | None = None
    within_curve_domain: bool = True
    off_bep_ratio: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pump_id": self.pump_id,
            "label": self.label,
            "station_id": self.station_id,
            "running": self.running,
            "flow_m3_s": self.flow_m3_s,
            "head_m": self.head_m,
            "speed_ratio": self.speed_ratio,
            "efficiency": self.efficiency,
            "hydraulic_power_w": self.hydraulic_power_w,
            "absorbed_power_w": self.absorbed_power_w,
            "npsh_required_m": self.npsh_required_m,
            "npsh_available_m": self.npsh_available_m,
            "npsh_margin_m": self.npsh_margin_m,
            "within_curve_domain": self.within_curve_domain,
            "off_bep_ratio": self.off_bep_ratio,
        }


@dataclass(frozen=True, slots=True)
class StationResult:
    """Bilan d'une station de pompage."""

    station_id: str
    name: str
    chainage_m: float
    elevation_m: float
    in_service: bool
    bypassed: bool
    flow_m3_s: float
    suction_pressure_pa: float
    discharge_pressure_pa: float
    head_m: float
    hydraulic_power_w: float
    absorbed_power_w: float | None
    efficiency: float | None
    active_pump_count: int
    pumps: tuple[PumpResult, ...] = ()

    @property
    def differential_pressure_pa(self) -> float:
        return self.discharge_pressure_pa - self.suction_pressure_pa

    def as_dict(self) -> dict[str, Any]:
        return {
            "station_id": self.station_id,
            "name": self.name,
            "chainage_m": self.chainage_m,
            "elevation_m": self.elevation_m,
            "in_service": self.in_service,
            "bypassed": self.bypassed,
            "flow_m3_s": self.flow_m3_s,
            "suction_pressure_pa": self.suction_pressure_pa,
            "discharge_pressure_pa": self.discharge_pressure_pa,
            "differential_pressure_pa": self.differential_pressure_pa,
            "head_m": self.head_m,
            "hydraulic_power_w": self.hydraulic_power_w,
            "absorbed_power_w": self.absorbed_power_w,
            "efficiency": self.efficiency,
            "active_pump_count": self.active_pump_count,
            "pumps": [p.as_dict() for p in self.pumps],
        }


@dataclass(frozen=True, slots=True)
class GravityZone:
    """Portion du tracé où la pression atteint la pression de vapeur (D07 § 8).

    Le MVP se limite à **détecter et signaler** ces zones. Une modélisation détaillée de
    l'écoulement à surface libre, de la séparation de colonne et de la reprise de pression
    doit être validée avant tout usage industriel : le champ ``fill_ratio`` n'est renseigné
    qu'à titre indicatif et n'est jamais présenté comme un résultat approuvé.
    """

    start_chainage_m: float
    end_chainage_m: float
    #: Degré de remplissage estimé, sans dimension. Indicatif uniquement.
    fill_ratio: float | None = None

    @property
    def length_m(self) -> float:
        return self.end_chainage_m - self.start_chainage_m

    def as_dict(self) -> dict[str, Any]:
        return {
            "start_chainage_m": self.start_chainage_m,
            "end_chainage_m": self.end_chainage_m,
            "length_m": self.length_m,
            "fill_ratio": self.fill_ratio,
        }


@dataclass(frozen=True, slots=True)
class EnergySummary:
    """Consommation énergétique du scénario."""

    total_hydraulic_power_w: float
    total_absorbed_power_w: float | None
    #: Énergie absorbée sur la période de référence, en joules.
    energy_j: float | None = None
    #: Durée de référence du chiffrage, en secondes.
    duration_s: float | None = None
    cost: float | None = None
    #: Énergie spécifique en J/m³ transporté : indicateur de comparaison entre scénarios.
    specific_energy_j_m3: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_hydraulic_power_w": self.total_hydraulic_power_w,
            "total_absorbed_power_w": self.total_absorbed_power_w,
            "energy_j": self.energy_j,
            "duration_s": self.duration_s,
            "cost": self.cost,
            "specific_energy_j_m3": self.specific_energy_j_m3,
        }


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Résultat complet et immuable d'une simulation stationnaire."""

    status: SimulationStatus
    scenario_id: str
    engine: str
    engine_version: str = ENGINE_VERSION
    input_hash: str | None = None

    flow_m3_s: float = 0.0
    min_pressure_pa: float | None = None
    max_pressure_pa: float | None = None
    total_head_loss_m: float = 0.0

    segments: tuple[SegmentResult, ...] = ()
    stations: tuple[StationResult, ...] = ()
    profile: tuple[ProfilePointResult, ...] = ()
    gravity_zones: tuple[GravityZone, ...] = ()
    energy: EnergySummary | None = None

    violations: tuple[Violation, ...] = ()
    warnings: tuple[Diagnostic, ...] = ()
    diagnostics: SolverDiagnostics = field(default_factory=SolverDiagnostics)

    #: Hypothèses retenues : propriétés, corrélations, conventions et sources.
    assumptions: dict[str, Any] = field(default_factory=dict)
    #: Empreinte de l'environnement de calcul (versions, dépendances, commit).
    environment: dict[str, Any] = field(default_factory=dict)
    #: Autorisation propre au moteur de présenter le résultat comme approuvable.
    #:
    #: Un moteur secondaire peut converger numériquement sans exécuter tous les contrôles
    #: scientifiques obligatoires. Ce verrou distingue cette limite de périmètre d'une
    #: violation physique du scénario.
    approval_permitted: bool = True
    #: Motif explicite du verrou d'approbation, lorsqu'il est actif.
    approval_block_reason: str | None = None

    # ------------------------------------------------------------------ synthèse

    @property
    def critical_violations(self) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.severity is Severity.CRITICAL)

    @property
    def has_critical_violation(self) -> bool:
        return bool(self.critical_violations)

    @property
    def is_feasible(self) -> bool:
        """Vrai si le scénario est réalisable : convergé et sans violation critique."""
        return self.status.has_results and not self.has_critical_violation

    @property
    def is_approvable(self) -> bool:
        """Un résultat n'est approuvable que si la physique **et** la numérique tiennent.

        Les quatre conditions sont cumulatives (NFR-SCI-005) : moteur autorisé à conclure,
        convergence atteinte, bilan de masse sous tolérance, aucune violation critique.
        """
        return (
            self.approval_permitted
            and self.status.has_results
            and self.diagnostics.converged
            and self.diagnostics.mass_balance_ok
            and not self.has_critical_violation
        )

    @property
    def severity(self) -> Severity:
        levels = [v.severity for v in self.violations] + [w.severity for w in self.warnings]
        return max(levels) if levels else Severity.INFO

    def station(self, station_id: str) -> StationResult | None:
        for station in self.stations:
            if station.station_id == station_id:
                return station
        return None

    def summary(self) -> dict[str, Any]:
        """Synthèse compacte, exposée par ``GET /calculations/{id}/summary``."""
        return {
            "status": self.status.value,
            "scenario_id": self.scenario_id,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "input_hash": self.input_hash,
            "flow_m3_s": self.flow_m3_s,
            "min_pressure_pa": self.min_pressure_pa,
            "max_pressure_pa": self.max_pressure_pa,
            "total_head_loss_m": self.total_head_loss_m,
            "total_power_w": self.energy.total_absorbed_power_w if self.energy else None,
            "station_count": len(self.stations),
            "segment_count": len(self.segments),
            "violations": [v.as_dict() for v in self.violations],
            "warnings": [w.as_dict() for w in self.warnings],
            "gravity_zone_count": len(self.gravity_zones),
            "feasible": self.is_feasible,
            "approvable": self.is_approvable,
            "approval_permitted": self.approval_permitted,
            "approval_block_reason": self.approval_block_reason,
            "iterations": self.diagnostics.iterations,
            "residual": self.diagnostics.residual,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "segments": [s.as_dict() for s in self.segments],
            "stations": [s.as_dict() for s in self.stations],
            "profile": [p.as_dict() for p in self.profile],
            "gravity_zones": [g.as_dict() for g in self.gravity_zones],
            "energy": self.energy.as_dict() if self.energy else None,
            "diagnostics": self.diagnostics.as_dict(),
            "assumptions": self.assumptions,
            "environment": self.environment,
        }
