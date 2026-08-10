"""Routes de téléversement et d'import des jeux de données."""

from __future__ import annotations

import uuid
from datetime import datetime
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
from hydro_api.deployment import (
    bind_default_organization,
    is_single_organization,
    require_default_organization_id,
)
from hydro_api.errors import ResourceConflictError
from hydro_api.schemas.core import Page
from hydro_api.schemas.data import (
    DatasetCreate,
    DatasetImportRead,
    DatasetMapping,
    DatasetPreview,
    DatasetRead,
    DatasetRowsRead,
    MeasurementQualitySummary,
    StoredFileRead,
)
from hydro_api.schemas.measurement_comparison import (
    MappingStatus,
    MeasurementComparisonCreate,
    MeasurementComparisonRead,
    MeasurementModelMappingApproval,
    MeasurementModelMappingCreate,
    MeasurementModelMappingRead,
    MeasurementResidualRead,
)
from hydro_api.schemas.time_series import (
    MeasurementTagCreate,
    MeasurementTagRead,
    NormalizedSampleRead,
    OutlierMethod,
    ProcessingVersionRead,
    SampleQuality,
    SeriesAnalysisRead,
    TimeSeriesDatasetImportCreate,
    TimeSeriesImportRead,
)
from hydro_api.services import data_import, measurement_comparison, measurement_quality, time_series
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
    summary="Téléverser un fichier CSV, XLSX ou JSON",
)
async def upload_file(
    organization_id: Annotated[uuid.UUID, Form()],
    file: Annotated[UploadFile, File()],
    request: Request,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    settings: SettingsDependency,
):
    if is_single_organization(request.app.state.settings):
        organization_id = require_default_organization_id(request, session)
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


