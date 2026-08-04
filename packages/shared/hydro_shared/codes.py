"""Codes stables de statut, d'erreur, de violation et d'avertissement.

Référence : *Documentation complète du MVP v2.0*, annexe D « Statuts et codes d'erreur »,
et § 5.8 « Contrôles physiques et numériques obligatoires ».

Ces codes font partie du contrat public de l'API et des rapports : ils ne doivent jamais
être renommés sans procédure de dépréciation (D13 § 13).
"""

from __future__ import annotations

from enum import StrEnum


class SimulationStatus(StrEnum):
    """Cycle de vie d'une simulation (annexe D)."""

    QUEUED = "SIM_QUEUED"
    RUNNING = "SIM_RUNNING"
    CONVERGED = "SIM_CONVERGED"
    CONVERGED_WARN = "SIM_CONVERGED_WARN"
    INVALID_INPUT = "SIM_INVALID_INPUT"
    NO_PHYSICAL_SOLUTION = "SIM_NO_PHYSICAL_SOLUTION"
    NOT_CONVERGED = "SIM_NOT_CONVERGED"
    CANCELLED = "SIM_CANCELLED"
    # Résultat déclaré convergent mais contenant une valeur non finie : ce
    # n'est ni une panne d'infrastructure (TECHNICAL_ERROR) ni une entrée
    # invalide, mais une incohérence numérique qui ne peut être approuvée.
    NUMERIC_ERROR = "SIM_NUMERIC_ERROR"
    TECHNICAL_ERROR = "SIM_TECHNICAL_ERROR"

    @property
    def is_terminal(self) -> bool:
        return self not in (SimulationStatus.QUEUED, SimulationStatus.RUNNING)

    @property
    def has_results(self) -> bool:
        """Vrai si un jeu de résultats exploitable est attaché au statut."""
        return self in (SimulationStatus.CONVERGED, SimulationStatus.CONVERGED_WARN)

    @property
    def is_approvable(self) -> bool:
        """Un résultat n'est approuvable que s'il a convergé sans violation critique.

        `CONVERGED_WARN` reste approuvable après examen humain des avertissements ;
        c'est la présence d'une violation critique qui bloque (voir `ValidationReport`).
        """
        return self.has_results


class ErrorCode(StrEnum):
    """Erreurs de données d'entrée — le calcul n'est pas lancé (D19 § 14)."""

    UNIT_UNKNOWN = "ERR_UNIT_UNKNOWN"
    UNIT_DIMENSION_MISMATCH = "ERR_UNIT_DIMENSION_MISMATCH"
    PROFILE_NOT_MONOTONIC = "ERR_PROFILE_NOT_MONOTONIC"
    PUMP_CURVE_INVALID = "ERR_PUMP_CURVE_INVALID"
    TANK_TABLE_INVALID = "ERR_TANK_TABLE_INVALID"
    GEOMETRY_INVALID = "ERR_GEOMETRY_INVALID"
    TOPOLOGY_INVALID = "ERR_TOPOLOGY_INVALID"
    BOUNDARY_CONDITIONS_INVALID = "ERR_BOUNDARY_CONDITIONS_INVALID"
    FLUID_PROPERTIES_MISSING = "ERR_FLUID_PROPERTIES_MISSING"
    SCENARIO_INVALID = "ERR_SCENARIO_INVALID"
    ENGINE_UNSUPPORTED_CASE = "ERR_ENGINE_UNSUPPORTED_CASE"


