"""Qualification PostgreSQL de concurrence et reprise du worker.

Huit prétendants tentent de réserver simultanément une tâche unique. Le verrou
``FOR UPDATE SKIP LOCKED`` doit produire un seul gagnant. Le test vieillit ensuite le bail,
simule l'arrêt brutal du processus et vérifie remise en file puis nouvelle réservation.
"""

from __future__ import annotations

import argparse
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path

from hydro_api.config import Settings
from hydro_api.database.base import utc_now
from hydro_api.database.session import session_factory
from hydro_api.models import BackgroundJob
from hydro_api.worker import _claim_one, recover_stale_jobs


@dataclass(frozen=True, slots=True)
class WorkerConcurrencyResult:
    contenders: int
    successful_claims: int
    stale_jobs_recovered: int
    claimed_after_recovery: bool
    passed: bool


def run(database_url: str, contenders: int = 8) -> WorkerConcurrencyResult:
    settings = Settings(
        environment="test",
        database_url=database_url,
        background_jobs_enabled=True,
        worker_stale_seconds=30,
    )
    factory = session_factory(database_url)
    with factory() as session:
        job = BackgroundJob(
            kind="calculation",
            resource_id=uuid.uuid4(),
            status="queued",
            payload={"qualification": True},
            attempts=0,
            maximum_attempts=3,
            available_at=utc_now(),
        )
        session.add(job)
        session.commit()
        job_id = job.id

    with ThreadPoolExecutor(max_workers=contenders) as executor:
        claims = list(executor.map(lambda _: _claim_one(settings), range(contenders)))
    successful_claims = sum(claim == job_id for claim in claims)

    with factory() as session:
        job = session.get(BackgroundJob, job_id)
        assert job is not None
        job.locked_at = utc_now() - timedelta(seconds=60)
        session.commit()
    recovered = recover_stale_jobs(settings)
    claimed_after_recovery = _claim_one(settings) == job_id
    passed = successful_claims == 1 and recovered == 1 and claimed_after_recovery
    return WorkerConcurrencyResult(
        contenders=contenders,
        successful_claims=successful_claims,
        stale_jobs_recovered=recovered,
        claimed_after_recovery=claimed_after_recovery,
        passed=passed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Qualification de concurrence du worker.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.database_url)
    rendered = json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