@router.post(
    "/documents",
    response_model=StoredFileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Téléverser une pièce jointe documentaire",
)
async def upload_document(
    organization_id: Annotated[uuid.UUID, Form()],
    file: Annotated[UploadFile, File()],
    request: Request,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    settings: SettingsDependency,
    project_id: Annotated[uuid.UUID | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
):
    """Stocke un document consulté tel quel : fiche constructeur, plan, rapport.

    Ce flux est distinct de l'import scientifique : le contenu n'est jamais
    interprété comme un tableau de données.
    """

    if is_single_organization(request.app.state.settings):
        organization_id = require_default_organization_id(request, session)
    content = await file.read(settings.max_upload_size_bytes + 1)
    return data_import.store_file(
        session,
        storage,
        organization_id=organization_id,
        filename=file.filename or "",
        media_type=file.content_type or "",
        content=content,
        max_size_bytes=settings.max_upload_size_bytes,
        purpose="document",
        project_id=project_id,
        description=description,
    )


@router.get(
    "/documents",
    response_model=Page[StoredFileRead],
    summary="Lister les pièces jointes documentaires",
)
def list_documents(
    request: Request,
    session: DatabaseSession,
    organization_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if is_single_organization(request.app.state.settings):
        organization_id = require_default_organization_id(request, session)
    items, total = data_import.list_documents(
        session,
        organization_id=organization_id,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


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
def create_dataset(data: DatasetCreate, request: Request, session: DatabaseSession):
    data = bind_default_organization(request, session, data)
    return data_import.create_dataset(session, data)


@router.post(
    "/measurement-tags",
    response_model=MeasurementTagRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un tag de mesure de site",
)
def create_measurement_tag(
    data: MeasurementTagCreate,
    request: Request,
    session: DatabaseSession,
):
    """Crée la racine hiérarchique site → tag des séries Pilote/V1."""

    data = bind_default_organization(request, session, data)
    return time_series.create_measurement_tag(session, data)


@router.get(
    "/measurement-tags",
    response_model=Page[MeasurementTagRead],
    summary="Lister les tags de mesure",
)
def list_measurement_tags(
    organization_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    site_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if is_single_organization(request.app.state.settings):
        organization_id = require_default_organization_id(request, session)
    items, total = time_series.list_measurement_tags(
        session,
        organization_id=organization_id,
        site_id=site_id,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/measurement-tags/{tag_id}",
    response_model=MeasurementTagRead,
    summary="Lire un tag de mesure",
)
def read_measurement_tag(tag_id: uuid.UUID, session: DatabaseSession):
    return time_series.get_measurement_tag(session, tag_id)


@router.post(
    "/measurement-model-mappings",
    response_model=MeasurementModelMappingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une correspondance explicite mesure ↔ résultat calculé",
)
def create_measurement_model_mapping(
    data: MeasurementModelMappingCreate,
    request: Request,
    session: DatabaseSession,
):
    """Crée un brouillon : aucune association ne dérive du nom du tag."""

    data = bind_default_organization(request, session, data)
    return measurement_comparison.create_measurement_mapping(
        session,
        data,
        actor_id=request.state.access_context.user_id,
    )


@router.get(
    "/measurement-model-mappings",
    response_model=Page[MeasurementModelMappingRead],
    summary="Lister les correspondances versionnées mesure ↔ modèle",
)
def list_measurement_model_mappings(
    organization_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    project_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
    status_filter: Annotated[MappingStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if is_single_organization(request.app.state.settings):
        organization_id = require_default_organization_id(request, session)
    items, total = measurement_comparison.list_measurement_mappings(
        session,
        organization_id=organization_id,
        project_id=project_id,
        tag_id=tag_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/measurement-model-mappings/{mapping_id}",
    response_model=MeasurementModelMappingRead,
    summary="Lire une correspondance versionnée",
)
def read_measurement_model_mapping(mapping_id: uuid.UUID, session: DatabaseSession):
    return measurement_comparison.get_measurement_mapping(session, mapping_id)


@router.post(
    "/measurement-model-mappings/{mapping_id}/approve",
    response_model=MeasurementModelMappingRead,
    summary="Approuver et figer une correspondance mesure ↔ modèle",
)
def approve_measurement_model_mapping(
    mapping_id: uuid.UUID,
    data: MeasurementModelMappingApproval,
    request: Request,
    session: DatabaseSession,
):
    return measurement_comparison.approve_measurement_mapping(
        session,
        mapping_id,
        actor_id=request.state.access_context.user_id,
        comment=data.comment,
    )


@router.post(
    "/measurement-comparisons",
    response_model=MeasurementComparisonRead,
    status_code=status.HTTP_201_CREATED,
    summary="Comparer une fenêtre de mesures à un calcul stationnaire",
)
def create_measurement_comparison(
    data: MeasurementComparisonCreate,
    request: Request,
    session: DatabaseSession,
):
    """Archive résidus/KPI et lignage sans modifier les deux sources."""

    data = bind_default_organization(request, session, data)
    comparison = measurement_comparison.create_measurement_comparison(
        session,
        data,
        actor_id=request.state.access_context.user_id,
    )
    return measurement_comparison.comparison_payload(session, comparison)


@router.get(
    "/measurement-comparisons/{measurement_comparison_id}",
    response_model=MeasurementComparisonRead,
    summary="Lire une comparaison stationnaire archivée",
)
def read_measurement_comparison(
    measurement_comparison_id: uuid.UUID,
    session: DatabaseSession,
):
    comparison = measurement_comparison.get_measurement_comparison(
        session,
        measurement_comparison_id,
    )
    return measurement_comparison.comparison_payload(session, comparison)


@router.get(
    "/measurement-comparisons/{measurement_comparison_id}/residuals",
    response_model=Page[MeasurementResidualRead],
    summary="Lister les résidus et leur lignage de mesure",
)
def list_measurement_comparison_residuals(
    measurement_comparison_id: uuid.UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=5_000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = measurement_comparison.list_measurement_residuals(
        session,
        comparison_id=measurement_comparison_id,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/measurement-tags/{tag_id}/samples",
    response_model=Page[NormalizedSampleRead],
    summary="Lire les échantillons SI d'un tag",
)
def list_measurement_tag_samples(
    tag_id: uuid.UUID,
    session: DatabaseSession,
    start_timestamp: datetime | None = None,
    end_timestamp: datetime | None = None,
    processing_version: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    qualities: Annotated[list[SampleQuality] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=5_000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if (
        start_timestamp is not None
        and end_timestamp is not None
        and start_timestamp > end_timestamp
    ):
        raise ResourceConflictError("La borne de début doit précéder la borne de fin.")
    items, total = time_series.list_normalized_samples(
        session,
        tag_id=tag_id,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        processing_version=processing_version,
        qualities=qualities,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/measurement-tags/{tag_id}/processing-versions",
    response_model=list[ProcessingVersionRead],
    summary="Lister les projections temporelles d'un tag",
)
def list_measurement_tag_processing_versions(tag_id: uuid.UUID, session: DatabaseSession):
    """L'interface choisit une version, sans mélanger plusieurs reprocessings."""

    return time_series.list_processing_versions(session, tag_id=tag_id)


@router.get(
    "/measurement-tags/{tag_id}/series-analysis",
    response_model=SeriesAnalysisRead,
    summary="Explorer une série SI et ses diagnostics de qualité",
)
def analyze_measurement_tag_series(
    tag_id: uuid.UUID,
    session: DatabaseSession,
    processing_version: Annotated[str, Query(min_length=1, max_length=80)],
    start_timestamp: datetime | None = None,
    end_timestamp: datetime | None = None,
    qualities: Annotated[list[SampleQuality] | None, Query()] = None,
    reference_interval_seconds: Annotated[float | None, Query(gt=0)] = None,
    gap_factor: Annotated[float, Query(gt=1, le=100)] = 1.5,
    outlier_method: OutlierMethod = "none",
    zscore_threshold: Annotated[float, Query(gt=0, le=100)] = 3.0,
    iqr_multiplier: Annotated[float, Query(gt=0, le=100)] = 1.5,
    limit: Annotated[int, Query(ge=1, le=5_000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Analyse en lecture seule ; les seuils restent visibles dans la réponse."""

    return time_series.analyze_normalized_series(
        session,
        tag_id=tag_id,
        processing_version=processing_version,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        qualities=qualities,
        reference_interval_seconds=reference_interval_seconds,
        gap_factor=gap_factor,
        outlier_method=outlier_method,
        zscore_threshold=zscore_threshold,
        iqr_multiplier=iqr_multiplier,
        limit=limit,
        offset=offset,
    )


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


@router.post(
    "/datasets/{dataset_id}/time-series-imports",
    response_model=TimeSeriesImportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Projeter un dataset de mesures vers une série temporelle",
)
def import_dataset_time_series(
    dataset_id: uuid.UUID,
    data: TimeSeriesDatasetImportCreate,
    idempotency_key: IdempotencyKey,
    session: DatabaseSession,
):
    return time_series.import_dataset_time_series(
        session,
        dataset_id=dataset_id,
        tag_id=data.tag_id,
        idempotency_key=idempotency_key,
        processing_version=data.processing_version,
    )


@router.get(
    "/time-series-imports/{import_id}",
    response_model=TimeSeriesImportRead,
    summary="Lire un import temporel",
)
def read_time_series_import(import_id: uuid.UUID, session: DatabaseSession):
    return time_series.get_time_series_import(session, import_id)


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
    "/datasets/{dataset_id}/quality-summary",
    response_model=MeasurementQualitySummary,
    summary="Synthétiser la qualité d'un jeu de mesures",
)
def read_measurement_quality_summary(
    dataset_id: uuid.UUID,
    session: DatabaseSession,
):
    """Expose les contrôles DQ-007/DQ-008 sans modifier les données importées."""

    return measurement_quality.summarize_measurement_quality(session, dataset_id)


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
