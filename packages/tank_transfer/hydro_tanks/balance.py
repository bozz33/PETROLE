"""Bilan matière d'un transfert et propagation des incertitudes.

Les incertitudes fournies sont des incertitudes-types. Leur combinaison suppose des
mesures indépendantes ; l'incertitude élargie vaut k multiplié par l'incertitude combinée.
Ce calcul numérique ne remplace pas l'analyse métrologique des compteurs et du jaugeage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_shared.errors import InvalidInputError


@dataclass(frozen=True, slots=True)
class VolumeMeasurement:
    """Mesure volumique en m³, accompagnée de son incertitude-type."""

    value_m3: float
    standard_uncertainty_m3: float = 0.0
    label: str | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.value_m3):
            raise InvalidInputError(
                "Une mesure volumique doit être finie.",
                label=self.label,
                value_m3=self.value_m3,
            )
        if not math.isfinite(self.standard_uncertainty_m3) or self.standard_uncertainty_m3 < 0:
            raise InvalidInputError(
                "L'incertitude-type doit être positive ou nulle.",
                label=self.label,
                standard_uncertainty_m3=self.standard_uncertainty_m3,
            )


@dataclass(frozen=True, slots=True)
class TransferBalanceInput:
    """Mesures compteur et jaugeage encadrant un transfert."""

    source_opening: VolumeMeasurement
    source_closing: VolumeMeasurement
    destination_opening: VolumeMeasurement
    destination_closing: VolumeMeasurement
    metered_volume: VolumeMeasurement
    accounted_losses: VolumeMeasurement = VolumeMeasurement(0.0, 0.0, "Pertes comptabilisées")
    coverage_factor: float = 2.0
    absolute_tolerance_m3: float = 0.0
    relative_tolerance: float = 0.001

    def __post_init__(self) -> None:
        if not math.isfinite(self.coverage_factor) or self.coverage_factor <= 0:
            raise InvalidInputError(
                "Le facteur d'élargissement doit être strictement positif.",
                coverage_factor=self.coverage_factor,
            )
        if not math.isfinite(self.absolute_tolerance_m3) or self.absolute_tolerance_m3 < 0:
            raise InvalidInputError(
                "La tolérance absolue doit être positive ou nulle.",
                absolute_tolerance_m3=self.absolute_tolerance_m3,
            )
        if not math.isfinite(self.relative_tolerance) or self.relative_tolerance < 0:
            raise InvalidInputError(
                "La tolérance relative doit être positive ou nulle.",
                relative_tolerance=self.relative_tolerance,
            )


@dataclass(frozen=True, slots=True)
class TransferBalanceResult:
    """Écarts de bilan, incertitude combinée et décision de conformité."""

    source_withdrawal_m3: float
    destination_receipt_m3: float
    metered_volume_m3: float
    system_imbalance_m3: float
    meter_source_difference_m3: float
    meter_destination_difference_m3: float
    combined_standard_uncertainty_m3: float
    expanded_uncertainty_m3: float
    acceptance_limit_m3: float
    relative_imbalance: float | None
    within_tolerance: bool

    def as_dict(self) -> dict[str, float | bool | None]:
        return {
            "source_withdrawal_m3": self.source_withdrawal_m3,
            "destination_receipt_m3": self.destination_receipt_m3,
            "metered_volume_m3": self.metered_volume_m3,
            "system_imbalance_m3": self.system_imbalance_m3,
            "meter_source_difference_m3": self.meter_source_difference_m3,
            "meter_destination_difference_m3": self.meter_destination_difference_m3,
            "combined_standard_uncertainty_m3": self.combined_standard_uncertainty_m3,
            "expanded_uncertainty_m3": self.expanded_uncertainty_m3,
            "acceptance_limit_m3": self.acceptance_limit_m3,
            "relative_imbalance": self.relative_imbalance,
            "within_tolerance": self.within_tolerance,
        }


def compute_transfer_balance(data: TransferBalanceInput) -> TransferBalanceResult:
    """Calcule le bilan source-destination et les écarts au compteur.

    Convention : écart système = soutirage source - réception destination - pertes.
    Une valeur positive représente un volume non expliqué.
    """

    source_withdrawal = data.source_opening.value_m3 - data.source_closing.value_m3
    destination_receipt = data.destination_closing.value_m3 - data.destination_opening.value_m3
    system_imbalance = source_withdrawal - destination_receipt - data.accounted_losses.value_m3
    meter_source_difference = data.metered_volume.value_m3 - source_withdrawal
    meter_destination_difference = data.metered_volume.value_m3 - destination_receipt

    inventory_uncertainties = (
        data.source_opening.standard_uncertainty_m3,
        data.source_closing.standard_uncertainty_m3,
        data.destination_opening.standard_uncertainty_m3,
        data.destination_closing.standard_uncertainty_m3,
        data.accounted_losses.standard_uncertainty_m3,
    )
    combined_uncertainty = math.sqrt(sum(uncertainty**2 for uncertainty in inventory_uncertainties))
    expanded_uncertainty = data.coverage_factor * combined_uncertainty
    reference_volume = max(
        abs(source_withdrawal),
        abs(destination_receipt),
        abs(data.metered_volume.value_m3),
    )
    relative_imbalance = system_imbalance / reference_volume if reference_volume > 0 else None
    acceptance_limit = max(
        data.absolute_tolerance_m3,
        data.relative_tolerance * reference_volume,
        expanded_uncertainty,
    )
    return TransferBalanceResult(
        source_withdrawal_m3=source_withdrawal,
        destination_receipt_m3=destination_receipt,
        metered_volume_m3=data.metered_volume.value_m3,
        system_imbalance_m3=system_imbalance,
        meter_source_difference_m3=meter_source_difference,
        meter_destination_difference_m3=meter_destination_difference,
        combined_standard_uncertainty_m3=combined_uncertainty,
        expanded_uncertainty_m3=expanded_uncertainty,
        acceptance_limit_m3=acceptance_limit,
        relative_imbalance=relative_imbalance,
        within_tolerance=abs(system_imbalance) <= acceptance_limit,
    )
