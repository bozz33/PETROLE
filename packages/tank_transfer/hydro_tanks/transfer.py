"""Simulation dynamique des transferts bac-à-bac.

Le moteur applique le bilan volumique discret :

V_source(t + dt) = V_source(t) - Q dt
V_destination(t + dt) = V_destination(t) + Q (1 - f_pertes) dt

Les événements de fin sont ramenés à leur instant exact dans le dernier pas. Cette
interpolation évite de dépasser un niveau de sécurité à cause du pas de calcul
(VAL-TNK-006). Les volumes proviennent exclusivement des tables de barémage des bacs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

from hydro_domain.enums import TransferStopReason
from hydro_domain.tanks import Tank
from hydro_shared.codes import ViolationCode, WarningCode
from hydro_shared.errors import InvalidInputError

_VOLUME_EPSILON_M3 = 1e-9
_TIME_EPSILON_S = 1e-9


@dataclass(frozen=True, slots=True)
class TransferState:
    """État transmis au calcul hydraulique à chaque pas."""

    time_s: float
    source_level_m: float
    source_volume_m3: float
    destination_level_m: float
    destination_volume_m3: float
    cumulative_withdrawn_m3: float
    cumulative_received_m3: float


@dataclass(frozen=True, slots=True)
class TransferOperatingPoint:
    """Point de fonctionnement instantané du chemin de transfert."""

    flow_m3_s: float
    discharge_pressure_pa: float | None = None
    absorbed_power_w: float | None = None
    feasible: bool = True
    detail: str | None = None

    def __post_init__(self) -> None:
        values = (self.flow_m3_s, self.discharge_pressure_pa, self.absorbed_power_w)
        if any(value is not None and not math.isfinite(value) for value in values):
            raise InvalidInputError(
                "Le point de fonctionnement contient une valeur non finie.",
                operating_point=values,
            )
        if self.discharge_pressure_pa is not None and self.discharge_pressure_pa < 0:
            raise InvalidInputError(
                "La pression de refoulement doit être absolue et positive.",
                discharge_pressure_pa=self.discharge_pressure_pa,
            )
        if self.absorbed_power_w is not None and self.absorbed_power_w < 0:
            raise InvalidInputError(
                "La puissance absorbée ne peut pas être négative.",
                absorbed_power_w=self.absorbed_power_w,
            )


class OperatingPointResolver(Protocol):
    """Interface du calcul hydraulique utilisé pendant un transfert."""

    def __call__(self, state: TransferState, /) -> TransferOperatingPoint:
        """Retourne le débit, la pression et la puissance à l'état courant."""


@dataclass(frozen=True, slots=True)
class TransferRequest:
    """Demande de transfert et limites d'exploitation.

    Un seul objectif de fin doit être fourni : volume brut soutiré, niveau de destination
    ou durée. Le débit demandé est le débit brut à la sortie du bac source.
    """

    source: Tank
    destination: Tank
    fluid_id: str
    requested_flow_m3_s: float
    target_volume_m3: float | None = None
    target_destination_level_m: float | None = None
    target_duration_s: float | None = None
    time_step_s: float = 60.0
    maximum_duration_s: float = 31_536_000.0
    maximum_flow_m3_s: float | None = None
    loss_fraction: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source.id == self.destination.id:
            raise InvalidInputError(
                "Les bacs source et destination doivent être distincts.",
                tank_id=self.source.id,
            )
        if not self.fluid_id.strip():
            raise InvalidInputError("L'identifiant du produit est obligatoire.")
        if not math.isfinite(self.requested_flow_m3_s) or self.requested_flow_m3_s <= 0:
            raise InvalidInputError(
                "Le débit de transfert doit être strictement positif.",
                requested_flow_m3_s=self.requested_flow_m3_s,
            )
        objectives = (
            self.target_volume_m3,
            self.target_destination_level_m,
            self.target_duration_s,
        )
        if sum(value is not None for value in objectives) != 1:
            raise InvalidInputError(
                "Un seul objectif est requis : volume, niveau de destination ou durée."
            )
        for name, value in (
            ("target_volume_m3", self.target_volume_m3),
            ("target_destination_level_m", self.target_destination_level_m),
            ("target_duration_s", self.target_duration_s),
            ("time_step_s", self.time_step_s),
            ("maximum_duration_s", self.maximum_duration_s),
            ("maximum_flow_m3_s", self.maximum_flow_m3_s),
        ):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise InvalidInputError(
                    f"La valeur {name} doit être strictement positive et finie.",
                    field=name,
                    value=value,
                )
        if not 0.0 <= self.loss_fraction < 1.0:
            raise InvalidInputError(
                "La fraction de pertes doit appartenir à l'intervalle [0 ; 1[.",
                loss_fraction=self.loss_fraction,
            )
        if self.target_duration_s is not None and self.target_duration_s > self.maximum_duration_s:
            raise InvalidInputError(
                "La durée cible dépasse la durée maximale autorisée.",
                target_duration_s=self.target_duration_s,
                maximum_duration_s=self.maximum_duration_s,
            )


