"""Export et import de la topologie d'une version de modèle, au format JSON.

Le cahier des charges classe cet aller-retour parmi les exigences obligatoires :
un réseau exporté puis réimporté doit redonner exactement le même réseau. Le
format est volontairement lisible et indépendant des identifiants techniques :
les liens entre objets passent par les codes métier, stables et signifiants,
plutôt que par des UUID qui changeraient à chaque import.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from hydro_api.errors import ResourceConflictError
from hydro_api.models import CatalogItem, ModelVersion
from hydro_api.schemas.network import (
    AssetInstanceCreate,
    NetworkEdgeCreate,
    NetworkNodeCreate,
)
from hydro_api.services import network

#: Version du format d'échange. Un import refuse une version qu'il ne connaît pas
#: plutôt que d'interpréter approximativement un document plus récent.
TOPOLOGY_SCHEMA_VERSION = "hydro-topology/1"


def export_topology(session: Session, model: ModelVersion) -> dict[str, Any]:
    """Sérialise nœuds, tronçons et équipements d'une version de modèle."""

    nodes, edges, assets = network.model_components(session, model.id)
    node_codes = {node.id: node.code for node in nodes}
    edge_codes = {edge.id: edge.code for edge in edges}
    catalog_codes = _catalog_codes(session, {asset.catalog_item_id for asset in assets})

    return {
        "schema_version": TOPOLOGY_SCHEMA_VERSION,
        "nodes": [
            {
                "code": node.code,
                "name": node.name,
                "kind": node.kind,
                "elevation_m": node.elevation_m,
                "latitude": node.latitude,
                "longitude": node.longitude,
                "status": node.status,
                "payload": node.payload,
            }
            for node in sorted(nodes, key=lambda item: item.code)
        ],
        "edges": [
            {
                "code": edge.code,
                "name": edge.name,
                "from_node_code": node_codes[edge.from_node_id],
                "to_node_code": node_codes[edge.to_node_id],
                "material_catalog_code": _catalog_code(session, edge.material_catalog_item_id),
                "sequence": edge.sequence,
                "length_m": edge.length_m,
                "inner_diameter_m": edge.inner_diameter_m,
                "roughness_m": edge.roughness_m,
                "mawp_pa": edge.mawp_pa,
                "status": edge.status,
                "profile": edge.profile_payload,
                "fittings": edge.fittings_payload,
                "payload": edge.payload,
            }
            for edge in sorted(edges, key=lambda item: item.sequence)
        ],
        "assets": [
            {
                "code": asset.code,
                "name": asset.name,
                "catalog_code": catalog_codes[asset.catalog_item_id],
                "node_code": node_codes.get(asset.node_id) if asset.node_id else None,
                "edge_code": edge_codes.get(asset.edge_id) if asset.edge_id else None,
                "role": asset.role,
                "status": asset.status,
                "payload": asset.payload,
            }
            for asset in sorted(assets, key=lambda item: item.code)
        ],
    }


