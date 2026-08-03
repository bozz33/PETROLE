"""Services d'import CSV/XLSX avec lignage et validation par ligne."""

from __future__ import annotations

import hashlib
import io
import math
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AuditEvent,
    Dataset,
    DatasetImport,
    DatasetRow,
    Organization,
    Project,
    StoredFile,
)
from hydro_api.schemas.data import DatasetCreate, DatasetMapping
from hydro_api.storage import ObjectStorage
from hydro_shared.hashing import canonical_json, sha256_of_bytes

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "profile": frozenset({"chainage_m", "elevation_m"}),
    "pump_curve": frozenset({"flow_m3_s", "head_m"}),
    "strapping": frozenset({"level_m", "volume_m3"}),
    "measurements": frozenset({"timestamp", "value", "unit", "quality", "source"}),
    "generic": frozenset(),
}
NUMERIC_FIELDS = frozenset(
    {
        "chainage_m",
        "elevation_m",
        "flow_m3_s",
        "head_m",
        "efficiency",
        "power_w",
        "npshr_m",
        "level_m",
        "volume_m3",
        "value",
    }
)
QUALITY_CODES = frozenset({"good", "uncertain", "bad", "substituted", "estimated"})
IMPORT_BATCH_SIZE = 5_000


def _audit(
    session: Session,
    *,
    organization_id: uuid.UUID,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details or {},
            created_at=utc_now(),
        )
    )


def _json_value(value: Any) -> Any:
    """Convertit les scalaires pandas en valeurs JSON sans perte utile."""

    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat() if value.tzinfo else value.isoformat()
    return value


def _read_frame(content: bytes, filename: str, *, max_rows: int) -> pd.DataFrame:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Seuls les fichiers CSV et XLSX sont acceptés.")
    source = io.BytesIO(content)
    try:
        if extension == ".csv":
            frame = pd.read_csv(
                source,
                sep=None,
                engine="python",
                dtype=object,
                keep_default_na=False,
            )
        else:
            frame = pd.read_excel(source, dtype=object, engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"Lecture impossible du fichier {filename} : {exc}") from exc
    if len(frame.index) > max_rows:
        raise ValueError(
            f"Le fichier contient {len(frame.index)} lignes ; la limite est {max_rows}."
        )
    columns = [str(column).strip() for column in frame.columns]
    if not columns or any(not column for column in columns):
        raise ValueError("Chaque colonne doit posséder un nom non vide.")
    if len(columns) != len(set(columns)):
        raise ValueError("Les noms de colonnes doivent être uniques.")
    frame.columns = columns
    return frame


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(column): _json_value(value) for column, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _iter_frame_rows(frame: pd.DataFrame):
    """Parcourt un grand tableau sans créer une seconde liste de toutes ses lignes."""

    columns = [str(column) for column in frame.columns]
    for values in frame.itertuples(index=False, name=None):
        yield {column: _json_value(value) for column, value in zip(columns, values, strict=True)}


def get_file(session: Session, file_id: uuid.UUID) -> StoredFile:
    stored_file = session.get(StoredFile, file_id)
    if stored_file is None:
        raise ResourceNotFoundError("Fichier", file_id)
    return stored_file


def audit_file_download(
    session: Session,
    stored_file: StoredFile,
    *,
    actor_id: uuid.UUID | None,
) -> None:
    """Journalise le téléchargement d'un fichier privé."""

    session.add(
        AuditEvent(
            organization_id=stored_file.organization_id,
            actor_id=actor_id,
            action="file.downloaded",
            object_type="file",
            object_id=stored_file.id,
            details={
                "content_hash": stored_file.content_hash,
                "media_type": stored_file.media_type,
            },
            created_at=utc_now(),
        )
    )
    session.flush()