@dataclass(frozen=True, slots=True)
class TransferSample:
    """Valeurs calculées à un instant de la simulation."""

    time_s: float
    source_level_m: float
    source_volume_m3: float
    destination_level_m: float
    destination_volume_m3: float
    flow_m3_s: float
    discharge_pressure_pa: float | None
    absorbed_power_w: float | None
    cumulative_withdrawn_m3: float
    cumulative_received_m3: float
    cumulative_losses_m3: float


@dataclass(frozen=True, slots=True)
class TransferResult:
    """Résultat complet, y compris l'événement d'arrêt et le bilan volumique."""

    stop_reason: TransferStopReason
    samples: tuple[TransferSample, ...]
    source_final: Tank
    destination_final: Tank
    preflight_feasible: bool
    messages: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()
    violation_codes: tuple[str, ...] = ()
    energy_j: float | None = None

    @property
    def duration_s(self) -> float:
        return self.samples[-1].time_s

    @property
    def withdrawn_volume_m3(self) -> float:
        return self.samples[-1].cumulative_withdrawn_m3

    @property
    def received_volume_m3(self) -> float:
        return self.samples[-1].cumulative_received_m3

    @property
    def losses_m3(self) -> float:
        return self.samples[-1].cumulative_losses_m3

    @property
    def balance_residual_m3(self) -> float:
        """Résidu du système fermé : stock initial - stock final - pertes."""

        first = self.samples[0]
        last = self.samples[-1]
        initial_stock = first.source_volume_m3 + first.destination_volume_m3
        final_stock = last.source_volume_m3 + last.destination_volume_m3
        return initial_stock - final_stock - last.cumulative_losses_m3

    @property
    def target_reached(self) -> bool:
        return self.stop_reason in {
            TransferStopReason.TARGET_VOLUME_REACHED,
            TransferStopReason.TARGET_LEVEL_REACHED,
            TransferStopReason.DURATION_REACHED,
        }


def constant_operating_point(
    flow_m3_s: float,
    *,
    discharge_pressure_pa: float | None = None,
    absorbed_power_w: float | None = None,
) -> OperatingPointResolver:
    """Construit un résolveur constant, utile pour un débit imposé."""

    point = TransferOperatingPoint(
        flow_m3_s=flow_m3_s,
        discharge_pressure_pa=discharge_pressure_pa,
        absorbed_power_w=absorbed_power_w,
    )

    def resolve(_: TransferState) -> TransferOperatingPoint:
        return point

    return resolve


