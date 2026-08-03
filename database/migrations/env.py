"""Environnement Alembic lié aux modèles SQLAlchemy de l'API."""

from __future__ import annotations

import importlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from hydro_api.config import get_settings
from hydro_api.database.base import Base

importlib.import_module("hydro_api.models")
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata
MANAGED_TABLE_NAMES = frozenset(target_metadata.tables)


def include_name(name, type_, parent_names):
    """Évite de réfléchir les tables gérées par les extensions PostgreSQL."""

    del parent_names
    if type_ == "table":
        return name in MANAGED_TABLE_NAMES
    return True


def include_object(obj, name, type_, reflected, compare_to):
    """Ignore les objets externes, notamment les tables internes de PostGIS."""

    del obj, name, type_
    return not (reflected and compare_to is None)


def run_migrations_offline() -> None:
    """Génère le SQL sans ouvrir de connexion."""

    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Applique les migrations dans une transaction."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_name=include_name,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