def store_file(
    session: Session,
    storage: ObjectStorage,
    *,
    organization_id: uuid.UUID,
    filename: str,
    media_type: str,
    content: bytes,
    max_size_bytes: int,
) -> StoredFile:
    """Stocke un fichier privé après contrôle du nom, du format et de la taille."""

    if session.get(Organization, organization_id) is None:
        raise ResourceNotFoundError("Organisation", organization_id)
    safe_name = Path(filename).name.strip()
    if not safe_name:
        raise ValueError("Le nom du fichier est vide.")
    extension = Path(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Seuls les fichiers CSV et XLSX sont acceptés.")
    if not content:
        raise ValueError("Le fichier est vide.")
    if len(content) > max_size_bytes:
        raise ValueError(f"Le fichier dépasse la limite autorisée de {max_size_bytes} octets.")

    file_id = uuid.uuid4()
    object_key = f"imports/{organization_id}/{file_id}/{safe_name}"
    effective_media_type = media_type or (
        "text/csv"
        if extension == ".csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    storage.put_bytes(object_key, content, effective_media_type)
    stored_file = StoredFile(
        id=file_id,
        organization_id=organization_id,
        bucket=storage.bucket,
        object_key=object_key,
        filename=safe_name,
        media_type=effective_media_type,
        size_bytes=len(content),
        content_hash=sha256_of_bytes(content),
        created_at=utc_now(),
    )
    session.add(stored_file)
    try:
        session.flush()
    except Exception:
        storage.delete(object_key)
        raise
    _audit(
        session,
        organization_id=organization_id,
        action="upload",
        object_type="file",
        object_id=stored_file.id,
        details={"filename": safe_name, "content_hash": stored_file.content_hash},
    )
    return stored_file


def get_dataset(session: Session, dataset_id: uuid.UUID) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise ResourceNotFoundError("Jeu de données", dataset_id)
    return dataset


def create_dataset(session: Session, data: DatasetCreate) -> Dataset:
    """Crée un jeu de données en vérifiant l'isolement organisationnel."""

    stored_file = get_file(session, data.file_id)
    if stored_file.organization_id != data.organization_id:
        raise ResourceConflictError(
            "Le fichier et le jeu de données doivent appartenir à la même organisation."
        )
    if data.project_id is not None:
        project = session.get(Project, data.project_id)
        if project is None:
            raise ResourceNotFoundError("Projet", data.project_id)
        if project.organization_id != data.organization_id:
            raise ResourceConflictError(
                "Le projet et le jeu de données doivent appartenir à la même organisation."
            )
    dataset = Dataset(
        organization_id=data.organization_id,
        project_id=data.project_id,
        file_id=data.file_id,
        name=data.name,
        kind=data.kind,
        status="uploaded",
        mapping={},
        preview={},
    )
    session.add(dataset)
    session.flush()
    _audit(
        session,
        organization_id=dataset.organization_id,
        action="create",
        object_type="dataset",
        object_id=dataset.id,
        details={"kind": dataset.kind, "file_id": str(dataset.file_id)},
    )
    return dataset


def preview_dataset(
    session: Session,
    storage: ObjectStorage,
    dataset_id: uuid.UUID,
    *,
    max_rows: int,
    preview_rows: int = 20,
) -> dict[str, Any]:
    """Analyse le fichier et conserve un aperçu borné sans importer de lignes."""

    dataset = get_dataset(session, dataset_id)
    stored_file = get_file(session, dataset.file_id)
    frame = _read_frame(
        storage.get_bytes(stored_file.object_key),
        stored_file.filename,
        max_rows=max_rows,
    )
    rows = _frame_rows(frame.head(preview_rows))
    detected_types = {column: str(frame[column].infer_objects().dtype) for column in frame.columns}
    preview = {
        "dataset_id": str(dataset.id),
        "columns": list(frame.columns),
        "detected_types": detected_types,
        "rows": rows,
        "row_count": len(frame.index),
        "errors": [],
    }
    dataset.preview = preview
    dataset.status = "previewed"
    session.flush()
    return preview


def set_mapping(
    session: Session,
    dataset_id: uuid.UUID,
    mapping: DatasetMapping,
) -> Dataset:
    """Valide puis fige le mapping de colonnes du jeu de données."""

    dataset = get_dataset(session, dataset_id)
    if not dataset.preview:
        raise ResourceConflictError("Un aperçu doit être généré avant le mapping.")
    columns = set(dataset.preview.get("columns", []))
    missing_columns = sorted(set(mapping.fields.values()) - columns)
    if missing_columns:
        raise ValueError("Colonnes absentes du fichier : " + ", ".join(missing_columns) + ".")
    provided = set(mapping.fields) | set(mapping.constants)
    missing_fields = sorted(REQUIRED_FIELDS[dataset.kind] - provided)
    if missing_fields:
        raise ValueError(
            "Champs canoniques obligatoires non mappés : " + ", ".join(missing_fields) + "."
        )
    dataset.mapping = mapping.model_dump(mode="json")
    dataset.status = "mapped"
    session.flush()
    _audit(
        session,
        organization_id=dataset.organization_id,
        action="map",
        object_type="dataset",
        object_id=dataset.id,
        details={"fields": sorted(provided)},
    )
    return dataset


def _normalize_row(
    raw: dict[str, Any],
    mapping: dict[str, Any],
    source_row: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fields: dict[str, str] = mapping.get("fields", {})
    constants: dict[str, Any] = mapping.get("constants", {})
    normalized: dict[str, Any] = {}
    errors: list[dict[str, Any]] = []

    for target, source in fields.items():
        normalized[target] = raw.get(source)
    normalized.update(constants)

    for target in NUMERIC_FIELDS & normalized.keys():
        value = normalized[target]
        if isinstance(value, str):
            value = value.replace(" ", "").replace(",", ".")
        try:
            normalized[target] = float(value)
            if not math.isfinite(normalized[target]):
                raise ValueError
        except (TypeError, ValueError):
            errors.append(
                {
                    "row": source_row,
                    "field": target,
                    "code": "INVALID_NUMBER",
                    "message": f"La valeur du champ {target} doit être numérique.",
                }
            )

    if "timestamp" in normalized:
        try:
            normalized["timestamp"] = pd.to_datetime(
                normalized["timestamp"],
                utc=True,
                errors="raise",
            ).isoformat()
        except (TypeError, ValueError):
            errors.append(
                {
                    "row": source_row,
                    "field": "timestamp",
                    "code": "INVALID_TIMESTAMP",
                    "message": "L'horodatage est invalide.",
                }
            )

    if "quality" in normalized:
        quality = str(normalized["quality"]).strip().lower()
        normalized["quality"] = quality
        if quality not in QUALITY_CODES:
            errors.append(
                {
                    "row": source_row,
                    "field": "quality",
                    "code": "INVALID_QUALITY",
                    "message": "Le code qualité est inconnu.",
                }
            )
    return normalized, errors


def _append_row_monotonicity_errors(
    kind: str,
    normalized: dict[str, Any],
    source_row: int,
    previous_values: dict[str, float],
    errors: list[dict[str, Any]],
) -> None:
    """Contrôle la monotonie en flux, sans conserver le million de lignes en mémoire."""

    fields_by_kind = {
        "profile": ("chainage_m",),
        "pump_curve": ("flow_m3_s",),
        "strapping": ("level_m", "volume_m3"),
    }
    for field in fields_by_kind.get(kind, ()):
        value = normalized.get(field)
        if not isinstance(value, int | float):
            continue
        previous = previous_values.get(field)
        if previous is not None and value <= previous:
            errors.append(
                {
                    "row": source_row,
                    "field": field,
                    "code": "NOT_STRICTLY_INCREASING",
                    "message": f"Le champ {field} doit être strictement croissant.",
                }
            )
        previous_values[field] = float(value)


def _start_import_hash(file_hash: str, mapping: dict[str, Any]) -> hashlib._Hash:
    """Initialise une empreinte identique à ``sha256_of`` sans matérialiser toutes les lignes."""

    digest = hashlib.sha256()
    digest.update(b'{"file_hash":')
    digest.update(canonical_json(file_hash).encode("utf-8"))
    digest.update(b',"mapping":')
    digest.update(canonical_json(mapping).encode("utf-8"))
    digest.update(b',"rows":[')
    return digest


def import_dataset(
    session: Session,
    storage: ObjectStorage,
    dataset_id: uuid.UUID,
    *,
    idempotency_key: str,
    max_rows: int,
) -> DatasetImport:
    """Normalise toutes les lignes et conserve les erreurs sans perte du brut."""

    dataset = get_dataset(session, dataset_id)
    existing = session.scalar(
        select(DatasetImport).where(
            DatasetImport.dataset_id == dataset.id,
            DatasetImport.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing
    if dataset.status not in {"mapped", "imported", "failed"} or not dataset.mapping:
        raise ResourceConflictError("Le mapping doit être validé avant l'import.")

    stored_file = get_file(session, dataset.file_id)
    content = storage.get_bytes(stored_file.object_key)
    frame = _read_frame(content, stored_file.filename, max_rows=max_rows)
    session.execute(delete(DatasetRow).where(DatasetRow.dataset_id == dataset.id))

    digest = _start_import_hash(stored_file.content_hash, dataset.mapping)
    batch: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []
    previous_values: dict[str, float] = {}
    accepted_count = 0
    row_count = 0
    first_hash_row = True
    for source_row, raw in enumerate(_iter_frame_rows(frame), start=2):
        row_count += 1
        normalized, errors = _normalize_row(raw, dataset.mapping, source_row)
        _append_row_monotonicity_errors(
            dataset.kind,
            normalized,
            source_row,
            previous_values,
            errors,
        )
        if not errors:
            accepted_count += 1
        all_errors.extend(errors)
        batch.append(
            {
                "id": uuid.uuid4(),
                "dataset_id": dataset.id,
                "source_row": source_row,
                "raw_payload": raw,
                "normalized_payload": normalized,
                "corrected_payload": None,
                "quality": "bad" if errors else str(normalized.get("quality", "good")),
                "errors": errors,
            }
        )
        if not first_hash_row:
            digest.update(b",")
        digest.update(canonical_json(normalized).encode("utf-8"))
        first_hash_row = False
        if len(batch) >= IMPORT_BATCH_SIZE:
            session.execute(insert(DatasetRow), batch)
            batch.clear()
    if batch:
        session.execute(insert(DatasetRow), batch)
    digest.update(b"]}")

    status = "completed" if not all_errors else "completed_with_errors"
    finished_at = utc_now()
    import_run = DatasetImport(
        dataset_id=dataset.id,
        idempotency_key=idempotency_key,
        status=status,
        row_count=row_count,
        accepted_count=accepted_count,
        rejected_count=row_count - accepted_count,
        content_hash=f"sha256:{digest.hexdigest()}",
        errors=all_errors,
        created_at=finished_at,
        finished_at=finished_at,
    )
    session.add(import_run)
    dataset.status = "imported" if not all_errors else "failed"
    session.flush()
    _audit(
        session,
        organization_id=dataset.organization_id,
        action="import",
        object_type="dataset",
        object_id=dataset.id,
        details={
            "import_id": str(import_run.id),
            "accepted_count": accepted_count,
            "rejected_count": import_run.rejected_count,
        },
    )
    return import_run


def get_import(session: Session, import_id: uuid.UUID) -> DatasetImport:
    import_run = session.get(DatasetImport, import_id)
    if import_run is None:
        raise ResourceNotFoundError("Import", import_id)
    return import_run


def dataset_rows(
    session: Session,
    dataset_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Retourne les lignes avec les trois niveaux de lignage."""

    get_dataset(session, dataset_id)
    total = session.scalar(
        select(func.count()).select_from(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
    )
    records = session.scalars(
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset_id)
        .order_by(DatasetRow.source_row)
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        {
            "id": str(row.id),
            "source_row": row.source_row,
            "raw": row.raw_payload,
            "normalized": row.normalized_payload,
            "corrected": row.corrected_payload,
            "quality": row.quality,
            "errors": row.errors,
        }
        for row in records
    ]
    return items, int(total or 0)


__all__ = [
    "create_dataset",
    "dataset_rows",
    "get_dataset",
    "get_file",
    "get_import",
    "import_dataset",
    "preview_dataset",
    "set_mapping",
    "store_file",
]
