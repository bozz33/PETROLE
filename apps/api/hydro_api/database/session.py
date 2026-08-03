"""Création du moteur SQLAlchemy et portée transactionnelle des requêtes."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from hydro_api.config import Settings, get_settings


@lru_cache(maxsize=8)
def database_engine(database_url: str) -> Engine:
    """Crée un moteur par URL et le réutilise dans le processus."""

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


@lru_cache(maxsize=8)
def session_factory(database_url: str) -> sessionmaker[Session]:
    """Construit la fabrique de sessions liée à une URL."""

    return sessionmaker(
        bind=database_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
    )


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_session(
    settings: SettingsDependency,
) -> Generator[Session, None, None]:
    """Fournit une transaction isolée à une requête HTTP."""

    factory = session_factory(settings.database_url)
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
