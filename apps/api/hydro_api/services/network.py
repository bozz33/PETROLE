"""Services transactionnels d'édition et de validation du réseau."""

from __future__ import annotations

import uuid
from collections import Counter, deque
from copy import deepcopy
from itertools import pairwise
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AssetInstance,
    AuditEvent,
    CatalogItem,
    ModelVersion,
    NetworkEdge,
    NetworkNode,
    ScenarioRecord,
    TankRecord,
)
from hydro_api.schemas.network import (
    AssetInstanceCreate,
    AssetInstanceUpdate,
    ModelCloneCreate,
    NetworkEdgeCreate,
    NetworkEdgeUpdate,
    NetworkNodeCreate,
    NetworkNodeUpdate,
    NetworkValidationIssue,
    NetworkValidationReport,
)
from hydro_shared.errors import InvalidInputError
from hydro_shared.hashing import sha256_of


def _get_model(session: Session, model_id: uuid.UUID, *, mutable: bool = False) -> ModelVersion:
    """Charge une version et exige un brouillon pour toute mutation."""

    model = session.get(ModelVersion, model_id)
    if model is None:
        raise ResourceNotFoundError("Version de modèle", model_id)
    if mutable and model.status != "draft":
        raise ResourceConflictError(
            "Une version approuvée ou archivée est immuable ; créez une nouvelle version."
        )
    return model


def _organization_id(model: ModelVersion) -> uuid.UUID:
    """Retourne le tenant propriétaire du modèle."""

    return model.project.organization_id


def _audit(
    session: Session,
    model: ModelVersion,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None,
    details: dict[str, Any] | None = None,
) -> None:
    """Ajoute un événement append-only corrélé à la mutation réseau."""

    session.add(
        AuditEvent(
            organization_id=_organization_id(model),
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details or {},
            created_at=utc_now(),
        )
    )


def _flush(session: Session, message: str) -> None:
    """Convertit une contrainte SQL en conflit API explicite."""

    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ResourceConflictError(message) from error


def get_network_node(session: Session, node_id: uuid.UUID) -> NetworkNode:
    node = session.get(NetworkNode, node_id)
    if node is None:
        raise ResourceNotFoundError("Nœud réseau", node_id)
    return node


def get_network_edge(session: Session, edge_id: uuid.UUID) -> NetworkEdge:
    edge = session.get(NetworkEdge, edge_id)
    if edge is None:
        raise ResourceNotFoundError("Tronçon réseau", edge_id)
    return edge


def get_asset_instance(session: Session, asset_id: uuid.UUID) -> AssetInstance:
    asset = session.get(AssetInstance, asset_id)
    if asset is None:
        raise ResourceNotFoundError("Équipement placé", asset_id)
    return asset


def _model_components(
    session: Session,
    model_id: uuid.UUID,
) -> tuple[list[NetworkNode], list[NetworkEdge], list[AssetInstance]]:
    """Charge les composants dans un ordre stable pour validation et empreinte."""

    nodes = list(
        session.scalars(
            select(NetworkNode)
            .where(NetworkNode.model_version_id == model_id)
            .order_by(NetworkNode.code)
        )
    )
    edges = list(
        session.scalars(
            select(NetworkEdge)
            .where(NetworkEdge.model_version_id == model_id)
            .order_by(NetworkEdge.sequence, NetworkEdge.code)
        )
    )
    assets = list(
        session.scalars(
            select(AssetInstance)
            .where(AssetInstance.model_version_id == model_id)
            .order_by(AssetInstance.code)
        )
    )
    return nodes, edges, assets


def refresh_model_hash(session: Session, model: ModelVersion) -> str:
    """Inclut réseau et équipements dans l'empreinte de la version."""

    nodes, edges, assets = _model_components(session, model.id)
    node_codes = {node.id: node.code for node in nodes}
    edge_codes = {edge.id: edge.code for edge in edges}
    model.content_hash = sha256_of(
        {
            "payload": model.payload,
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
                for node in nodes
            ],
            "edges": [
                {
                    "from_node_code": node_codes[edge.from_node_id],
                    "to_node_code": node_codes[edge.to_node_id],
                    "material_catalog_item_id": edge.material_catalog_item_id,
                    "code": edge.code,
                    "name": edge.name,
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
                for edge in edges
            ],
            "assets": [
                {
                    "catalog_item_id": asset.catalog_item_id,
                    "node_code": node_codes[asset.node_id] if asset.node_id is not None else None,
                    "edge_code": edge_codes[asset.edge_id] if asset.edge_id is not None else None,
                    "code": asset.code,
                    "name": asset.name,
                    "role": asset.role,
                    "status": asset.status,
                    "payload": asset.payload,
                }
                for asset in assets
            ],
        }
    )
    session.flush()
    return model.content_hash


