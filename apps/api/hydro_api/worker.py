"""Processus PostgreSQL des calculs scientifiques différés."""

from __future__ import annotations

import logging
import signal
import uuid
from datetime import timedelta
from threading import Event

from sqlalchemy import select

from hydro_api.config import Settings, get_settings
from hydro_api.database.base import utc_now
from hydro_api.database.session import session_factory
from hydro_api.models import BackgroundJob, CalculationRun
from hydro_api.services import core
from hydro_shared.observability import bound_context, configure_logging, get_logger

_LOGGER = get_logger("calcul_differe")


def recover_stale_jobs(settings: Settings) -> int:
    """Replace en file les tâches abandonnées par un processus interrompu."""

    threshold = utc_now() - timedelta(seconds=settings.worker_stale_seconds)
    recovered = 0
    factory = session_factory(settings.database_url)
    with factory() as session:
        jobs = session.scalars(
            select(BackgroundJob).where(
                BackgroundJob.status == "running",
                BackgroundJob.locked_at < threshold,
            )
        ).all()
        for job in jobs:
            if job.attempts >= job.maximum_attempts:
                job.status = "failed"
                job.finished_at = utc_now()
            else:
                job.status = "queued"
                job.available_at = utc_now()
            job.locked_at = None
            recovered += 1
        session.commit()
    return recovered


def _claim_one(settings: Settings) -> uuid.UUID | None:
    factory = session_factory(settings.database_url)
    with factory() as session:
        job = session.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.status == "queued",
                BackgroundJob.available_at <= utc_now(),
            )
            .order_by(BackgroundJob.available_at, BackgroundJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = "running"
        job.attempts += 1
        job.locked_at = utc_now()
        job.last_error = None
        job_id = job.id
        session.commit()
        return job_id


def _mark_failure(settings: Settings, job_id: uuid.UUID, error: Exception) -> None:
    factory = session_factory(settings.database_url)
    with factory() as session:
        job = session.get(BackgroundJob, job_id)
        if job is None:
            return
        if job.status == "cancelled":
            return
        calculation = session.get(CalculationRun, job.resource_id)
        job.last_error = (f"{type(error).__name__}: échec de l'exécution scientifique.")[:2_000]
        job.locked_at = None
        if job.attempts < job.maximum_attempts:
            job.status = "queued"
            job.available_at = utc_now() + timedelta(seconds=min(2**job.attempts, 60))
            if calculation is not None:
                calculation.status = "SIM_QUEUED"
                calculation.started_at = None
        else:
            job.status = "failed"
            job.finished_at = utc_now()
            if calculation is not None:
                calculation.status = "SIM_NOT_CONVERGED"
                calculation.finished_at = utc_now()
                calculation.diagnostics = {
                    "worker_error": "Le processus de calcul n'a pas pu terminer l'exécution après trois tentatives.",
                    "exception_type": type(error).__name__,
                }
        session.commit()


def process_one(settings: Settings) -> bool:
    """Réclame puis traite une tâche ; retourne faux lorsque la file est vide."""

    job_id = _claim_one(settings)
    if job_id is None:
        return False
    factory = session_factory(settings.database_url)
    try:
        with factory() as session:
            job = session.get(BackgroundJob, job_id)
            if job is None:
                return True
            if job.kind != "calculation":
                raise ValueError(f"Type de tâche inconnu : {job.kind}.")
            calculation = session.scalar(
                select(CalculationRun)
                .where(CalculationRun.id == job.resource_id)
                .with_for_update()
            )
            if calculation is None:
                raise ValueError("Le calcul associé à la tâche est introuvable.")
            if calculation.status == "SIM_CANCELLED" or job.status == "cancelled":
                session.commit()
                return True
            calculation.status = "SIM_RUNNING"
            calculation.started_at = calculation.started_at or utc_now()
            session.commit()
            organization_id = (
                str(calculation.scenario.model_version.project.organization_id)
            )
            correlation_id = str(job.payload.get("correlation_id") or job.id)
            with bound_context(
                correlation_id=correlation_id,
                calculation_id=str(job.resource_id),
                organization_id=organization_id,
            ):
                try:
                    _LOGGER.info(
                        "calcul_differe_demarre",
                        tentative=job.attempts,
                    )
                    core.execute_calculation(session, job.resource_id)
                    session.refresh(job)
                    if job.status != "cancelled":
                        job.status = "completed"
                        job.locked_at = None
                        job.finished_at = utc_now()
                    session.commit()
                    _LOGGER.info("calcul_differe_termine")
                except Exception as error:
                    _LOGGER.error(
                        "calcul_differe_echoue",
                        type_exception=type(error).__name__,
                    )
                    raise
    except Exception as error:
        _mark_failure(settings, job_id, error)
    return True


def main() -> None:
    """Traite la file jusqu'au signal d'arrêt du conteneur."""

    settings = get_settings()
    log_level = (
        logging.DEBUG
        if settings.log_level in {"debug", "trace"}
        else getattr(logging, settings.log_level.upper())
    )
    configure_logging(
        json_output=settings.environment != "development",
        level=log_level,
    )
    stop_event = Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    recovered = recover_stale_jobs(settings)
    _LOGGER.info("file_calcul_demarre", taches_recuperees=recovered)
    while not stop_event.is_set():
        processed = process_one(settings)
        if not processed:
            stop_event.wait(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
