"""Configuration commune de la suite de tests PostgreSQL/PostGIS.

Politique ADR-TEST-DB-001 :

* aucune base embarquée ou en mémoire ;
* une URL dédiée fournie par ``HYDRO_TEST_DATABASE_URL`` ;
* schéma créé exclusivement par Alembic ;
* isolation des tests API par transaction externe SQLAlchemy et SAVEPOINT ;
* base réellement commitée uniquement pour les scénarios multi-connexion
  (worker), avec remise à zéro centralisée hors des fichiers de test.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.orm import Session, sessionmaker

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.session import database_engine as application_database_engine
from hydro_api.database.session import get_session, session_factory
from hydro_shared.testing.postgres import reset_public_tables

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = REPO_ROOT / "tests"
TEST_DATABASE_ENV = "HYDRO_TEST_DATABASE_URL"

if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))


def _validated_test_database_url() -> str:
    """Retourne une URL PostgreSQL explicitement dédiée aux tests.

    Aucun repli vers la base de développement n'est autorisé. Cette garde rend
    impossible une exécution accidentelle de pytest contre la recette ou la
    production.
    """

    raw_url = os.environ.get(TEST_DATABASE_ENV)
    if not raw_url:
        raise RuntimeError(
            f"{TEST_DATABASE_ENV} est obligatoire. Lancez la suite avec "
            "deployment/docker-compose.test.yml."
        )

    url = make_url(raw_url)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("Les tests de persistance exigent PostgreSQL/PostGIS.")
    if not (url.database or "").endswith("_test"):
        raise RuntimeError(
            "La base de test doit avoir un nom se terminant par '_test' ; "
            f"valeur reçue : {url.database!r}."
        )
    return raw_url


def _assert_database_at_alembic_head(engine: Engine, database_url: str) -> None:
    """Vérifie que la base a été préparée par Alembic jusqu'à la tête courante."""

    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    scripts = ScriptDirectory.from_config(config)
    expected_heads = set(scripts.get_heads())
    with engine.connect() as connection:
        current_heads = set(MigrationContext.configure(connection).get_current_heads())

    if current_heads != expected_heads:
        raise RuntimeError(
            "Schéma PostgreSQL de test non migré. "
            f"Révisions présentes={sorted(current_heads)}, "
            f"attendues={sorted(expected_heads)}. Exécutez migrate-test."
        )


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _validated_test_database_url()


@pytest.fixture(scope="session")
def pg_engine(test_database_url: str) -> Generator[Engine, None, None]:
    """Moteur PostgreSQL partagé par la session pytest."""

    engine = application_database_engine(test_database_url)
    _assert_database_at_alembic_head(engine, test_database_url)
    yield engine
    engine.dispose()
    application_database_engine.cache_clear()
    session_factory.cache_clear()


@pytest.fixture
def pg_connection(pg_engine: Engine) -> Generator[Connection, None, None]:
    """Connexion isolée par une transaction externe annulée après le test."""

    connection = pg_engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def pg_session_factory(pg_connection: Connection) -> sessionmaker[Session]:
    """Fabrique de sessions utilisant un SAVEPOINT par cycle applicatif.

    ``join_transaction_mode='create_savepoint'`` est le mécanisme SQLAlchemy 2
    prévu pour tester du code qui appelle ``commit()`` tout en conservant une
    transaction externe annulable à la fin du test.
    """

    return sessionmaker(
        bind=pg_connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest.fixture
def pg_session(pg_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with pg_session_factory() as session:
        yield session
        session.rollback()


@pytest.fixture
def api_client_factory(
    pg_session_factory: sessionmaker[Session],
    test_database_url: str,
    tmp_path: Path,
) -> Callable[..., Iterator[TestClient]]:
    """Construit une application dont chaque requête ouvre sa propre session."""

    @contextmanager
    def factory(**settings_overrides: Any) -> Iterator[TestClient]:
        settings_values: dict[str, Any] = {
            "environment": "test",
            "database_url": test_database_url,
            "background_jobs_enabled": False,
            "object_storage_backend": "filesystem",
            "object_storage_directory": tmp_path / "objects",
        }
        settings_values.update(settings_overrides)
        application = create_application(Settings(**settings_values))

        def session_override() -> Generator[Session, None, None]:
            with pg_session_factory() as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        application.dependency_overrides[get_session] = session_override
        try:
            with TestClient(application) as client:
                yield client
        finally:
            application.dependency_overrides.clear()

    return factory


@pytest.fixture
def api_client(api_client_factory) -> Generator[TestClient, None, None]:
    with api_client_factory() as client:
        yield client


# Alias historique conservé pour les tests de ressources, sans moteur local.
@pytest.fixture
def client(api_client: TestClient) -> TestClient:
    return api_client


# Le nom historique représente désormais une connexion transactionnelle, pas
# un moteur autonome susceptible de supprimer le schéma partagé.
@pytest.fixture
def database_engine(pg_connection: Connection) -> Connection:
    return pg_connection


@pytest.fixture
def committed_database(pg_engine: Engine) -> Generator[None, None, None]:
    """Base nettoyée pour les scénarios nécessitant plusieurs connexions réelles."""

    reset_public_tables(pg_engine)
    try:
        yield
    finally:
        reset_public_tables(pg_engine)


@pytest.fixture
def committed_session_factory(
    committed_database: None,
    pg_engine: Engine,
) -> sessionmaker[Session]:
    del committed_database
    return sessionmaker(
        bind=pg_engine,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture
def committed_api_client_factory(
    committed_database: None,
    test_database_url: str,
    tmp_path: Path,
) -> Callable[..., Iterator[TestClient]]:
    """Client utilisant le cycle de sessions réel pour les tests du worker."""

    del committed_database

    @contextmanager
    def factory(**settings_overrides: Any) -> Iterator[TestClient]:
        settings_values: dict[str, Any] = {
            "environment": "test",
            "database_url": test_database_url,
            "background_jobs_enabled": True,
            "object_storage_backend": "filesystem",
            "object_storage_directory": tmp_path / "objects-committed",
        }
        settings_values.update(settings_overrides)
        application = create_application(Settings(**settings_values))
        with TestClient(application) as client:
            yield client

    return factory


__all__ = [
    "api_client",
    "api_client_factory",
    "client",
    "committed_api_client_factory",
    "committed_database",
    "committed_session_factory",
    "database_engine",
    "pg_connection",
    "pg_engine",
    "pg_session",
    "pg_session_factory",
    "test_database_url",
]