class ViolationCode(StrEnum):
    """Violations physiques ou normatives détectées sur un résultat.

    Correspondance avec les contrôles obligatoires `C-001` à `C-012` :

    ===============  ==============================================
    Contrôle         Code
    ===============  ==============================================
    C-001            ``VIOL_MASS_BALANCE``
    C-002            ``VIOL_PRESSURE_BELOW_VAPOR``
    C-003            ``VIOL_CAVITATION``
    C-004            ``VIOL_PRESSURE_HIGH``
    C-005            ``VIOL_VELOCITY_OUT_OF_RANGE``
    C-006            ``VIOL_PUMP_OFF_CURVE``
    C-007            ``VIOL_POWER``
    C-008            ``VIOL_TANK_BELOW_MIN``
    C-009            ``VIOL_TANK_ABOVE_HIGH_HIGH``
    C-010            ``SIM_NOT_CONVERGED`` (statut)
    C-011            ``WARN_EXTRAPOLATION`` (avertissement)
    C-012            ``VIOL_RESIDUAL_ABOVE_TOLERANCE``
    ===============  ==============================================
    """

    MASS_BALANCE = "VIOL_MASS_BALANCE"
    PRESSURE_HIGH = "VIOL_PRESSURE_HIGH"
    PRESSURE_LOW = "VIOL_PRESSURE_LOW"
    PRESSURE_BELOW_VAPOR = "VIOL_PRESSURE_BELOW_VAPOR"
    CAVITATION = "VIOL_CAVITATION"
    POWER = "VIOL_POWER"
    VELOCITY_OUT_OF_RANGE = "VIOL_VELOCITY_OUT_OF_RANGE"
    PUMP_OFF_CURVE = "VIOL_PUMP_OFF_CURVE"
    PUMP_BELOW_MIN_FLOW = "VIOL_PUMP_BELOW_MIN_FLOW"
    PUMP_ABOVE_MAX_FLOW = "VIOL_PUMP_ABOVE_MAX_FLOW"
    TANK_BELOW_MIN = "VIOL_TANK_BELOW_MIN"
    TANK_ABOVE_HIGH_HIGH = "VIOL_TANK_ABOVE_HIGH_HIGH"
    TANK_ABOVE_HIGH = "VIOL_TANK_ABOVE_HIGH"
    TANK_PRODUCT_INCOMPATIBLE = "VIOL_TANK_PRODUCT_INCOMPATIBLE"
    RESIDUAL_ABOVE_TOLERANCE = "VIOL_RESIDUAL_ABOVE_TOLERANCE"
    SUCTION_PRESSURE_LOW = "VIOL_SUCTION_PRESSURE_LOW"
    DISCHARGE_PRESSURE_HIGH = "VIOL_DISCHARGE_PRESSURE_HIGH"


class WarningCode(StrEnum):
    """Avertissements : le résultat est disponible mais doit être examiné (D19 § 14)."""

    EXTRAPOLATION = "WARN_EXTRAPOLATION"
    NEAR_LIMIT = "WARN_NEAR_LIMIT"
    PUMP_EXTRAPOLATION_NEAR_LIMIT = "WARN_PUMP_EXTRAPOLATION_NEAR_LIMIT"
    TRANSITION_REGIME = "WARN_TRANSITION_REGIME"
    GRAVITY_FLOW_SUSPECTED = "WARN_GRAVITY_FLOW_SUSPECTED"
    PROPERTY_DEFAULTED = "WARN_PROPERTY_DEFAULTED"
    PROPERTY_CONSTANT_ASSUMED = "WARN_PROPERTY_CONSTANT_ASSUMED"
    SOLVER_FALLBACK = "WARN_SOLVER_FALLBACK"
    LOW_VELOCITY = "WARN_LOW_VELOCITY"
    HIGH_VELOCITY = "WARN_HIGH_VELOCITY"
    PUMP_OFF_BEP = "WARN_PUMP_OFF_BEP"
    RULE_NOT_IMPLEMENTED = "WARN_RULE_NOT_IMPLEMENTED"


class DataQualityCode(StrEnum):
    """Règles de qualité des données à l'import (D09 § 13)."""

    DQ_001_UNIT_UNKNOWN = "DQ-001"
    DQ_002_NON_POSITIVE_DIMENSION = "DQ-002"
    DQ_003_PROFILE_UNORDERED = "DQ-003"
    DQ_004_STRAPPING_NOT_MONOTONIC = "DQ-004"
    DQ_005_PUMP_CURVE_DOMAIN = "DQ-005"
    DQ_006_PROPERTY_EXTRAPOLATED = "DQ-006"
    DQ_007_TIMESTAMP_INVALID = "DQ-007"
    DQ_008_SENSOR_QUALITY_BAD = "DQ-008"
    DQ_009_MASS_BALANCE_INCONSISTENT = "DQ-009"
    DQ_010_STANDARD_NOT_APPROVED = "DQ-010"


#: Contrôles physiques et numériques obligatoires (§ 5.8 de la documentation v2.0).
#: Le moteur doit produire un diagnostic pour chacun d'eux à chaque simulation.
MANDATORY_CHECKS: dict[str, str] = {
    "C-001": "Conservation de masse",
    "C-002": "Pression inférieure à la pression de vapeur",
    "C-003": "NPSH insuffisant",
    "C-004": "Pression supérieure à la limite admissible",
    "C-005": "Vitesse hors plage configurée",
    "C-006": "Pompe hors courbe",
    "C-007": "Puissance moteur dépassée",
    "C-008": "Réservoir sous niveau minimal",
    "C-009": "Réservoir au-dessus du niveau haut-haut",
    "C-010": "Non-convergence",
    "C-011": "Extrapolation de propriété",
    "C-012": "Résidu supérieur à la tolérance",
}