def import_topology(
    session: Session,
    model: ModelVersion,
    document: dict[str, Any],
    *,
    actor_id: uuid.UUID | None,
) -> dict[str, int]:
    """Recrée une topologie dans une version de modèle encore vide.

    L'import est refusé sur un modèle déjà peuplé : fusionner deux réseaux
    demanderait des règles de résolution de conflits que le MVP ne définit pas,
    et produirait un résultat non reproductible.
    """

    version = document.get("schema_version")
    if version != TOPOLOGY_SCHEMA_VERSION:
        raise ResourceConflictError(
            f"Format de topologie non pris en charge : « {version} » "
            f"au lieu de « {TOPOLOGY_SCHEMA_VERSION} »."
        )

    existing_nodes, existing_edges, existing_assets = network.model_components(session, model.id)
    if existing_nodes or existing_edges or existing_assets:
        raise ResourceConflictError(
            "La version de modèle contient déjà un réseau : importez une topologie "
            "dans une version vide."
        )

    node_ids: dict[str, uuid.UUID] = {}
    for entry in document.get("nodes") or []:
        created = network.create_network_node(
            session,
            model.id,
            NetworkNodeCreate.model_validate(
                {key: value for key, value in entry.items() if key != "code"}
                | {"code": entry["code"]}
            ),
            actor_id=actor_id,
        )
        node_ids[created.code] = created.id

    edge_ids: dict[str, uuid.UUID] = {}
    for entry in sorted(document.get("edges") or [], key=lambda item: item["sequence"]):
        payload = {
            "from_node_id": _resolve(node_ids, entry["from_node_code"], "nœud"),
            "to_node_id": _resolve(node_ids, entry["to_node_code"], "nœud"),
            "material_catalog_item_id": _catalog_id(session, entry.get("material_catalog_code")),
            "code": entry["code"],
            "name": entry["name"],
            "sequence": entry["sequence"],
            "length_m": entry["length_m"],
            "inner_diameter_m": entry["inner_diameter_m"],
            "roughness_m": entry["roughness_m"],
            "mawp_pa": entry["mawp_pa"],
            "status": entry.get("status", "available"),
            "profile": entry.get("profile") or [],
            "fittings": entry.get("fittings") or [],
            "payload": entry.get("payload") or {},
        }
        created_edge = network.create_network_edge(
            session,
            model.id,
            NetworkEdgeCreate.model_validate(payload),
            actor_id=actor_id,
        )
        edge_ids[created_edge.code] = created_edge.id

    asset_count = 0
    for entry in document.get("assets") or []:
        catalog_id = _catalog_id(session, entry.get("catalog_code"))
        if catalog_id is None:
            raise ResourceConflictError(
                f"L'équipement « {entry['code']} » référence un élément de catalogue absent."
            )
        network.create_asset_instance(
            session,
            model.id,
            AssetInstanceCreate.model_validate(
                {
                    "catalog_item_id": catalog_id,
                    "node_id": (
                        _resolve(node_ids, entry["node_code"], "nœud")
                        if entry.get("node_code")
                        else None
                    ),
                    "edge_id": (
                        _resolve(edge_ids, entry["edge_code"], "tronçon")
                        if entry.get("edge_code")
                        else None
                    ),
                    "code": entry["code"],
                    "name": entry["name"],
                    "role": entry.get("role", "main"),
                    "status": entry.get("status", "available"),
                    "payload": entry.get("payload") or {},
                }
            ),
            actor_id=actor_id,
        )
        asset_count += 1

    return {
        "nodes": len(node_ids),
        "edges": len(edge_ids),
        "assets": asset_count,
    }


def _resolve(mapping: dict[str, uuid.UUID], code: str, label: str) -> uuid.UUID:
    identifier = mapping.get(code)
    if identifier is None:
        raise ResourceConflictError(
            f"La topologie référence un {label} « {code} » qu'elle ne définit pas."
        )
    return identifier


def _catalog_code(session: Session, catalog_item_id: uuid.UUID | None) -> str | None:
    if catalog_item_id is None:
        return None
    item = session.get(CatalogItem, catalog_item_id)
    return item.code if item is not None else None


def _catalog_codes(session: Session, identifiers: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    codes: dict[uuid.UUID, str] = {}
    for identifier in identifiers:
        item = session.get(CatalogItem, identifier)
        if item is None:
            raise ResourceConflictError(
                "Un équipement du modèle référence un élément de catalogue supprimé."
            )
        codes[identifier] = item.code
    return codes


def _catalog_id(session: Session, code: str | None) -> uuid.UUID | None:
    """Retrouve l'élément de catalogue approuvé le plus récent portant ce code."""

    if not code:
        return None
    from sqlalchemy import select

    item = session.scalars(
        select(CatalogItem)
        .where(CatalogItem.code == code)
        .order_by(CatalogItem.version_number.desc())
    ).first()
    return item.id if item is not None else None


__all__ = ["TOPOLOGY_SCHEMA_VERSION", "export_topology", "import_topology"]
