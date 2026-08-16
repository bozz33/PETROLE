#!/usr/bin/env python3
"""Construit REF-MVP-01 avec le compte unique de l'ingénieur utilisateur.

Le générateur historique ``projet_reference.py`` est conservé pour compatibilité
avec les anciens déploiements multi-utilisateurs. Cette façade réutilise toute
sa logique de construction mais neutralise ses anciens appels ``/approve`` : en
mode ``single_org`` les références sont rendues disponibles automatiquement par
l'API et aucune seconde identité humaine n'est requise.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_legacy_module() -> ModuleType:
    path = Path(__file__).with_name("projet_reference.py")
    specification = importlib.util.spec_from_file_location("petrole_projet_reference", path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Impossible de charger {path}.")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class ApprovalDisabledClient:
    """Compatibilité avec l'ancien générateur sans appeler de route d'approbation."""

    def request(self, method: str, path: str, payload: Any = None, **_: Any) -> dict[str, str]:
        del payload
        if method.upper() == "POST" and path.endswith("/approve"):
            return {"status": "disabled-single-user"}
        raise RuntimeError(f"Appel inattendu sur le client d'approbation désactivé : {method} {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    arguments = parser.parse_args()

    legacy = _load_legacy_module()
    client = legacy.Client(arguments.base_url)
    client.login(arguments.email, arguments.password)

    organizations = client.request("GET", "/organizations?limit=1&offset=0")
    if not organizations["items"]:
        print("Aucune organisation accessible.", file=sys.stderr)
        return 1
    organization_id = organizations["items"][0]["id"]

    try:
        summary = legacy.build(client, ApprovalDisabledClient(), organization_id)
    except legacy.ApiError as error:
        print(f"Échec : {error}", file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
