"""Reconstruction transitoire P(x,t) à partir des snapshots MOC et de D07.

La densité est fournie pour chaque nœud et chaque pas afin de ne pas supposer
un produit constant pendant un scénario multiproduit. Élévation, diamètre et
coefficient cinétique sont également explicites. Aucun modèle de cavitation ou
de séparation de colonne n'est substitué lorsque la pression devient négative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_transients.moc import MocStateSnapshot
from hydro_transients.pressure import mean_velocity_full_pipe, pressure_from_total_head


@dataclass(frozen=True, slots=True)
class TransientNodePressureInput:
    """Propriétés nécessaires à l'inversion de la charge totale D07."""

    elevation_m: float
    diameter_m: float
    density_kg_m3: float
    kinetic_correction_alpha: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.elevation_m):
            raise ValueError("L'élévation du nœud doit être finie.")
        positive = (
            self.diameter_m,
            self.density_kg_m3,
            self.kinetic_correction_alpha,
        )
        if any(not math.isfinite(value) or value <= 0 for value in positive):
            raise ValueError("D, rho et alpha doivent être finis et strictement positifs.")


@dataclass(frozen=True, slots=True)
class TransientPressureSnapshot:
    """Pressions reconstruites sur tous les nœuds à un instant MOC."""

    time_s: float
    pressures_pa: tuple[float, ...]
    negative_absolute_flags: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class NodePressureEnvelope:
    node_index: int
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    minimum_pressure_time_s: float
    maximum_pressure_time_s: float
    negative_absolute_count: int


@dataclass(frozen=True, slots=True)
class TransientPressureEnvelopeSet:
    node_count: int
    start_time_s: float
    end_time_s: float
    envelopes: tuple[NodePressureEnvelope, ...]


def build_transient_pressure_snapshots(
    snapshots: tuple[MocStateSnapshot, ...],
    pressure_inputs: tuple[tuple[TransientNodePressureInput, ...], ...],
) -> tuple[TransientPressureSnapshot, ...]:
    """Reconstruit P(x,t) sans supposer une densité constante dans le temps."""

    if not snapshots:
        raise ValueError("Au moins un snapshot MOC est requis pour reconstruire P(x,t).")
    if len(snapshots) != len(pressure_inputs):
        raise ValueError("Un jeu de propriétés pression est requis pour chaque snapshot MOC.")

    node_count = len(snapshots[0].heads_m)
    if node_count == 0 or len(snapshots[0].flows_m3_s) != node_count:
        raise ValueError("Le premier snapshot MOC est incohérent.")

    pressure_snapshots: list[TransientPressureSnapshot] = []
    previous_time: float | None = None
    for snapshot, properties in zip(snapshots, pressure_inputs, strict=True):
        if not math.isfinite(snapshot.time_s) or snapshot.time_s < 0:
            raise ValueError("Le temps MOC doit être fini et positif ou nul.")
        if previous_time is not None and snapshot.time_s <= previous_time:
            raise ValueError("Les snapshots MOC doivent être strictement ordonnés.")
        if len(snapshot.heads_m) != node_count or len(snapshot.flows_m3_s) != node_count:
            raise ValueError("Tous les snapshots MOC doivent conserver le même nombre de nœuds.")
        if len(properties) != node_count:
            raise ValueError("Les propriétés pression doivent couvrir exactement tous les nœuds.")

        pressures: list[float] = []
        negative_flags: list[bool] = []
        for head_m, flow_m3_s, node_input in zip(
            snapshot.heads_m,
            snapshot.flows_m3_s,
            properties,
            strict=True,
        ):
            velocity = mean_velocity_full_pipe(
                flow_m3_s=flow_m3_s,
                diameter_m=node_input.diameter_m,
            )
            result = pressure_from_total_head(
                total_head_m=head_m,
                elevation_m=node_input.elevation_m,
                density_kg_m3=node_input.density_kg_m3,
                velocity_m_s=velocity,
                kinetic_correction_alpha=node_input.kinetic_correction_alpha,
            )
            pressures.append(result.pressure_pa)
            negative_flags.append(result.nonphysical_negative_absolute)

        pressure_snapshots.append(
            TransientPressureSnapshot(
                time_s=snapshot.time_s,
                pressures_pa=tuple(pressures),
                negative_absolute_flags=tuple(negative_flags),
            )
        )
        previous_time = snapshot.time_s

    return tuple(pressure_snapshots)


def build_transient_pressure_envelopes(
    snapshots: tuple[TransientPressureSnapshot, ...],
) -> TransientPressureEnvelopeSet:
    """Calcule les extrêmes P et leurs temps, sans interpolation ni clipping."""

    if not snapshots:
        raise ValueError("Au moins un snapshot de pression est requis.")
    node_count = len(snapshots[0].pressures_pa)
    if node_count == 0 or len(snapshots[0].negative_absolute_flags) != node_count:
        raise ValueError("Le premier snapshot de pression est incohérent.")

    previous_time: float | None = None
    for snapshot in snapshots:
        if not math.isfinite(snapshot.time_s) or snapshot.time_s < 0:
            raise ValueError("Le temps de pression doit être fini et positif ou nul.")
        if previous_time is not None and snapshot.time_s <= previous_time:
            raise ValueError("Les snapshots de pression doivent être strictement ordonnés.")
        if (
            len(snapshot.pressures_pa) != node_count
            or len(snapshot.negative_absolute_flags) != node_count
        ):
            raise ValueError("Tous les snapshots de pression doivent conserver les mêmes nœuds.")
        if any(not math.isfinite(value) for value in snapshot.pressures_pa):
            raise ValueError("Les pressions transitoires doivent rester finies.")
        previous_time = snapshot.time_s

    envelopes: list[NodePressureEnvelope] = []
    for node_index in range(node_count):
        minimum = min(snapshots, key=lambda item: item.pressures_pa[node_index])
        maximum = max(snapshots, key=lambda item: item.pressures_pa[node_index])
        negative_count = sum(snapshot.negative_absolute_flags[node_index] for snapshot in snapshots)
        envelopes.append(
            NodePressureEnvelope(
                node_index=node_index,
                minimum_pressure_pa=minimum.pressures_pa[node_index],
                maximum_pressure_pa=maximum.pressures_pa[node_index],
                minimum_pressure_time_s=minimum.time_s,
                maximum_pressure_time_s=maximum.time_s,
                negative_absolute_count=negative_count,
            )
        )

    return TransientPressureEnvelopeSet(
        node_count=node_count,
        start_time_s=snapshots[0].time_s,
        end_time_s=snapshots[-1].time_s,
        envelopes=tuple(envelopes),
    )


__all__ = [
    "NodePressureEnvelope",
    "TransientNodePressureInput",
    "TransientPressureEnvelopeSet",
    "TransientPressureSnapshot",
    "build_transient_pressure_envelopes",
    "build_transient_pressure_snapshots",
]
