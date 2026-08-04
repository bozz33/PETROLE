"""Contrat numérique et JSON strict pour toutes les sorties de la plateforme.

La RFC 8259 (standard JSON) interdit ``NaN``, ``Infinity`` et ``-Infinity``.
PostgreSQL rejette donc ces valeurs dans ses colonnes ``json``/``jsonb``, tandis
que SQLite et l'encodeur Python par défaut (``allow_nan=True``) les acceptent en
silence. Cette divergence a déjà masqué un défaut de production : un calcul
non convergent produisait un ``residual`` à ``NaN`` qui cassait la persistance
du worker en PostgreSQL tout en passant les tests SQLite.

Ce module impose un contrat unique applicable à tous les moteurs, rapports,
règles, API et écritures en base (ADR-TEST-DB-001) :

* :func:`normalize_json_numbers` traverse une structure, remplace les nombres
  non finis par ``None`` et décrit chaque occurrence (chemin + nature) afin de
  conserver un diagnostic scientifique exploitable ;
* :func:`strict_json_dumps` sérialise en JSON conforme RFC 8259
  (``allow_nan=False``) : c'est la dernière barrière avant PostgreSQL.

Les scalaires NumPy (``numpy.floating``) produits par les moteurs scientifiques
sont convertis en ``float`` Python avant contrôle.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class NonFiniteKind(StrEnum):
    """Nature d'une valeur non finie détectée pendant la normalisation."""

    NAN = "nan"
    POSITIVE_INFINITY = "positive_infinity"
    NEGATIVE_INFINITY = "negative_infinity"


@dataclass(frozen=True, slots=True)
class NonFiniteOccurrence:
    """Localisation d'une valeur non finie dans la structure normalisée."""

    path: str
    kind: NonFiniteKind


@dataclass(frozen=True, slots=True)
class JsonNormalizationResult:
    """Résultat d'une normalisation : valeur nettoyée et occurrences constatées."""

    value: Any
    occurrences: tuple[NonFiniteOccurrence, ...]

    @property
    def has_non_finite(self) -> bool:
        """Indique si au moins une valeur non finie a été neutralisée."""

        return bool(self.occurrences)


def _to_python_float(item: Any) -> float | None:
    """Convertit un scalaire numérique en float Python ou renvoie None.

    Les moteurs scientifiques manipulent des ``numpy.floating`` : ils doivent
    redevenir des ``float`` Python avant tout contrôle de finitude ou de
    sérialisation JSON.
    """

    try:
        import numpy  # import différé : numpy n'est pas requis pour les tests purs
    except ImportError:  # pragma: no cover - numpy est une dépendance du projet
        numpy = None  # type: ignore[assignment]

    if numpy is not None and isinstance(item, numpy.floating):
        return float(item)
    if isinstance(item, float):
        return item
    return None


def _classify_non_finite(item: float) -> NonFiniteKind:
    """Identifie la nature d'un flottant non fini."""

    if math.isnan(item):
        return NonFiniteKind.NAN
    return NonFiniteKind.POSITIVE_INFINITY if item > 0 else NonFiniteKind.NEGATIVE_INFINITY


def normalize_json_numbers(
    value: Any,
    *,
    path: str = "$",
) -> JsonNormalizationResult:
    """Normalise une structure en remplaçant les non-finis par ``None``.

    La valeur d'origine n'est pas mutée. Chaque occurrence non finie est
    conservée dans le résultat pour alimentation du diagnostic
    ``data_quality.non_finite_values``.
    """

    occurrences: list[NonFiniteOccurrence] = []

    def visit(item: Any, current_path: str) -> Any:
        if item is None or isinstance(item, (str, bool, int)):
            return item

        as_float = _to_python_float(item)
        if as_float is not None:
            if math.isfinite(as_float):
                return as_float
            occurrences.append(
                NonFiniteOccurrence(path=current_path, kind=_classify_non_finite(as_float))
            )
            return None

        if isinstance(item, dict):
            return {str(key): visit(child, f"{current_path}.{key}") for key, child in item.items()}

        if isinstance(item, (list, tuple)):
            return [visit(child, f"{current_path}[{index}]") for index, child in enumerate(item)]

        raise TypeError(f"Type non compatible JSON à {current_path}: {type(item).__name__}")

    normalized = visit(value, path)
    return JsonNormalizationResult(
        value=normalized,
        occurrences=tuple(occurrences),
    )


def strict_json_dumps(value: Any) -> str:
    """Sérialise en JSON strictement conforme à la RFC 8259.

    ``allow_nan=False`` lève une :class:`ValueError` dès qu'une valeur non
    conforme échappe au normalisateur. C'est la barrière finale avant
    PostgreSQL : toute fuite devient une erreur explicite et contrôlée.
    """

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


__all__ = [
    "JsonNormalizationResult",
    "NonFiniteKind",
    "NonFiniteOccurrence",
    "normalize_json_numbers",
    "strict_json_dumps",
]
