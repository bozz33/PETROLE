"""Export déterministe de résultats gaz déjà calculés.

P6-G doit rendre les résultats, hypothèses, diagnostics et provenances
traçables. Ce module sérialise uniquement des valeurs déjà produites par les
briques scientifiques ; il ne recalcule ni propriétés, ni hydraulique, ni
performance compresseur et ne transforme aucun diagnostic en verdict.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Les horodatages exportés doivent être timezone-aware.")
        return value.isoformat()
    raise TypeError(f"Type non sérialisable dans l'export gaz : {type(value)!r}")


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class GasResultExportArtifact:
    """Artefact JSON avec empreinte SHA-256 calculée sur le contenu exact."""

    media_type: str
    filename: str
    content: bytes
    sha256: str


def export_gas_results_json(
    payload: dict[str, Any],
    *,
    export_version: str = "phase6-gas/1.0",
) -> GasResultExportArtifact:
    """Sérialise un résultat gaz pré-calculé dans une enveloppe canonique.

    Les champs obligatoires empêchent qu'un export soit publié sans version de
    modèle ni provenance des propriétés et de la composition. Les blocs
    ``results`` et ``diagnostics`` restent génériques afin de pouvoir contenir
    les sorties P6-B à P6-F au fur et à mesure de leur qualification.
    """

    if not export_version.strip():
        raise ValueError("La version d'export gaz est obligatoire.")

    required = (
        "calculation_ref",
        "model_version",
        "composition_source_ref",
        "property_method_ref",
        "results",
        "diagnostics",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Résultat gaz incomplet : {', '.join(missing)}.")

    reference_fields = (
        "calculation_ref",
        "model_version",
        "composition_source_ref",
        "property_method_ref",
    )
    for field in reference_fields:
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Le champ {field} doit être une chaîne non vide.")

    document = {
        "export_version": export_version,
        "calculation_ref": payload["calculation_ref"],
        "model_version": payload["model_version"],
        "composition_source_ref": payload["composition_source_ref"],
        "property_method_ref": payload["property_method_ref"],
        "generated_at": payload.get("generated_at"),
        "assumptions": payload.get("assumptions", {}),
        "results": payload["results"],
        "diagnostics": payload["diagnostics"],
        "source_refs": payload.get("source_refs", []),
    }
    content = _canonical_json(document)
    return GasResultExportArtifact(
        media_type="application/json",
        filename="gas-results.json",
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


__all__ = ["GasResultExportArtifact", "export_gas_results_json"]
