"""Création du moteur SQLAlchemy et portée transactionnelle des requêtes."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from hydro_api.config import Settings
from hydro_shared.json_safety import strict_json_dumps


@lru_cache(maxsize=8)
def database_engine(database_url: str) -> Engine:
    """Crée un moteur par URL et le réutilise dans le processus.

    Le sérialiseur JSON est figé à :func:`strict_json_dumps` (RFC 8259,
    ``allow_nan=False``) : c'est la barrière finale qui empêche une valeur
    non finie (``NaN``, ``Infinity``) issue d'un moteur scientifique de
    corrompre l'écriture en PostgreSQL. Les occurrences non finies doivent
    être neutralisées en amont par :func:`normalize_json_numbers` (cf.
    ``execute_calculation``), mais cette sécurité échoue explicitement
    plutôt que de produire un JSON invalide.
    """

    engine_options: dict[str, Any] = {
        "pool_pre_ping": True,
        "json_serializer": strict_json_dumps,
    }
    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            # TestClient traite les requêtes dans un autre thread. StaticPool
            # garantit que toutes les sessions utilisent la même base mémoire.
            engine_options["poolclass"] = StaticPool
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
