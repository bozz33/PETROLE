"""Snapshots versionnés du jumeau numérique analytique PETROLE.

Cette brique garantit traçabilité, unités et empreinte de contenu. Elle ne
constitue ni un estimateur d'état, ni un détecteur de fuite qualifié et ne
commande aucun actif industriel.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class TwinStateVariable:
    """Variable SI accompagnée de sa source de provenance."""

    name: str
    value_si: float
    unit: str
    source_ref: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Le nom d'une variable du jumeau est obligatoire.")
        if not math.isfinite(self.value_si):
            raise ValueError("La valeur d'une variable du jumeau doit être finie.")
        if not self.unit.strip():
            raise ValueError("L'unité SI d'une variable du jumeau est obligatoire.")
        if not self.source_ref.strip():
            raise ValueError("La provenance d'une variable du jumeau est obligatoire.")


@dataclass(frozen=True, slots=True)
class DigitalTwinSnapshot:
    """État immuable et adressé par contenu d'une version de modèle."""

    model_version: str
    observed_at: datetime
    sequence_number: int
    variables: tuple[TwinStateVariable, ...]
    content_hash: str


def build_twin_snapshot(
    *,
    model_version: str,
    observed_at: datetime,
    sequence_number: int,
    variables: tuple[TwinStateVariable, ...],
) -> DigitalTwinSnapshot:
    """Canonicalise et empreinte un snapshot sans identifiant aléatoire."""

    if not model_version.strip():
        raise ValueError("La version de modèle du jumeau est obligatoire.")
    if observed_at.tzinfo is None:
        raise ValueError("L'horodatage du jumeau doit être timezone-aware.")
    if sequence_number < 1:
        raise ValueError("La séquence du jumeau doit être strictement positive.")
    if not variables:
        raise ValueError("Un snapshot du jumeau doit contenir au moins une variable.")
    names = [variable.name for variable in variables]
    if len(set(names)) != len(names):
        raise ValueError("Les noms de variables doivent être uniques dans un snapshot.")

    ordered = tuple(sorted(variables, key=lambda variable: variable.name))
    normalized_time = observed_at.astimezone(UTC)
    payload = {
        "model_version": model_version,
        "observed_at": normalized_time.isoformat().replace("+00:00", "Z"),
        "sequence_number": sequence_number,
        "variables": [
            {
                "name": variable.name,
                "value_si": variable.value_si,
                "unit": variable.unit,
                "source_ref": variable.source_ref,
            }
            for variable in ordered
        ],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return DigitalTwinSnapshot(
        model_version=model_version,
        observed_at=normalized_time,
        sequence_number=sequence_number,
        variables=ordered,
        content_hash=digest,
    )


def state_delta(
    previous: DigitalTwinSnapshot,
    current: DigitalTwinSnapshot,
) -> dict[str, float]:
    """Retourne les deltas SI uniquement pour les variables comparables."""

    if previous.model_version != current.model_version:
        raise ValueError(
            "Deux snapshots de versions de modèle différentes ne sont pas comparables."
        )
    if current.sequence_number <= previous.sequence_number:
        raise ValueError("Le snapshot courant doit avoir une séquence postérieure.")
    previous_by_name = {variable.name: variable for variable in previous.variables}
    deltas: dict[str, float] = {}
    for variable in current.variables:
        old = previous_by_name.get(variable.name)
        if old is None:
            continue
        if old.unit != variable.unit:
            raise ValueError(f"Unité incohérente pour la variable {variable.name}.")
        deltas[variable.name] = variable.value_si - old.value_si
    return deltas


__all__ = [
    "DigitalTwinSnapshot",
    "TwinStateVariable",
    "build_twin_snapshot",
    "state_delta",
]
