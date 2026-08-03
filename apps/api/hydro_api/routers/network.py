"""Routes REST d'édition et de validation du réseau versionné."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from hydro_api.schemas.core import ModelVersionRead, Page
from hydro_api.schemas.network import (
    AssetInstanceCreate,
    AssetInstanceRead,
    AssetInstanceUpdate,
    ModelCloneCreate,
    NetworkEdgeCreate,
    NetworkEdgeRead,
    NetworkEdgeUpdate,
    NetworkNodeCreate,
    NetworkNodeRead,
    NetworkNodeUpdate,
    NetworkValidationReport,
)
from hydro_api.security import ApplicationAccess, DatabaseSession
from hydro_api.services import core, network

router = APIRouter(tags=["réseau versionné"])


@router.post(
    "/models/{model_id}/clone",
    response_model=ModelVersionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cloner une version complète du modèle",
)
def clone_model(
    model_id: uuid.UUID,
    data: ModelCloneCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> ModelVersionRead:
    return ModelVersionRead.model_validate(
        network.clone_model_version(session, model_id, data, actor_id=access.user_id)
    )


@router.get(
    "/models/{model_id}/canonical-sections",
    response_model=dict[str, object],
    summary="Prévisualiser les sections scientifiques assemblées",
)
def preview_canonical_sections(
    model_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> dict[str, object]:
    del access
    model = core.get_model_version(session, model_id)
    fluid, pipeline, equipment = network.canonical_sections_from_normalized(session, model)
    return {
        "fluid": fluid,
        "network": pipeline,
        "equipment": equipment,
        "rules": model.payload.get("rules", {"rule_set_ids": []}),
    }


@router.post(
    "/models/{model_id}/nodes",
    response_model=NetworkNodeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un nœud au modèle",
)
def create_node(
    model_id: uuid.UUID,
    data: NetworkNodeCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> NetworkNodeRead:
    return NetworkNodeRead.model_validate(
        network.create_network_node(session, model_id, data, actor_id=access.user_id)
    )


@router.get(
    "/models/{model_id}/nodes",
    response_model=Page[NetworkNodeRead],
    summary="Lister les nœuds du modèle",
)
def list_nodes(
    model_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[NetworkNodeRead]:
    del access
    items, total = network.list_network_nodes(session, model_id, limit=limit, offset=offset)
    return Page(
        items=[NetworkNodeRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/nodes/{node_id}",
    response_model=NetworkNodeRead,
    summary="Lire un nœud du modèle",
)
def get_node(
    node_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> NetworkNodeRead:
    del access
    return NetworkNodeRead.model_validate(network.get_network_node(session, node_id))


@router.patch(
    "/nodes/{node_id}",
    response_model=NetworkNodeRead,
    summary="Modifier un nœud du brouillon",
)
def update_node(
    node_id: uuid.UUID,
    data: NetworkNodeUpdate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> NetworkNodeRead:
    return NetworkNodeRead.model_validate(
        network.update_network_node(session, node_id, data, actor_id=access.user_id)
    )


@router.post(
    "/models/{model_id}/edges",
    response_model=NetworkEdgeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un tronçon hydraulique",
)
def create_edge(
    model_id: uuid.UUID,
    data: NetworkEdgeCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> NetworkEdgeRead:
    return NetworkEdgeRead.model_validate(
        network.create_network_edge(session, model_id, data, actor_id=access.user_id)
    )


@router.get(
    "/models/{model_id}/edges",
    response_model=Page[NetworkEdgeRead],
    summary="Lister les tronçons du modèle",
)
def list_edges(
    model_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[NetworkEdgeRead]:
    del access
    items, total = network.list_network_edges(session, model_id, limit=limit, offset=offset)
    return Page(
        items=[NetworkEdgeRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/edges/{edge_id}",
    response_model=NetworkEdgeRead,
    summary="Lire un tronçon hydraulique",
)
def get_edge(
    edge_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> NetworkEdgeRead:
    del access
    return NetworkEdgeRead.model_validate(network.get_network_edge(session, edge_id))


@router.patch(
    "/edges/{edge_id}",
    response_model=NetworkEdgeRead,
    summary="Modifier un tronçon du brouillon",
)
def update_edge(
    edge_id: uuid.UUID,
    data: NetworkEdgeUpdate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> NetworkEdgeRead:
    return NetworkEdgeRead.model_validate(
        network.update_network_edge(session, edge_id, data, actor_id=access.user_id)
    )


@router.post(
    "/models/{model_id}/assets",
    response_model=AssetInstanceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Placer un équipement de catalogue",
)
def create_asset(
    model_id: uuid.UUID,
    data: AssetInstanceCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> AssetInstanceRead:
    return AssetInstanceRead.model_validate(
        network.create_asset_instance(session, model_id, data, actor_id=access.user_id)
    )


@router.get(
    "/models/{model_id}/assets",
    response_model=Page[AssetInstanceRead],
    summary="Lister les équipements placés",
)
def list_assets(
    model_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AssetInstanceRead]:
    del access
    items, total = network.list_asset_instances(session, model_id, limit=limit, offset=offset)
    return Page(
        items=[AssetInstanceRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/assets/{asset_id}",
    response_model=AssetInstanceRead,
    summary="Lire un équipement placé",
)
def get_asset(
    asset_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> AssetInstanceRead:
    del access
    return AssetInstanceRead.model_validate(network.get_asset_instance(session, asset_id))


@router.patch(
    "/assets/{asset_id}",
    response_model=AssetInstanceRead,
    summary="Modifier un équipement placé",
)
def update_asset(
    asset_id: uuid.UUID,
    data: AssetInstanceUpdate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> AssetInstanceRead:
    return AssetInstanceRead.model_validate(
        network.update_asset_instance(session, asset_id, data, actor_id=access.user_id)
    )


@router.post(
    "/models/{model_id}/validate",
    response_model=NetworkValidationReport,
    summary="Valider la topologie et les références du modèle",
)
def validate_model_network(
    model_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> NetworkValidationReport:
    del access
    return network.validate_network(session, model_id)


__all__ = ["router"]