def clone_model_version(
    session: Session,
    model_id: uuid.UUID,
    data: ModelCloneCreate,
    *,
    actor_id: uuid.UUID | None = None,
) -> ModelVersion:
    """Clone une version et remappe toutes ses références internes."""

    from hydro_api.schemas.core import ModelVersionCreate
    from hydro_api.services.core import create_model_version

    source = _get_model(session, model_id)
    clone = create_model_version(
        session,
        source.project_id,
        ModelVersionCreate(
            name=data.name,
            parent_id=source.id,
            payload=deepcopy(source.payload),
        ),
    )
    nodes, edges, assets = _model_components(session, source.id)
    scenarios = list(
        session.scalars(
            select(ScenarioRecord)
            .where(ScenarioRecord.model_version_id == source.id)
            .order_by(ScenarioRecord.created_at, ScenarioRecord.id)
        )
    )
    node_ids: dict[uuid.UUID, uuid.UUID] = {}
    for node in nodes:
        copied_node = NetworkNode(
            model_version_id=clone.id,
            code=node.code,
            name=node.name,
            kind=node.kind,
            elevation_m=node.elevation_m,
            latitude=node.latitude,
            longitude=node.longitude,
            status=node.status,
            payload=deepcopy(node.payload),
        )
        session.add(copied_node)
        session.flush()
        node_ids[node.id] = copied_node.id

    edge_ids: dict[uuid.UUID, uuid.UUID] = {}
    for edge in edges:
        copied_edge = NetworkEdge(
            model_version_id=clone.id,
            from_node_id=node_ids[edge.from_node_id],
            to_node_id=node_ids[edge.to_node_id],
            material_catalog_item_id=edge.material_catalog_item_id,
            code=edge.code,
            name=edge.name,
            sequence=edge.sequence,
            length_m=edge.length_m,
            inner_diameter_m=edge.inner_diameter_m,
            roughness_m=edge.roughness_m,
            mawp_pa=edge.mawp_pa,
            status=edge.status,
            profile_payload=deepcopy(edge.profile_payload),
            fittings_payload=deepcopy(edge.fittings_payload),
            payload=deepcopy(edge.payload),
        )
        session.add(copied_edge)
        session.flush()
        edge_ids[edge.id] = copied_edge.id

    for asset in assets:
        session.add(
            AssetInstance(
                model_version_id=clone.id,
                catalog_item_id=asset.catalog_item_id,
                node_id=node_ids[asset.node_id] if asset.node_id is not None else None,
                edge_id=edge_ids[asset.edge_id] if asset.edge_id is not None else None,
                code=asset.code,
                name=asset.name,
                role=asset.role,
                status=asset.status,
                payload=deepcopy(asset.payload),
            )
        )
    scenario_ids: dict[uuid.UUID, uuid.UUID] = {}
    copied_scenarios: dict[uuid.UUID, ScenarioRecord] = {}
    for scenario in scenarios:
        copied_scenario = ScenarioRecord(
            model_version_id=clone.id,
            parent_id=None,
            name=scenario.name,
            description=scenario.description,
            payload=deepcopy(scenario.payload),
        )
        session.add(copied_scenario)
        session.flush()
        scenario_ids[scenario.id] = copied_scenario.id
        copied_scenarios[scenario.id] = copied_scenario
    for scenario in scenarios:
        if scenario.parent_id is not None and scenario.parent_id in scenario_ids:
            copied_scenarios[scenario.id].parent_id = scenario_ids[scenario.parent_id]
    session.flush()
    refresh_model_hash(session, clone)
    _audit(
        session,
        clone,
        "model_version.cloned",
        "model_version",
        clone.id,
        actor_id=actor_id,
        details={
            "source_model_id": str(source.id),
            "nodes": len(nodes),
            "edges": len(edges),
            "assets": len(assets),
            "scenarios": len(scenarios),
        },
    )
    session.flush()
    return clone


def create_network_node(
    session: Session,
    model_id: uuid.UUID,
    data: NetworkNodeCreate,
    *,
    actor_id: uuid.UUID | None = None,
) -> NetworkNode:
    model = _get_model(session, model_id, mutable=True)
    node = NetworkNode(model_version_id=model.id, **data.model_dump())
    session.add(node)
    _flush(session, f"Le code nœud « {data.code} » existe déjà dans cette version.")
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "network_node.created",
        "network_node",
        node.id,
        actor_id=actor_id,
        details={"code": node.code, "kind": node.kind},
    )
    return node


def list_network_nodes(
    session: Session,
    model_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[NetworkNode], int]:
    _get_model(session, model_id)
    condition = NetworkNode.model_version_id == model_id
    total = session.scalar(select(func.count()).select_from(NetworkNode).where(condition))
    items = session.scalars(
        select(NetworkNode).where(condition).order_by(NetworkNode.code).limit(limit).offset(offset)
    ).all()
    return list(items), int(total or 0)


def update_network_node(
    session: Session,
    node_id: uuid.UUID,
    data: NetworkNodeUpdate,
    *,
    actor_id: uuid.UUID | None = None,
) -> NetworkNode:
    node = get_network_node(session, node_id)
    model = _get_model(session, node.model_version_id, mutable=True)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(node, field, value)
    _flush(session, "La modification du nœud crée un conflit.")
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "network_node.updated",
        "network_node",
        node.id,
        actor_id=actor_id,
        details={"fields": sorted(changes)},
    )
    return node


