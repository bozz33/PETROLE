"""Versions de la plateforme et empreinte de l'environnement scientifique.

Chaque calcul enregistre la version du moteur, le commit applicatif et les versions des
dépendances scientifiques (D-v2 § 9.2). Sans cette empreinte, un résultat n'est pas
reproductible et ne peut pas être approuvé.

Le versionnement de l'application et celui du moteur scientifique sont **indépendants**
(D18 § 11) : une correction d'interface ne doit pas invalider un dossier de validation.
"""

from __future__ import annotations

import platform
import sys
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from typing import Any

#: Version de l'application (API, interface, persistance).
PLATFORM_VERSION = "0.1.0"

#: Version du noyau scientifique HydroLiquid Core. Toute modification d'une équation, d'une
#: corrélation ou d'un critère de convergence impose d'incrémenter cette version et de
#: produire une note de migration scientifique (D-v2 § 13.3).
ENGINE_VERSION = "hydroliquid-0.1.0"

#: Version du schéma du paquet d'entrée canonique (D12 § 12).
INPUT_SCHEMA_VERSION = "hydro-input/1"

#: Version du schéma de résultat exposé par l'API.
RESULT_SCHEMA_VERSION = "hydro-result/1"

#: Dépendances dont la version influence les résultats numériques.
SCIENTIFIC_DEPENDENCIES = ("numpy", "scipy", "fluids", "CoolProp", "Pint", "Pyomo")


def _safe_version(distribution: str) -> str:
    try:
        return _pkg_version(distribution)
    except PackageNotFoundError:
        return "absent"


@lru_cache(maxsize=1)
def scientific_environment() -> dict[str, str]:
    """Versions des bibliothèques scientifiques effectivement chargées."""
    return {name: _safe_version(name) for name in SCIENTIFIC_DEPENDENCIES}


@lru_cache(maxsize=1)
def engine_fingerprint(commit: str | None = None) -> dict[str, Any]:
    """Empreinte complète de l'environnement de calcul, jointe à chaque résultat."""
    return {
        "platform_version": PLATFORM_VERSION,
        "engine_version": ENGINE_VERSION,
        "input_schema_version": INPUT_SCHEMA_VERSION,
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "commit": commit,
        "python": sys.version.split()[0],
        "os": f"{platform.system()} {platform.release()}",
        "dependencies": scientific_environment(),
    }