class TankTransferEngine:
    """Moteur temporel du Tank & Transfer Core."""

    def assess_feasibility(self, request: TransferRequest) -> tuple[str, ...]:
        """Vérifie les contraintes connues avant tout calcul (VAL-TNK-007)."""

        problems: list[str] = []
        if not request.source.is_available:
            problems.append(f"Le bac source {request.source.display_name} est indisponible.")
        if not request.destination.is_available:
            problems.append(
                f"Le bac destination {request.destination.display_name} est indisponible."
            )
        if request.source.fluid_id is not None and request.source.fluid_id != request.fluid_id:
            problems.append(
                f"Le bac source contient {request.source.fluid_id}, pas {request.fluid_id}."
            )
        if not request.destination.accepts_fluid(request.fluid_id):
            problems.append(
                f"Le bac destination {request.destination.display_name} est incompatible "
                f"avec le produit {request.fluid_id}."
            )
        if (
            request.maximum_flow_m3_s is not None
            and request.requested_flow_m3_s > request.maximum_flow_m3_s + _VOLUME_EPSILON_M3
        ):
            problems.append(
                f"Le débit demandé ({request.requested_flow_m3_s:.6g} m³/s) dépasse "
                f"le débit maximal ({request.maximum_flow_m3_s:.6g} m³/s)."
            )

        required_withdrawal = self._planned_withdrawal(request)
        if required_withdrawal is not None:
            required_receipt = required_withdrawal * (1.0 - request.loss_fraction)
            if required_withdrawal > request.source.pumpable_volume_m3 + _VOLUME_EPSILON_M3:
                problems.append(
                    f"Le volume soutirable du bac source ({request.source.pumpable_volume_m3:.6g} "
                    f"m³) est inférieur au besoin ({required_withdrawal:.6g} m³)."
                )
            if required_receipt > request.destination.available_capacity_m3 + _VOLUME_EPSILON_M3:
                problems.append(
                    f"La capacité disponible du bac destination "
                    f"({request.destination.available_capacity_m3:.6g} m³) est inférieure "
                    f"au besoin ({required_receipt:.6g} m³)."
                )

        target_level = request.target_destination_level_m
        if target_level is not None:
            low, high = request.destination.strapping.height_range_m
            if not low <= target_level <= high:
                problems.append(
                    f"Le niveau cible ({target_level:.6g} m) sort du barémage "
                    f"[{low:.6g} ; {high:.6g}] m."
                )
            elif target_level <= request.destination.current_level_m:
                problems.append("Le niveau cible doit dépasser le niveau initial de destination.")
            elif target_level > request.destination.levels.high_high_m:
                problems.append(
                    f"Le niveau cible ({target_level:.6g} m) dépasse le seuil très haut "
                    f"({request.destination.levels.high_high_m:.6g} m)."
                )
        return tuple(problems)

    def simulate(
        self,
        request: TransferRequest,
        resolver: OperatingPointResolver | None = None,
    ) -> TransferResult:
        """Simule le transfert jusqu'au premier objectif ou seuil de sécurité."""

        problems = self.assess_feasibility(request)
        initial = self._initial_sample(request)
        if problems:
            violations = (
                (ViolationCode.TANK_PRODUCT_INCOMPATIBLE.value,)
                if any("incompatible" in problem for problem in problems)
                else ()
            )
            return TransferResult(
                stop_reason=TransferStopReason.NOT_FEASIBLE,
                samples=(initial,),
                source_final=request.source,
                destination_final=request.destination,
                preflight_feasible=False,
                messages=problems,
                violation_codes=violations,
            )

        operating_point = resolver or constant_operating_point(request.requested_flow_m3_s)
        samples = [initial]
        source_volume = request.source.current_volume_m3
        destination_volume = request.destination.current_volume_m3
        cumulative_withdrawn = 0.0
        cumulative_received = 0.0
        cumulative_losses = 0.0
        time_s = 0.0
        energy_j = 0.0
        energy_known = True
        messages: list[str] = []
        warning_codes: list[str] = []
        violation_codes: list[str] = []
        stop_reason: TransferStopReason | None = None

        while time_s < request.maximum_duration_s - _TIME_EPSILON_S:
            state = TransferState(
                time_s=time_s,
                source_level_m=request.source.strapping.height_at(source_volume),
                source_volume_m3=source_volume,
                destination_level_m=request.destination.strapping.height_at(destination_volume),
                destination_volume_m3=destination_volume,
                cumulative_withdrawn_m3=cumulative_withdrawn,
                cumulative_received_m3=cumulative_received,
            )
            point = operating_point(state)
            if not point.feasible or point.flow_m3_s <= 0:
                stop_reason = TransferStopReason.HYDRAULIC_CONSTRAINT
                messages.append(
                    point.detail or "Le chemin hydraulique ne fournit plus de débit positif."
                )
                break
            if (
                request.maximum_flow_m3_s is not None
                and point.flow_m3_s > request.maximum_flow_m3_s + _VOLUME_EPSILON_M3
            ):
                stop_reason = TransferStopReason.HYDRAULIC_CONSTRAINT
                messages.append(
                    f"Le débit calculé ({point.flow_m3_s:.6g} m³/s) dépasse le débit maximal "
                    f"({request.maximum_flow_m3_s:.6g} m³/s)."
                )
                break

            dt = min(request.time_step_s, request.maximum_duration_s - time_s)
            duration_reached = False
            if request.target_duration_s is not None:
                remaining_duration = request.target_duration_s - time_s
                dt = min(dt, max(remaining_duration, 0.0))
                duration_reached = remaining_duration <= dt + _TIME_EPSILON_S

            candidates: list[tuple[float, TransferStopReason]] = []
            if request.target_volume_m3 is not None:
                candidates.append(
                    (
                        max(request.target_volume_m3 - cumulative_withdrawn, 0.0),
                        TransferStopReason.TARGET_VOLUME_REACHED,
                    )
                )
            if request.target_destination_level_m is not None:
                target_volume = request.destination.strapping.volume_at(
                    request.target_destination_level_m
                )
                candidates.append(
                    (
                        max(target_volume - destination_volume, 0.0)
                        / (1.0 - request.loss_fraction),
                        TransferStopReason.TARGET_LEVEL_REACHED,
                    )
                )

            source_limit = request.source.minimum_volume_m3 + request.source.dead_volume_m3
            candidates.append(
                (
                    max(source_volume - source_limit, 0.0),
                    TransferStopReason.SOURCE_LOW_LEVEL,
                )
            )
            candidates.append(
                (
                    max(request.destination.high_high_volume_m3 - destination_volume, 0.0)
                    / (1.0 - request.loss_fraction),
                    TransferStopReason.DESTINATION_HIGH_LEVEL,
                )
            )

            planned_withdrawal = point.flow_m3_s * dt
            limiting_volume, limiting_reason = min(candidates, key=lambda item: item[0])
            actual_withdrawal = min(planned_withdrawal, limiting_volume)
            actual_dt = actual_withdrawal / point.flow_m3_s
            received = actual_withdrawal * (1.0 - request.loss_fraction)
            losses = actual_withdrawal - received

            source_volume -= actual_withdrawal
            destination_volume += received
            cumulative_withdrawn += actual_withdrawal
            cumulative_received += received
            cumulative_losses += losses
            time_s += actual_dt

            if point.absorbed_power_w is None:
                energy_known = False
            else:
                energy_j += point.absorbed_power_w * actual_dt

            source_level = request.source.strapping.height_at(source_volume)
            destination_level = request.destination.strapping.height_at(destination_volume)
            samples.append(
                TransferSample(
                    time_s=time_s,
                    source_level_m=source_level,
                    source_volume_m3=source_volume,
                    destination_level_m=destination_level,
                    destination_volume_m3=destination_volume,
                    flow_m3_s=point.flow_m3_s,
                    discharge_pressure_pa=point.discharge_pressure_pa,
                    absorbed_power_w=point.absorbed_power_w,
                    cumulative_withdrawn_m3=cumulative_withdrawn,
                    cumulative_received_m3=cumulative_received,
                    cumulative_losses_m3=cumulative_losses,
                )
            )

            if (
                request.destination.levels.high_m is not None
                and destination_level >= request.destination.levels.high_m
                and WarningCode.NEAR_LIMIT.value not in warning_codes
            ):
                warning_codes.append(WarningCode.NEAR_LIMIT.value)
                messages.append(
                    f"Le bac destination a atteint son niveau haut "
                    f"({request.destination.levels.high_m:.6g} m)."
                )

            if limiting_volume <= planned_withdrawal + _VOLUME_EPSILON_M3:
                stop_reason = limiting_reason
                break
            if duration_reached and dt <= actual_dt + _TIME_EPSILON_S:
                stop_reason = TransferStopReason.DURATION_REACHED
                break
            if actual_dt <= _TIME_EPSILON_S:
                stop_reason = TransferStopReason.HYDRAULIC_CONSTRAINT
                messages.append("Le pas de transfert est nul ; la simulation est arrêtée.")
                break

        if stop_reason is None:
            stop_reason = TransferStopReason.HYDRAULIC_CONSTRAINT
            messages.append(
                f"La durée maximale de calcul ({request.maximum_duration_s:.6g} s) est atteinte."
            )
        if stop_reason is TransferStopReason.DESTINATION_HIGH_LEVEL:
            messages.append("Arrêt au niveau très haut du bac destination.")
        if stop_reason is TransferStopReason.SOURCE_LOW_LEVEL:
            messages.append("Arrêt au niveau minimal soutirable du bac source.")

        source_final = request.source.with_volume(source_volume)
        destination_final = request.destination.with_volume(destination_volume)
        result = TransferResult(
            stop_reason=stop_reason,
            samples=tuple(samples),
            source_final=source_final,
            destination_final=destination_final,
            preflight_feasible=True,
            messages=tuple(messages),
            warning_codes=tuple(warning_codes),
            violation_codes=tuple(violation_codes),
            energy_j=energy_j if energy_known else None,
        )
        if abs(result.balance_residual_m3) > 1e-8:
            violation_codes.append(ViolationCode.MASS_BALANCE.value)
            result = TransferResult(
                stop_reason=result.stop_reason,
                samples=result.samples,
                source_final=result.source_final,
                destination_final=result.destination_final,
                preflight_feasible=result.preflight_feasible,
                messages=(*result.messages, "Le résidu du bilan volumique dépasse 1e-8 m³."),
                warning_codes=result.warning_codes,
                violation_codes=tuple(violation_codes),
                energy_j=result.energy_j,
            )
        return result

    @staticmethod
    def _initial_sample(request: TransferRequest) -> TransferSample:
        return TransferSample(
            time_s=0.0,
            source_level_m=request.source.current_level_m,
            source_volume_m3=request.source.current_volume_m3,
            destination_level_m=request.destination.current_level_m,
            destination_volume_m3=request.destination.current_volume_m3,
            flow_m3_s=0.0,
            discharge_pressure_pa=None,
            absorbed_power_w=None,
            cumulative_withdrawn_m3=0.0,
            cumulative_received_m3=0.0,
            cumulative_losses_m3=0.0,
        )

    @staticmethod
    def _planned_withdrawal(request: TransferRequest) -> float | None:
        if request.target_volume_m3 is not None:
            return request.target_volume_m3
        if request.target_destination_level_m is not None:
            low, high = request.destination.strapping.height_range_m
            if not low <= request.target_destination_level_m <= high:
                return None
            destination_gain = (
                request.destination.strapping.volume_at(request.target_destination_level_m)
                - request.destination.current_volume_m3
            )
            return max(destination_gain, 0.0) / (1.0 - request.loss_fraction)
        if request.target_duration_s is not None:
            return request.requested_flow_m3_s * request.target_duration_s
        return None