def delete_network_node(
    session: Session,
    node_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> None:
    """Supprime un nœud isolé d'un brouillon sans cascade implicite."""

    node = get_network_node(session, node_id)
    model = _get_model(session, node.model_version_id, mutable=True)
    edge_reference = session.scalar(
        select(NetworkEdge.id).where(
            (NetworkEdge.from_node_id == node.id) | (NetworkEdge.to_node_id == node.id)
        )
    )
    asset_reference = session.scalar(
        select(AssetInstance.id).where(AssetInstance.node_id == node.id)
    )
    if edge_reference is not None or asset_reference is not None:
        raise ResourceConflictError(
            "Supprimez d'abord les tronçons et équipements qui référencent ce nœud."
        )
    code = node.code
    session.delete(node)
    session.flush()
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "network_node.deleted",
        "network_node",
        node.id,
        actor_id=actor_id,
        details={"code": code},
    )


def _validate_material(session: Session, model: ModelVersion, item_id: uuid.UUID | None) -> None:
    """Vérifie qu'un tronçon référence un matériau du même tenant."""

    if item_id is None:
        return
    item = session.get(CatalogItem, item_id)
    if item is None:
        raise ResourceNotFoundError("Matériau de catalogue", item_id)
    if item.organization_id != _organization_id(model) or item.kind != "material":
        raise ResourceConflictError(
            "Le matériau doit appartenir à l'organisation du modèle et être de type material."
        )


def _validate_edge_nodes(
    session: Session,
    model_id: uuid.UUID,
    from_node_id: uuid.UUID,
    to_node_id: uuid.UUID,
) -> None:
    """Garantit que les deux extrémités appartiennent au même modèle."""

    start = get_network_node(session, from_node_id)
    end = get_network_node(session, to_node_id)
    if start.model_version_id != model_id or end.model_version_id != model_id:
        raise ResourceConflictError("Les deux nœuds doivent appartenir à cette version de modèle.")
    if start.id == end.id:
        raise ValueError("Un tronçon doit relier deux nœuds différents.")


def create_network_edge(
    session: Session,
    model_id: uuid.UUID,
    data: NetworkEdgeCreate,
    *,
    actor_id: uuid.UUID | None = None,
) -> NetworkEdge:
    model = _get_model(session, model_id, mutable=True)
    _validate_edge_nodes(session, model.id, data.from_node_id, data.to_node_id)
    _validate_material(session, model, data.material_catalog_item_id)
    values = data.model_dump(exclude={"profile", "fittings"})
    edge = NetworkEdge(
        model_version_id=model.id,
        profile_payload=[point.model_dump() for point in data.profile],
        fittings_payload=data.fittings,
        **values,
    )
    session.add(edge)
    _flush(
        session,
        f"Le code ou la séquence du tronçon « {data.code} » existe déjà dans cette version.",
    )
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "network_edge.created",
        "network_edge",
        edge.id,
        actor_id=actor_id,
        details={"code": edge.code, "sequence": edge.sequence},
    )
    return edge


def list_network_edges(
    session: Session,
    model_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[NetworkEdge], int]:
    _get_model(session, model_id)
    condition = NetworkEdge.model_version_id == model_id
    total = session.scalar(select(func.count()).select_from(NetworkEdge).where(condition))
    items = session.scalars(
        select(NetworkEdge)
        .where(condition)
        .order_by(NetworkEdge.sequence)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), int(total or 0)


def _merged_edge_input(edge: NetworkEdge, data: NetworkEdgeUpdate) -> NetworkEdgeCreate:
    """Revalide le profil complet après une mise à jour partielle."""

    changes = data.model_dump(exclude_unset=True)
    return NetworkEdgeCreate.model_validate(
        {
            "from_node_id": changes.get("from_node_id", edge.from_node_id),
            "to_node_id": changes.get("to_node_id", edge.to_node_id),
            "material_catalog_item_id": changes.get(
                "material_catalog_item_id",
                edge.material_catalog_item_id,
            ),
            "code": edge.code,
            "name": changes.get("name", edge.name),
            "sequence": changes.get("sequence", edge.sequence),
            "length_m": changes.get("length_m", edge.length_m),
            "inner_diameter_m": changes.get("inner_diameter_m", edge.inner_diameter_m),
            "roughness_m": changes.get("roughness_m", edge.roughness_m),
            "mawp_pa": changes.get("mawp_pa", edge.mawp_pa),
            "status": changes.get("status", edge.status),
            "profile": changes.get("profile", edge.profile_payload),
            "fittings": changes.get("fittings", edge.fittings_payload),
            "payload": changes.get("payload", edge.payload),
        }
    )


