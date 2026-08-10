"""Post-traitement déterministe des résultats transitoires MOC.

Le module calcule uniquement des enveloppes de charge H et de débit Q à partir
de snapshots déjà produits par le solveur. Il ne reconstruit pas une pression
sans altitude, densité et vitesse locales explicitement disponibles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_transients.moc import MocStateSnapshot


@dataclass(frozen=True, slots=True)
class NodeTransientEnvelope:
    """Extrêmes observés d'un nœud sur une campagne transitoire."""

    node_index: int
    minimum_head_m: float
    maximum_head_m: float
    minimum_flow_m3_s: float
    maximum_flow_m3_s: float
    minimum_head_time_s: float
    maximum_head_time_s: float
    minimum_flow_time_s: float
    maximum_flow_time_s: float


@dataclass(frozen=True, slots=True)
class TransientEnvelopeSet:
    """Enveloppes H/Q d'une série cohérente de snapshots."""

    node_count: int
    start_time_s: float
    end_time_s: float
    envelopes: tuple[NodeTransientEnvelope, ...]


def _validate_snapshots(snapshots: tuple[MocStateSnapshot, ...]) -> int:
    if not snapshots:
        raise ValueError("Au moins un snapshot transitoire est requis.")
    node_count = len(snapshots[0].heads_m)
    if node_count == 0 or len(snapshots[0].flows_m3_s) != node_count:
        raise ValueError("Le premier snapshot transitoire est incohérent.")
    previous_time: float | None = None
    for snapshot in snapshots:
        if not math.isfinite(snapshot.time_s) or snapshot.time_s < 0:
            raise ValueError("Les temps transitoires doivent être finis et positifs ou nuls.")
        if previous_time is not None and snapshot.time_s <= previous_time:
            raise ValueError("Les snapshots transitoires doivent être strictement ordonnés dans le temps.")
        if len(snapshot.heads_m) != node_count or len(snapshot.flows_m3_s) != node_count:
            raise ValueError("Tous les snapshots doivent conserver le même nombre de nœuds.")
        if any(not math.isfinite(value) for value in (*snapshot.heads_m, *snapshot.flows_m3_s)):
            raise ValueError("Les charges et débits transitoires doivent rester finis.")
        previous_time = snapshot.time_s
    return node_count


def build_transient_envelopes(
    snapshots: tuple[MocStateSnapshot, ...],
) -> TransientEnvelopeSet:
    """Calcule les min/max et leurs temps pour chaque nœud, sans interpolation."""

    node_count = _validate_snapshots(snapshots)
    envelopes: list[NodeTransientEnvelope] = []
    for node_index in range(node_count):
        minimum_head = min(snapshots, key=lambda item: item.heads_m[node_index])
        maximum_head = max(snapshots, key=lambda item: item.heads_m[node_index])
        minimum_flow = min(snapshots, key=lambda item: item.flows_m3_s[node_index])
        maximum_flow = max(snapshots, key=lambda item: item.flows_m3_s[node_index])
        envelopes.append(
            NodeTransientEnvelope(
                node_index=node_index,
                minimum_head_m=minimum_head.heads_m[node_index],
                maximum_head_m=maximum_head.heads_m[node_index],
                minimum_flow_m3_s=minimum_flow.flows_m3_s[node_index],
                maximum_flow_m3_s=maximum_flow.flows_m3_s[node_index],
                minimum_head_time_s=minimum_head.time_s,
                maximum_head_time_s=maximum_head.time_s,
                minimum_flow_time_s=minimum_flow.time_s,
                maximum_flow_time_s=maximum_flow.time_s,
            )
        )
    return TransientEnvelopeSet(
        node_count=node_count,
        start_time_s=snapshots[0].time_s,
        end_time_s=snapshots[-1].time_s,
        envelopes=tuple(envelopes),
    )


__all__ = [
    "NodeTransientEnvelope",
    "TransientEnvelopeSet",
    "build_transient_envelopes",
]
