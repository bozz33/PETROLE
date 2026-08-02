"""Sérialisation canonique et empreintes.

Au lancement d'un calcul, les entrées résolues sont matérialisées dans un **paquet d'entrée
canonique** qui reçoit une empreinte et reste accessible même si le catalogue ou le scénario
évolue ensuite (D12 § 5). L'empreinte sert aussi à la déduplication des calculs et à
l'idempotence des imports (D13 § 10).

La canonicalisation doit être **stable** : mêmes entrées ⇒ même empreinte, indépendamment de
l'ordre des clés, de la plateforme et de la version de Python.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

#: Nombre de chiffres significatifs conservés pour les flottants dans la forme canonique.
#: 15 chiffres restent en deçà de la précision d'un ``float64`` (~15,95 chiffres décimaux),
#: ce qui rend l'empreinte insensible au dernier bit de mantisse tout en préservant la
#: distinction de deux valeurs physiquement différentes.
FLOAT_PRECISION = 15


def _normalise(value: Any) -> Any:
    """Réduit une valeur arbitraire à des types JSON déterministes."""
    if value is None or isinstance(value, bool | str | int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        # `repr` du float arrondi élimine les écarts de dernier bit sans perdre d'information
        # physique, et garantit une écriture identique sur toutes les plateformes.
        return float(f"{value:.{FLOAT_PRECISION}g}")
    if isinstance(value, Decimal):
        return _normalise(float(value))
    if isinstance(value, Enum):
        return _normalise(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if is_dataclass(value) and not isinstance(value, type):
        return _normalise(asdict(value))
    if isinstance(value, dict):
        return {str(k): _normalise(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, list | tuple):
        return [_normalise(v) for v in value]
    if isinstance(value, set | frozenset):
        return [_normalise(v) for v in sorted(value, key=repr)]
    if hasattr(value, "as_dict"):
        return _normalise(value.as_dict())
    if hasattr(value, "model_dump"):
        return _normalise(value.model_dump(mode="python"))
    raise TypeError(f"Type non sérialisable de façon canonique : {type(value)!r}")


def canonical_json(value: Any) -> str:
    """Retourne la forme JSON canonique : clés triées, séparateurs compacts, UTF-8 littéral."""
    return json.dumps(
        _normalise(value),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_of(value: Any) -> str:
    """Empreinte SHA-256 de la forme canonique, préfixée par l'algorithme."""
    payload = canonical_json(value).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def sha256_of_bytes(payload: bytes) -> str:
    """Empreinte SHA-256 d'un contenu binaire (fichier importé, rapport généré)."""
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def short_hash(fingerprint: str, length: int = 12) -> str:
    """Forme abrégée d'une empreinte, pour l'affichage et les noms de fichiers."""
    digest = fingerprint.split(":", 1)[-1]
    return digest[:length]