def update_network_edge(
    session: Session,
    edge_id: uuid.UUID,
    data: NetworkEdgeUpdate,
    *,
    actor_id: uuid.UUID | None = None,
) -> NetworkEdge:
    edge = get_network_edge(session, edge_id)
    model = _get_model(session, edge.model_version_id, mutable=True)
    merged = _merged_edge_input(edge, data)
    _validate_edge_nodes(session, model.id, merged.from_node_id, merged.to_node_id)
    _validate_material(session, model, merged.material_catalog_item_id)
    values = merged.model_dump(exclude={"code", "profile", "fittings"})
    for field, value in values.items():
        setattr(edge, field, value)
    edge.profile_payload = [point.model_dump() for point in merged.profile]
    edge.fittings_payload = merged.fittings
    _flush(session, "La modification du tronçon crée un conflit de code ou de séquence.")
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "network_edge.updated",
        "network_edge",
        edge.id,
        actor_id=actor_id,
        details={"fields": sorted(data.model_fields_set)},
    )
    return edge


def delete_network_edge(
    session: Session,
    edge_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> None:
    """Supprime un tronçon sans supprimer ses équipements par surprise."""

    edge = get_network_edge(session, edge_id)
    model = _get_model(session, edge.model_version_id, mutable=True)
    asset_reference = session.scalar(
        select(AssetInstance.id).where(AssetInstance.edge_id == edge.id)
    )
    if asset_reference is not None:
        raise ResourceConflictError("Supprimez d'abord les équipements placés sur ce tronçon.")
    code = edge.code
    session.delete(edge)
    session.flush()
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "network_edge.deleted",
        "network_edge",
        edge.id,
        actor_id=actor_id,
        details={"code": code},
    )


def _validate_asset_location(
    session: Session,
    model: ModelVersion,
    catalog_item: CatalogItem,
    node_id: uuid.UUID | None,
    edge_id: uuid.UUID | None,
) -> None:
    """Contrôle tenant, type de ressource et emplacement de l'instance."""

    if catalog_item.organization_id != _organization_id(model):
        raise ResourceConflictError(
            "L'équipement de catalogue appartient à une autre organisation."
        )
    if catalog_item.kind in {"fluid", "material"}:
        raise ResourceConflictError(
            "Un produit ou matériau ne peut pas être placé comme équipement du réseau."
        )
    if node_id is not None:
        node = get_network_node(session, node_id)
        if node.model_version_id != model.id:
            raise ResourceConflictError("Le nœud appartient à une autre version de modèle.")
        if catalog_item.kind == "pump" and node.kind != "station":
            raise ResourceConflictError("Une pompe doit être placée sur un nœud de type station.")
        if catalog_item.kind in {"valve", "accessory"}:
            raise ResourceConflictError(
                "Une vanne ou un accessoire hydraulique doit être placé sur un tronçon."
            )
    if edge_id is not None:
        edge = get_network_edge(session, edge_id)
        if edge.model_version_id != model.id:
            raise ResourceConflictError("Le tronçon appartient à une autre version de modèle.")
        if catalog_item.kind == "pump":
            raise ResourceConflictError(
                "Une pompe doit être placée sur une station, pas un tronçon."
            )


def create_asset_instance(
    session: Session,
    model_id: uuid.UUID,
    data: AssetInstanceCreate,
    *,
    actor_id: uuid.UUID | None = None,
) -> AssetInstance:
    model = _get_model(session, model_id, mutable=True)
    catalog_item = session.get(CatalogItem, data.catalog_item_id)
    if catalog_item is None:
        raise ResourceNotFoundError("Équipement de catalogue", data.catalog_item_id)
    _validate_asset_location(session, model, catalog_item, data.node_id, data.edge_id)
    if catalog_item.kind == "pump" and data.role not in {"main", "standby", "auxiliary"}:
        raise ResourceConflictError("Une pompe doit utiliser le rôle main, standby ou auxiliary.")
    asset = AssetInstance(model_version_id=model.id, **data.model_dump())
    session.add(asset)
    _flush(session, f"Le code équipement « {data.code} » existe déjà dans cette version.")
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "asset_instance.created",
        "asset_instance",
        asset.id,
        actor_id=actor_id,
        details={"code": asset.code, "catalog_item_id": str(asset.catalog_item_id)},
    )
    return asset


def list_asset_instances(
    session: Session,
    model_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[AssetInstance], int]:
    _get_model(session, model_id)
    condition = AssetInstance.model_version_id == model_id
    total = session.scalar(select(func.count()).select_from(AssetInstance).where(condition))
    items = session.scalars(
        select(AssetInstance)
        .where(condition)
        .order_by(AssetInstance.code)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), int(total or 0)


def update_asset_instance(
    session: Session,
    asset_id: uuid.UUID,
    data: AssetInstanceUpdate,
    *,
    actor_id: uuid.UUID | None = None,
) -> AssetInstance:
    asset = get_asset_instance(session, asset_id)
    model = _get_model(session, asset.model_version_id, mutable=True)
    changes = data.model_dump(exclude_unset=True)
    catalog_item = session.get(CatalogItem, asset.catalog_item_id)
    if (
        catalog_item is not None
        and catalog_item.kind == "pump"
        and changes.get("role", asset.role) not in {"main", "standby", "auxiliary"}
    ):
        raise ResourceConflictError("Une pompe doit utiliser le rôle main, standby ou auxiliary.")
    for field, value in changes.items():
        setattr(asset, field, value)
    _flush(session, "La modification de l'équipement crée un conflit.")
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "asset_instance.updated",
        "asset_instance",
        asset.id,
        actor_id=actor_id,
        details={"fields": sorted(changes)},
    )
    return asset


