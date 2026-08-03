"""Routes de téléversement et d'import des jeux de données."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from hydro_api.config import Settings
from hydro_api.database.session import get_session
from hydro_api.schemas.data import (
    DatasetCreate,
    DatasetImportRead,
    DatasetMapping,
    DatasetPreview,
    DatasetRead,
    DatasetRowsRead,
    StoredFileRead,
)
from hydro_api.services import data_import
from hydro_api.storage import ObjectStorageDependency

router = APIRouter(tags=["Données"])
DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
        description="Clé stable de l'exécution d'import.",
    ),
]


def _settings(request: Request) -> Settings:
    """Expose les limites validées de l'environnement actif."""

    return request.app.state.settings


SettingsDependency = Annotated[Settings, Depends(_settings)]


@router.post(
    "/files",
    response_model=StoredFileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Téléverser un fichier CSV ou XLSX",
)
async def upload_file(
    organization_id: Annotated[uuid.UUID, Form()],
    file: Annotated[UploadFile, File()],
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    settings: SettingsDependency,
):
    content = await file.read(settings.max_upload_size_bytes + 1)
    return data_import.store_file(
        session,
        storage,
        organization_id=organization_id,
        filename=file.filename or "",
        media_type=file.content_type or "application/octet-stream",
        content=content,
        max_size_bytes=settings.max_upload_size_bytes,
    )


@router.get(
    "/files/{file_id}",
    response_model=StoredFileRead,
    summary="Lire les métadonnées d'un fichier",
)
def read_file(file_id: uuid.UUID, session: DatabaseSession):
    return data_import.get_file(session, file_id)


@router.get(
    "/files/{file_id}/download",
    summary="Télécharger un fichier privé",
)
def download_file(
    file_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
):
    stored_file = data_import.get_file(session, file_id)
    content = storage.get_bytes(stored_file.object_key)
    data_import.audit_file_download(
        session,
        stored_file,
        actor_id=request.state.access_context.user_id,
    )
    safe_name = stored_file.filename.replace('"', "")
    return Response(
        content=content,
        media_type=stored_file.media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.post(
    "/datasets",
    response_model=DatasetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un jeu de données",
)
def create_dataset(data: DatasetCreate, session: DatabaseSession):
    return data_import.create_dataset(session, data)


@router.get(
    "/datasets/{dataset_id}",
    response_model=DatasetRead,
    summary="Lire un jeu de données",
)
def read_dataset(dataset_id: uuid.UUID, session: DatabaseSession):
    return data_import.get_dataset(session, dataset_id)


@router.post(
    "/datasets/{dataset_id}/preview",
    response_model=DatasetPreview,
    summary="Prévisualiser et analyser un fichier",
)
def preview_dataset(
    dataset_id: uuid.UUID,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    settings: SettingsDependency,
):
    return data_import.preview_dataset(
        session,
        storage,
        dataset_id,
        max_rows=settings.max_import_rows,
    )


@router.post(
    "/datasets/{dataset_id}/mappings",
    response_model=DatasetRead,
    summary="Valider le mapping des colonnes",
)
def map_dataset(
    dataset_id: uuid.UUID,
    mapping: DatasetMapping,
    session: DatabaseSession,
):
    return data_import.set_mapping(session, dataset_id, mapping)


@router.post(
    "/datasets/{dataset_id}/imports",
    response_model=DatasetImportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Importer et normaliser les lignes",
)
def run_import(
    dataset_id: uuid.UUID,
    idempotency_key: IdempotencyKey,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    settings: SettingsDependency,
):
    return data_import.import_dataset(
        session,
        storage,
        dataset_id,
        idempotency_key=idempotency_key,
        max_rows=settings.max_import_rows,
    )


@router.get(
    "/datasets/{dataset_id}/rows",
    response_model=DatasetRowsRead,
    summary="Lire les lignes et leur lignage",
)
def read_dataset_rows(
    dataset_id: uuid.UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=1_000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = data_import.dataset_rows(
        session,
        dataset_id,
        limit=limit,
        offset=offset,
    )
    return DatasetRowsRead(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/imports/{import_id}",
    response_model=DatasetImportRead,
    summary="Lire le bilan d'un import",
)
def read_import(import_id: uuid.UUID, session: DatabaseSession):
    return data_import.get_import(session, import_id)


@router.get(
    "/imports/{import_id}/errors",
    summary="Lire les erreurs détaillées d'un import",
)
def read_import_errors(import_id: uuid.UUID, session: DatabaseSession):
    import_run = data_import.get_import(session, import_id)
    return {
        "import_id": str(import_run.id),
        "count": len(import_run.errors),
        "items": import_run.errors,
    }


@router.post(
    "/imports/{import_id}/retry",
    response_model=DatasetImportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Relancer un import corrigé",
)
def retry_import(
    import_id: uuid.UUID,
    idempotency_key: IdempotencyKey,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    settings: SettingsDependency,
):
    previous = data_import.get_import(session, import_id)
    return data_import.import_dataset(
        session,
        storage,
        previous.dataset_id,
        idempotency_key=idempotency_key,
        max_rows=settings.max_import_rows,
    )


__all__ = ["router"]
