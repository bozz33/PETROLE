"""Création du moteur SQLAlchemy et portée transactionnelle des requêtes."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from hydro_api.config import Settings
from hydro_shared.json_safety import strict_json_dumps


@lru_cache(maxsize=8)
def database_engine(database_url: str) -> Engine:
    """Cree un moteur par URL et le reutilise dans le processus.

    Le serialiseur JSON est fige a :func:`strict_json_dumps` (RFC 8259,
    ``allow_nan=False``) : c'est la barriere finale qui empeche une valeur
    non finie (``NaN``, ``Infinity``) issue d'un moteur scientifique de
    corrompre l'ecriture en PostgreSQL. Les occurrences non finies doivent
    etre neutralisees en amont par :func:`normalize_json_numbers` (cf.
    ``execute_calculation``), mais cette securite echoue explicitement
    plutot que de produire un JSON invalide.
    """

    engine_options: dict[str, Any] = {
        "pool_pre_ping": True,
        "json_serializer": strict_json_dumps,
    }
    return create_engine(database_url, **engine_options)


@lru_cache(maxsize=8)
def session_factory(database_url: str) -> sessionmaker[Session]:
    """Construit la fabrique de sessions liée à une URL."""

    return sessionmaker(
        bind=database_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session(request: Request) -> Generator[Session, None, None]:
    """Fournit une transaction isolée à une requête HTTP."""

    settings: Settings = request.app.state.settings
    factory = session_factory(settings.database_url)
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