def delete_asset_instance(
    session: Session,
    asset_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> None:
    """Retire un équipement d'un brouillon en conservant sa version de catalogue."""

    asset = get_asset_instance(session, asset_id)
    model = _get_model(session, asset.model_version_id, mutable=True)
    code = asset.code
    session.delete(asset)
    session.flush()
    refresh_model_hash(session, model)
    _audit(
        session,
        model,
        "asset_instance.deleted",
        "asset_instance",
        asset.id,
        actor_id=actor_id,
        details={"code": code},
    )


def validate_network(session: Session, model_id: uuid.UUID) -> NetworkValidationReport:
    """Contrôle topologie, profils, stations et références de catalogue."""

    model = _get_model(session, model_id)
    nodes, edges, assets = _model_components(session, model_id)
    errors: list[NetworkValidationIssue] = []
    warnings: list[NetworkValidationIssue] = []

    def error(
        code: str, message: str, object_type: str, object_id: uuid.UUID | None = None
    ) -> None:
        errors.append(
            NetworkValidationIssue(
                code=code,
                message=message,
                object_type=object_type,
                object_id=object_id,
            )
        )

    def warning(
        code: str,
        message: str,
        object_type: str,
        object_id: uuid.UUID | None = None,
    ) -> None:
        warnings.append(
            NetworkValidationIssue(
                code=code,
                message=message,
                object_type=object_type,
                object_id=object_id,
            )
        )

    if len(nodes) < 2:
        error("NET_NODE_COUNT", "Le réseau doit contenir au moins deux nœuds.", "model", model_id)
    if not edges:
        error("NET_EDGE_COUNT", "Le réseau doit contenir au moins un tronçon.", "model", model_id)

    node_by_id = {node.id: node for node in nodes}
    adjacency: dict[uuid.UUID, set[uuid.UUID]] = {node.id: set() for node in nodes}
    for edge in edges:
        adjacency.setdefault(edge.from_node_id, set()).add(edge.to_node_id)
        adjacency.setdefault(edge.to_node_id, set()).add(edge.from_node_id)
        start = node_by_id.get(edge.from_node_id)
        end = node_by_id.get(edge.to_node_id)
        if start is None or end is None:
            error("NET_EDGE_NODE", "Le tronçon référence un nœud absent.", "edge", edge.id)
            continue
        first_value = edge.profile_payload[0].get("elevation_m")
        last_value = edge.profile_payload[-1].get("elevation_m")
        if first_value is None or last_value is None:
            error(
                "NET_PROFILE_ELEVATION",
                "Les extrémités du profil doivent porter une altitude.",
                "edge",
                edge.id,
            )
            continue
        first_elevation = float(first_value)
        last_elevation = float(last_value)
        if abs(first_elevation - start.elevation_m) > 0.1:
            warning(
                "NET_PROFILE_START_ELEVATION",
                "L'altitude initiale du profil diffère de celle du nœud amont.",
                "edge",
                edge.id,
            )
        if abs(last_elevation - end.elevation_m) > 0.1:
            warning(
                "NET_PROFILE_END_ELEVATION",
                "L'altitude finale du profil diffère de celle du nœud aval.",
                "edge",
                edge.id,
            )

    for node in nodes:
        if not adjacency.get(node.id):
            error("NET_NODE_ISOLATED", "Le nœud est isolé.", "node", node.id)

    if nodes:
        visited: set[uuid.UUID] = set()
        pending = deque([nodes[0].id])
        while pending:
            current = pending.popleft()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(adjacency.get(current, set()) - visited)
        if len(visited) != len(nodes):
            error(
                "NET_DISCONNECTED", "Le réseau contient plusieurs composantes.", "model", model_id
            )

    sequences = [edge.sequence for edge in edges]
    if sequences and sorted(sequences) != list(range(1, len(sequences) + 1)):
        error(
            "NET_EDGE_SEQUENCE",
            "Les séquences de tronçons doivent être contiguës à partir de 1.",
            "model",
            model_id,
        )
    ordered_edges = sorted(edges, key=lambda item: item.sequence)
    for previous, following in pairwise(ordered_edges):
        if previous.to_node_id != following.from_node_id:
            error(
                "NET_EDGE_CHAIN",
                "Les tronçons successifs doivent former une chaîne orientée continue.",
                "edge",
                following.id,
            )
    if ordered_edges:
        first_node = node_by_id.get(ordered_edges[0].from_node_id)
        last_node = node_by_id.get(ordered_edges[-1].to_node_id)
        if first_node is not None and first_node.kind not in {"source", "tank"}:
            error(
                "NET_CHAIN_SOURCE",
                "Le premier tronçon doit partir du nœud source ou d'un raccordement de bac.",
                "node",
                first_node.id,
            )
        if last_node is not None and last_node.kind not in {"terminal", "tank"}:
            error(
                "NET_CHAIN_TERMINAL",
                "Le dernier tronçon doit aboutir au nœud terminal ou à un raccordement de bac.",
                "node",
                last_node.id,
            )

    terminal_node_ids: set[uuid.UUID] = set()
    if ordered_edges:
        terminal_node_ids = {ordered_edges[0].from_node_id, ordered_edges[-1].to_node_id}

    kinds = Counter(node.kind for node in nodes)
    boundary_kinds = Counter(node.kind for node in nodes if node.id in terminal_node_ids)
    # Une extrémité vaut source ou terminal selon qu'elle ouvre ou ferme le
    # chaînage : un raccordement de bac y tient le même rôle.
    if kinds["source"] + boundary_kinds["tank"] < 1:
        warning(
            "NET_SOURCE_COUNT",
            "Un pipeline linéaire devrait s'ouvrir sur une source ou un raccordement de bac.",
            "model",
            model_id,
        )
    if kinds["terminal"] + boundary_kinds["tank"] < 1:
        warning(
            "NET_TERMINAL_COUNT",
            "Un pipeline linéaire devrait se fermer sur un terminal ou un raccordement de bac.",
            "model",
            model_id,
        )

    referenced_catalog_ids = {asset.catalog_item_id for asset in assets} | {
        edge.material_catalog_item_id for edge in edges if edge.material_catalog_item_id is not None
    }
    catalog_items = (
        {
            item.id: item
            for item in session.scalars(
                select(CatalogItem).where(CatalogItem.id.in_(referenced_catalog_ids))
            )
        }
        if referenced_catalog_ids
        else {}
    )
    pump_count_by_node = Counter(
        asset.node_id
        for asset in assets
        if catalog_items.get(asset.catalog_item_id)
        and catalog_items[asset.catalog_item_id].kind == "pump"
    )
    for asset in assets:
        item = catalog_items.get(asset.catalog_item_id)
        if item is None:
            error(
                "NET_ASSET_CATALOG",
                "L'équipement référence un catalogue absent.",
                "asset",
                asset.id,
            )
        elif item.status != "approved":
            error(
                "NET_ASSET_UNAPPROVED",
                "L'équipement référence une version de catalogue non approuvée.",
                "asset",
                asset.id,
            )
    for node in nodes:
        if node.kind == "station" and pump_count_by_node[node.id] == 0:
            error("NET_STATION_EMPTY", "La station ne contient aucune pompe.", "node", node.id)
        if node.kind == "tank":
            # Un raccordement de bac n'est compilable qu'aux extrémités du
            # chaînage : ailleurs, le moteur liquide du MVP n'a pas de modèle
            # de piquage intermédiaire.
            if node.id not in terminal_node_ids:
                error(
                    "NET_NODE_UNSUPPORTED",
                    "Un raccordement de bac ne peut être placé qu'à une extrémité du "
                    "chaînage ; utilisez une injection ou un soutirage pour un piquage "
                    "intermédiaire.",
                    "node",
                    node.id,
                )
            elif not _declared_tank_id(node):
                error(
                    "NET_TANK_REFERENCE",
                    "Un raccordement de bac doit désigner le réservoir raccordé par "
                    "payload.tank_id.",
                    "node",
                    node.id,
                )
        if node.kind in {"injection", "offtake"}:
            flow = node.payload.get("flow_m3_s")
            if isinstance(flow, bool) or not isinstance(flow, int | float) or flow <= 0:
                error(
                    "NET_NODE_FLOW",
                    "Une injection ou un soutirage doit définir payload.flow_m3_s strictement "
                    "positif ; le sens est porté par le type du nœud.",
                    "node",
                    node.id,
                )

    for edge in edges:
        if edge.material_catalog_item_id is None:
            continue
        material = catalog_items.get(edge.material_catalog_item_id)
        if material is None:
            error(
                "NET_MATERIAL_CATALOG",
                "Le tronçon référence un matériau de catalogue absent.",
                "edge",
                edge.id,
            )
        elif material.organization_id != _organization_id(model) or material.kind != "material":
            error(
                "NET_MATERIAL_CATALOG",
                "Le matériau doit appartenir à la même organisation et au catalogue matériaux.",
                "edge",
                edge.id,
            )
        elif material.status != "approved":
            error(
                "NET_MATERIAL_UNAPPROVED",
                "Le tronçon référence une version de matériau non approuvée.",
                "edge",
                edge.id,
            )

    raw_fluid_id = model.payload.get("fluid_catalog_item_id")
    try:
        fluid_id = uuid.UUID(str(raw_fluid_id))
    except (TypeError, ValueError):
        error(
            "NET_FLUID_REFERENCE",
            "Le modèle doit référencer un produit approuvé par fluid_catalog_item_id.",
            "model",
            model.id,
        )
    else:
        fluid = session.get(CatalogItem, fluid_id)
        if (
            fluid is None
            or fluid.organization_id != _organization_id(model)
            or fluid.kind != "fluid"
            or fluid.status != "approved"
        ):
            error(
                "NET_FLUID_REFERENCE",
                "Le produit référencé doit être un fluide approuvé de la même organisation.",
                "model",
                model.id,
            )

    return NetworkValidationReport(
        model_version_id=model_id,
        valid=not errors,
        errors=errors,
        warnings=warnings,
        node_count=len(nodes),
        edge_count=len(edges),
        asset_count=len(assets),
    )


def _boundary_tank_payload(session: Session, node: NetworkNode | None) -> dict[str, Any] | None:
    """Sérialise le réservoir raccordé à une extrémité du chaînage."""

    if node is None or node.kind != "tank":
        return None
    tank_id = _declared_tank_id(node)
    if tank_id is None:
        return None
    record = session.get(TankRecord, tank_id)
    if record is None:
        raise InvalidInputError(
            "Le nœud de raccordement désigne un réservoir inexistant.",
            node_id=str(node.id),
            tank_id=str(tank_id),
        )
    from hydro_api.services.operations import tank_domain_payload

    return tank_domain_payload(record)


def _declared_tank_id(node: NetworkNode) -> uuid.UUID | None:
    """Retourne le réservoir désigné par un nœud de raccordement, s'il existe."""

    payload = node.payload if isinstance(node.payload, dict) else {}
    raw = payload.get("tank_id")
    if raw is None:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def canonical_sections_from_normalized(
    session: Session,
    model: ModelVersion,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Assemble fluide, pipeline et équipements depuis les tables normalisées."""

    validation = validate_network(session, model.id)
    if not validation.valid:
        raise InvalidInputError(
            "Le réseau normalisé ne peut pas être assemblé tant qu'il contient des erreurs.",
            model_version_id=str(model.id),
            errors=[issue.model_dump(mode="json") for issue in validation.errors],
        )
    nodes, edges, assets = _model_components(session, model.id)
    ordered_edges = sorted(edges, key=lambda item: item.sequence)
    node_by_id = {node.id: node for node in nodes}
    fluid_id = uuid.UUID(str(model.payload["fluid_catalog_item_id"]))
    fluid = session.get(CatalogItem, fluid_id)
    if fluid is None:
        raise ResourceNotFoundError("Produit de catalogue", fluid_id)

    referenced_catalog_ids = {asset.catalog_item_id for asset in assets} | {
        edge.material_catalog_item_id
        for edge in ordered_edges
        if edge.material_catalog_item_id is not None
    }
    catalog_by_id = (
        {
            item.id: item
            for item in session.scalars(
                select(CatalogItem).where(CatalogItem.id.in_(referenced_catalog_ids))
            )
        }
        if referenced_catalog_ids
        else {}
    )
    assets_by_node: dict[uuid.UUID, list[AssetInstance]] = {}
    assets_by_edge: dict[uuid.UUID, list[AssetInstance]] = {}
    for asset in assets:
        if asset.node_id is not None:
            assets_by_node.setdefault(asset.node_id, []).append(asset)
        if asset.edge_id is not None:
            assets_by_edge.setdefault(asset.edge_id, []).append(asset)

    segments: list[dict[str, Any]] = []
    profile_points: list[dict[str, float | None]] = []
    chainage_by_node: dict[uuid.UUID, float] = {}
    current_chainage = 0.0
    for edge_index, edge in enumerate(ordered_edges):
        chainage_by_node.setdefault(edge.from_node_id, current_chainage)
        local_profile = deepcopy(edge.profile_payload)
        for point_index, point in enumerate(local_profile):
            if edge_index > 0 and point_index == 0:
                continue
            profile_points.append(
                {
                    **point,
                    "chainage_m": current_chainage + float(point["chainage_m"] or 0.0),
                }
            )
        fittings = deepcopy(edge.fittings_payload)
        for fitting in fittings:
            if fitting.get("chainage_m") is not None:
                fitting["chainage_m"] = current_chainage + float(fitting["chainage_m"])
        for asset in sorted(assets_by_edge.get(edge.id, []), key=lambda item: item.code):
            item = catalog_by_id[asset.catalog_item_id]
            if item.kind not in {"valve", "accessory"}:
                raise InvalidInputError(
                    "Seules les vannes et accessoires sont matérialisables sur un tronçon.",
                    asset_id=str(asset.id),
                    catalog_kind=item.kind,
                )
            local_chainage = asset.payload.get("chainage_m")
            fittings.append(
                {
                    "id": asset.code,
                    "kind": str(item.payload.get("kind", item.kind)),
                    "label": asset.name,
                    "k_coefficient": item.payload.get("k_coefficient"),
                    "quantity": asset.payload.get("quantity", 1),
                    "chainage_m": (
                        current_chainage + float(local_chainage)
                        if local_chainage is not None
                        else None
                    ),
                    "status": asset.status,
                    "opening_ratio": asset.payload.get("opening_ratio", 1.0),
                }
            )
        material = (
            catalog_by_id.get(edge.material_catalog_item_id)
            if edge.material_catalog_item_id is not None
            else None
        )
        segments.append(
            {
                "id": edge.code,
                "sequence": edge.sequence,
                "label": edge.name,
                "length_m": edge.length_m,
                "inner_diameter_m": edge.inner_diameter_m,
                "outer_diameter_m": edge.payload.get("outer_diameter_m"),
                "wall_thickness_m": edge.payload.get("wall_thickness_m"),
                "roughness_m": edge.roughness_m,
                "material": material.code if material is not None else None,
                "maop_pa": edge.mawp_pa,
                "minimum_pressure_pa": edge.payload.get("minimum_pressure_pa"),
                "start_chainage_m": current_chainage,
                "status": edge.status,
                "fittings": fittings,
            }
        )
        current_chainage += edge.length_m
        chainage_by_node[edge.to_node_id] = current_chainage

    pump_models: dict[str, dict[str, Any]] = {}
    stations: list[dict[str, Any]] = []
    for node in sorted(nodes, key=lambda item: (chainage_by_node.get(item.id, 0.0), item.code)):
        if node.kind != "station":
            continue
        pump_assets = [
            asset
            for asset in sorted(assets_by_node.get(node.id, []), key=lambda item: item.code)
            if catalog_by_id[asset.catalog_item_id].kind == "pump"
        ]
        pumps: list[dict[str, Any]] = []
        for asset in pump_assets:
            catalog_item = catalog_by_id[asset.catalog_item_id]
            model_payload = deepcopy(catalog_item.payload)
            pump_models[str(model_payload["id"])] = model_payload
            pumps.append(
                {
                    "id": asset.code,
                    "label": asset.name,
                    "model_id": model_payload["id"],
                    "role": "booster" if asset.role == "auxiliary" else asset.role,
                    "status": asset.status,
                    "running": asset.payload.get("running", asset.role != "standby"),
                    "speed_ratio": asset.payload.get("speed_ratio", 1.0),
                }
            )
        arrangement = str(node.payload.get("arrangement", "series"))
        if arrangement not in {"series", "parallel"}:
            raise InvalidInputError(
                "Le montage d'une station doit être series ou parallel.",
                node_id=str(node.id),
                arrangement=arrangement,
            )
        groups = (
            [{"id": f"{node.code}-G1", "label": None, "pumps": pumps}]
            if arrangement == "series"
            else [
                {"id": f"{node.code}-G{index}", "label": None, "pumps": [pump]}
                for index, pump in enumerate(pumps, start=1)
            ]
        )
        stations.append(
            {
                "id": node.code,
                "name": node.name,
                "label": node.payload.get("label"),
                "chainage_m": chainage_by_node[node.id],
                "elevation_m": node.elevation_m,
                "arrangement": arrangement,
                "status": node.status,
                "suction_pressure_min_pa": node.payload.get("suction_pressure_min_pa"),
                "discharge_pressure_max_pa": node.payload.get("discharge_pressure_max_pa"),
                "suction_line_k": node.payload.get("suction_line_k", 0.0),
                "suction_line_diameter_m": node.payload.get("suction_line_diameter_m"),
                "bypass_k": node.payload.get("bypass_k", 0.0),
                "drive_efficiency": node.payload.get("drive_efficiency", 1.0),
                "groups": groups,
            }
        )

    injections: list[dict[str, Any]] = []
    for node in sorted(nodes, key=lambda item: (chainage_by_node.get(item.id, 0.0), item.code)):
        if node.kind not in {"injection", "offtake"}:
            continue
        entered_flow = float(node.payload["flow_m3_s"])
        injections.append(
            {
                "id": node.code,
                "label": node.name,
                "chainage_m": chainage_by_node[node.id],
                "flow_m3_s": entered_flow if node.kind == "injection" else -entered_flow,
                "status": node.status,
            }
        )

    network_payload = {
        "id": str(model.payload.get("network_id", model.id)),
        "name": str(model.payload.get("network_name", model.name)),
        "total_length_m": current_chainage,
        "segments": segments,
        "profile": {"points": profile_points},
        "stations": stations,
        "injections": injections,
        # Les bacs d'extrémité permettent au moteur de convertir un niveau en
        # pression statique : sans eux, un transfert ne peut pas être piloté par
        # les niveaux des réservoirs.
        "origin_tank": _boundary_tank_payload(
            session, node_by_id.get(ordered_edges[0].from_node_id) if ordered_edges else None
        ),
        "destination_tank": _boundary_tank_payload(
            session, node_by_id.get(ordered_edges[-1].to_node_id) if ordered_edges else None
        ),
    }
    equipment_payload = {
        "pump_models": [pump_models[identifier] for identifier in sorted(pump_models)]
    }
    return deepcopy(fluid.payload), network_payload, equipment_payload


__all__ = [
    "canonical_sections_from_normalized",
    "create_asset_instance",
    "create_network_edge",
    "create_network_node",
    "delete_asset_instance",
    "delete_network_edge",
    "delete_network_node",
    "get_asset_instance",
    "get_network_edge",
    "get_network_node",
    "list_asset_instances",
    "list_network_edges",
    "list_network_nodes",
    "refresh_model_hash",
    "update_asset_instance",
    "update_network_edge",
    "update_network_node",
    "validate_network",
]
