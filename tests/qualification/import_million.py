"""Benchmark d'import d'un million de mesures dans PostgreSQL.

La campagne utilise une base jetable dédiée. Elle vérifie lecture CSV, stockage privé,
prévisualisation, mapping, import par lots, comptage SQL, empreinte et reprise idempotente.
La création et la suppression de la base restent pilotées par le script PowerShell de recette ;
ce programme ne touche qu'aux données de la base reçue par ``HYDRO_DATABASE_URL``.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import resource
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from hydro_api.models import DatasetRow, Organization
from hydro_api.schemas.data import DatasetCreate, DatasetMapping
from hydro_api.services.data_import import (
    create_dataset,
    import_dataset,
    preview_dataset,
    set_mapping,
    store_file,
)
from hydro_api.storage import FilesystemObjectStorage

ROW_COUNT = 1_000_000


@dataclass(frozen=True, slots=True)
class ImportBenchmarkResult:
    """Preuve mesurée du benchmark de données D18 § 8."""

    started_at: str
    row_count: int
    accepted_count: int
    rejected_count: int
    csv_size_bytes: int
    preview_duration_s: float
    import_duration_s: float
    idempotent_replay_duration_s: float
    maximum_resident_memory_mib: float
    persisted_row_count: int
    content_hash: str
    passed: bool


def _csv_content(row_count: int) -> bytes:
    """Génère un fichier compact et déterministe sans dépendance supplémentaire."""

    output = io.StringIO()
    output.write("index,value\n")
    output.writelines(f"{index},{index}\n" for index in range(row_count))
    return output.getvalue().encode("utf-8")


def run_benchmark(database_url: str, storage_directory: Path) -> ImportBenchmarkResult:
    started_at = datetime.now(UTC).isoformat()
    engine = create_engine(database_url, pool_pre_ping=True)
    storage = FilesystemObjectStorage(storage_directory)
    content = _csv_content(ROW_COUNT)
    with Session(engine, expire_on_commit=False) as session:
        organization = Organization(
            name="Qualification import million",
            slug="qualification-import-million",
            default_locale="fr",
            default_unit_system="SI",
        )
        session.add(organization)
        session.flush()
        stored_file = store_file(
            session,
            storage,
            organization_id=organization.id,
            filename="million_mesures.csv",
            media_type="text/csv",
            content=content,
            max_size_bytes=25_000_000,
        )
        dataset = create_dataset(
            session,
            DatasetCreate(
                organization_id=organization.id,
                file_id=stored_file.id,
                name="Million de mesures",
                kind="generic",
            ),
        )

        preview_started = time.perf_counter()
        preview = preview_dataset(
            session,
            storage,
            dataset.id,
            max_rows=ROW_COUNT,
        )
        preview_duration_s = time.perf_counter() - preview_started
        assert preview["row_count"] == ROW_COUNT
        set_mapping(session, dataset.id, DatasetMapping(fields={"value": "value"}))

        import_started = time.perf_counter()
        imported = import_dataset(
            session,
            storage,
            dataset.id,
            idempotency_key="million-v1",
            max_rows=ROW_COUNT,
        )
        import_duration_s = time.perf_counter() - import_started
        session.commit()

        replay_started = time.perf_counter()
        replayed = import_dataset(
            session,
            storage,
            dataset.id,
            idempotency_key="million-v1",
            max_rows=ROW_COUNT,
        )
        replay_duration_s = time.perf_counter() - replay_started
        persisted_count = int(
            session.scalar(
                select(func.count())
                .select_from(DatasetRow)
                .where(DatasetRow.dataset_id == dataset.id)
            )
            or 0
        )

        passed = (
            imported.status == "completed"
            and imported.accepted_count == ROW_COUNT
            and imported.rejected_count == 0
            and persisted_count == ROW_COUNT
            and replayed.id == imported.id
        )
        result = ImportBenchmarkResult(
            started_at=started_at,
            row_count=imported.row_count,
            accepted_count=imported.accepted_count,
            rejected_count=imported.rejected_count,
            csv_size_bytes=len(content),
            preview_duration_s=preview_duration_s,
            import_duration_s=import_duration_s,
            idempotent_replay_duration_s=replay_duration_s,
            maximum_resident_memory_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            persisted_row_count=persisted_count,
            content_hash=imported.content_hash,
            passed=passed,
        )
    engine.dispose()
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark d'import d'un million de lignes.")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--storage-directory",
        type=Path,
        default=Path("var/qa/import-million-storage"),
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    database_url = os.environ.get("HYDRO_DATABASE_URL")
    if not database_url:
        raise SystemExit("HYDRO_DATABASE_URL doit désigner la base jetable de qualification.")
    result = run_benchmark(database_url, args.storage_directory)
    rendered = json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
