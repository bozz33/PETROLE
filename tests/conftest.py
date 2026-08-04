"""Configuration commune de la suite de tests (ADR-TEST-DB-001).

Le repertoire ``tests`` est ajoute au chemin d'import pour que le module de fabriques
:mod:`tests.factories` soit accessible depuis n'importe quel fichier de test.

Les tests d'integration utilisent **exclusivement PostgreSQL/PostGIS** via le compose
:file:`deployment/docker-compose.test.yml`. SQLite est interdit dans tous les tests
necessitant une base de donnees (cf. check_test_database_policy.py).
"""

from __future__ import annotations

import sys
from collections.abc import Generator
from functools import lru_cache
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.session import get_session

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

#: URL de la base de test PostgreSQL/PostGIS (injectee par le compose de test).
#: La valeur par defaut pointe vers le service ``postgres-test`` du compose.
DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://petrole_test:test-only-password@localhost:5432/petrole_test"
)


def _test_database_url() -> str:
    """Lit la variable d'environnement HYDRO_DATABASE_URL definie par le compose."""

    import os

    return os.environ.get("HYDRO_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@lru_cache(maxsize=1)
def _postgres_engine() -> Engine:
    """Moteur PostgreSQL partage par tous les tests de la session.

    Le cache LRU garantit un seul moteur par session pytest, ce qui est
    suffisant tant que les tests ne s'executent pas en parallele sur le meme
    processus. Pour ``pytest-xdist``, chaque worker aura sa propre instance.
    """

    return create_engine(_test_database_url(), pool_pre_ping=True)


def _truncate_all_tables(session: Session) -> None:
    """Nettoie les tables entre les tests sans detruire le schema.

    TRUNCATE ... CASCADE est plus rapide que DROP/CREATE et preserve les
    sequences et index crees par Alembic.
    """

    session.execute(text("SET session_replication_role = 'replica'"))
    try:
        for row in session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tableowner = current_user"
            )
        ):
            session.execute(text(f'TRUNCATE TABLE "{row[0]}" CASCADE'))
    finally:
        session.execute(text("SET session_replication_role = 'origin'"))
    session.commit()


@pytest.fixture
def pg_session() -> Generator[Session, None, None]:
    """Session PostgreSQL nettoyee avant chaque test.

    Toutes les tables sont tronquees au debut du test (pas a la fin, afin
    qu'un echec laisse l'etat visible pour le diagnostic). La session est
    fermee apres le test.
    """

    engine = _postgres_engine()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        _truncate_all_tables(session)
        yield session
        session.rollback()


@pytest.fixture
def api_client(pg_session: Session) -> Generator[TestClient, None, None]:
    """Client de test FastAPI branche sur PostgreSQL via l'override de session.

    Usage dans les tests :

        def test_exemple(api_client):
            response = api_client.post("/api/v1/organizations", json={...})
            assert response.status_code == 201
    """

    application = create_application(
        Settings(
            environment="test",
            database_url=_test_database_url(),
            background_jobs_enabled=False,
        )
    )

    def session_override():
        """Branche la session PostgreSQL de test a la place du moteur par defaut."""

        yield pg_session

    application.dependency_overrides[get_session] = session_override
    with TestClient(application) as client:
        yield client

    # Nettoyer les overrides pour eviter les fuites entre tests.
    application.dependency_overrides.clear()


__all__ = ["api_client", "pg_session"]
