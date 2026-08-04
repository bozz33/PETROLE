"""Outils d'infrastructure pour les tests d'intégration PostgreSQL.

Ce module centralise les opérations PostgreSQL qui ne doivent pas apparaître dans
les fichiers de test. Les tests ordinaires utilisent une transaction externe
SQLAlchemy et des SAVEPOINT ; les tests multi-connexion (worker) utilisent une
base dédiée remise à zéro par :func:`reset_public_tables`.
"""

from __future__ import annotations

from sqlalchemy import Engine, inspect, text

_ALEMBIC_TABLE = "alembic_version"


def reset_public_tables(engine: Engine) -> None:
    """Vide toutes les tables applicatives en conservant le schéma Alembic.

    L'identification des tables passe par l'inspecteur SQLAlchemy. Les noms sont
    ensuite protégés par le préparateur d'identifiants du dialecte avant
    l'instruction PostgreSQL ``TRUNCATE ... RESTART IDENTITY CASCADE``.

    Cette fonction est réservée à une base dont le nom se termine par ``_test``.
    """

    database_name = engine.url.database or ""
    if not database_name.endswith("_test"):
        raise RuntimeError(
            "Refus de nettoyer une base non dédiée aux tests : "
            f"{database_name!r}. Le nom doit se terminer par '_test'."
        )

    table_names = [
        name for name in inspect(engine).get_table_names(schema="public") if name != _ALEMBIC_TABLE
    ]
    if not table_names:
        return

    preparer = engine.dialect.identifier_preparer
    qualified = ", ".join(
        f"{preparer.quote_schema('public')}.{preparer.quote(name)}" for name in sorted(table_names)
    )
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {qualified} RESTART IDENTITY CASCADE"))


__all__ = ["reset_public_tables"]
