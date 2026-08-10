"""Fondations déterministes de séquencement multiproduit.

Ce module décrit l'ordre des lots injectés et la position de leurs interfaces
dans un axe de volume cumulé. Il ne calcule ni dispersion, ni mélange, ni
position spatiale dans une conduite : ces phénomènes exigent un modèle
physique, des propriétés produit et des benchmarks séparés.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductBatch:
    """Lot produit identifié par une référence et un volume planifié."""

    batch_id: str
    product_ref: str
    volume_m3: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.batch_id.strip():
            raise ValueError("L'identifiant du lot produit est obligatoire.")
        if not self.product_ref.strip():
            raise ValueError("La référence produit est obligatoire.")
        if not math.isfinite(self.volume_m3) or self.volume_m3 <= 0:
            raise ValueError("Le volume du lot doit être fini et strictement positif.")
        if not self.source_ref.strip():
            raise ValueError("La provenance du lot produit est obligatoire.")


@dataclass(frozen=True, slots=True)
class ProductInterface:
    """Frontière logique entre deux lots dans l'axe de volume injecté."""

    upstream_batch_id: str
    downstream_batch_id: str
    cumulative_volume_m3: float


@dataclass(frozen=True, slots=True)
class BatchSequence:
    """Séquence immuable de lots et interfaces planifiées."""

    batches: tuple[ProductBatch, ...]
    interfaces: tuple[ProductInterface, ...]
    total_volume_m3: float


def build_batch_sequence(batches: tuple[ProductBatch, ...]) -> BatchSequence:
    """Construit les interfaces à partir de l'ordre de lots fourni.

    Le volume cumulé d'une interface correspond à la somme des volumes de tous
    les lots injectés jusqu'au lot amont inclus. Aucun volume d'interface ou de
    contamination n'est ajouté implicitement.
    """

    if not batches:
        raise ValueError("Une séquence multiproduit doit contenir au moins un lot.")
    batch_ids = [batch.batch_id for batch in batches]
    if len(batch_ids) != len(set(batch_ids)):
        raise ValueError("Les identifiants de lots doivent être uniques dans la séquence.")

    interfaces: list[ProductInterface] = []
    cumulative_volume = 0.0
    for index, batch in enumerate(batches):
        cumulative_volume += batch.volume_m3
        if index < len(batches) - 1:
            interfaces.append(
                ProductInterface(
                    upstream_batch_id=batch.batch_id,
                    downstream_batch_id=batches[index + 1].batch_id,
                    cumulative_volume_m3=cumulative_volume,
                )
            )
    return BatchSequence(
        batches=batches,
        interfaces=tuple(interfaces),
        total_volume_m3=cumulative_volume,
    )


__all__ = [
    "BatchSequence",
    "ProductBatch",
    "ProductInterface",
    "build_batch_sequence",
]
