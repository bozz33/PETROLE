"""Configuration typée de l'API.

Toutes les valeurs propres à un environnement proviennent de variables préfixées par
« HYDRO_ ». Aucun secret ni paramètre de déploiement n'est codé dans l'application.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres d'exécution validés au démarrage."""

    application_name: str = "Plateforme Hydrocarbures"
    environment: Literal["development", "test", "staging", "production"] = "development"
    # L'écoute sur toutes les interfaces est requise dans le conteneur. Le port exposé et
    # son filtrage restent sous la responsabilité de la configuration de déploiement.
    host: str = "0.0.0.0"  # nosec B104
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = False
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = "info"
    database_url: str = "postgresql+psycopg://hydro:hydro_dev@localhost:5432/hydro"
    authentication_required: bool = False
    jwt_secret: SecretStr = SecretStr("development-secret-change-before-production")
    access_token_minutes: int = Field(default=15, ge=1, le=1_440)
    refresh_token_days: int = Field(default=7, ge=1, le=90)
    background_jobs_enabled: bool = False
    worker_poll_seconds: float = Field(default=1.0, ge=0.1, le=60.0)
    worker_stale_seconds: int = Field(default=300, ge=30, le=86_400)
    object_storage_backend: Literal["filesystem", "s3"] = "filesystem"
    object_storage_directory: Path = Path(".hydro_storage")
    object_storage_bucket: str = "hydro-reports"
    max_upload_size_bytes: int = Field(default=25_000_000, ge=1_024)
    max_import_rows: int = Field(default=100_000, ge=1, le=1_000_000)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "hydro"
    s3_secret_key: SecretStr = SecretStr("hydro_dev_storage")
    s3_region: str = "us-east-1"
    deployment_mode: Literal["single_org", "multi_org", "saas"] = "multi_org"
    default_organization_id: UUID | None = None
    default_organization_name: str = "PETROLE"
    default_organization_slug: str = "petrole"
    build_git_sha: str = "unknown"
    build_ref: str = "unknown"
    build_date: str = "unknown"
    database_migration_version: str = "7c2d4f8b1a35"

    @model_validator(mode="after")
    def validate_production_security(self) -> Settings:
        """Refuse un démarrage de production avec une sécurité incomplète."""

        if self.environment != "production":
            return self
        if not self.authentication_required:
            raise ValueError("HYDRO_AUTHENTICATION_REQUIRED doit être activé en production.")
        if not self.background_jobs_enabled:
            raise ValueError("HYDRO_BACKGROUND_JOBS_ENABLED doit être activé en production.")
        secret = self.jwt_secret.get_secret_value()
        if len(secret) < 32 or secret.startswith("development-"):
            raise ValueError(
                "HYDRO_JWT_SECRET doit contenir au moins 32 caractères privés en production."
            )
        return self

    model_config = SettingsConfigDict(
        env_prefix="HYDRO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Charge une seule instance de configuration par processus."""

    return Settings()
