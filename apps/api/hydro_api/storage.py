"""Stockage privé des rapports et fichiers générés."""

from __future__ import annotations

import socket
from functools import lru_cache
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import Annotated, Any, Protocol
from urllib.parse import urlparse

from fastapi import Depends, Request

from hydro_api.config import Settings


class ObjectStorage(Protocol):
    """Contrat minimal du stockage objet utilisé par l'API."""

    bucket: str

    def put_bytes(self, key: str, content: bytes, media_type: str) -> None:
        """Écrit un objet complet sous une clé privée."""

    def get_bytes(self, key: str) -> bytes:
        """Lit intégralement un objet privé."""

    def delete(self, key: str) -> None:
        """Supprime un objet après échec transactionnel."""

    def check(self) -> None:
        """Vérifie que le stockage est joignable et prêt."""


def _validated_key(key: str) -> PurePosixPath:
    path = PurePosixPath(key)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(
            "La clé de stockage doit être relative et ne contenir aucun segment parent."
        )
    return path


class FilesystemObjectStorage:
    """Stockage local borné à un répertoire, utilisé en test et en poste autonome."""

    def __init__(self, root: Path) -> None:
        self.bucket = "filesystem"
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        relative = _validated_key(key)
        target = self.root.joinpath(*relative.parts).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError("La clé de stockage sort du répertoire autorisé.")
        return target

    def put_bytes(self, key: str, content: bytes, media_type: str) -> None:
        del media_type
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)

    def get_bytes(self, key: str) -> bytes:
        target = self._path(key)
        if not target.is_file():
            raise FileNotFoundError(f"Objet de stockage introuvable : {key}.")
        return target.read_bytes()

    def delete(self, key: str) -> None:
        target = self._path(key)
        if target.is_file():
            target.unlink()

    def check(self) -> None:
        """Vérifie que le répertoire existe réellement et reste inscriptible."""

        self.root.mkdir(parents=True, exist_ok=True)
        if not self.root.is_dir():
            raise OSError("Le répertoire de stockage local est indisponible.")
        with NamedTemporaryFile(
            mode="wb",
            prefix=".hydro-readiness-",
            dir=self.root,
            delete=True,
        ) as probe:
            probe.write(b"ready")
            probe.flush()


class S3ObjectStorage:
    """Stockage compatible S3, notamment MinIO en déploiement local."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str,
        bucket: str,
    ) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.region = region
        endpoint = urlparse(endpoint_url)
        if not endpoint.hostname:
            raise ValueError("Le point d'accès S3 ne contient aucun nom d'hôte valide.")
        self.endpoint_ip = socket.gethostbyname(endpoint.hostname)
        self.endpoint_port = endpoint.port or (443 if endpoint.scheme == "https" else 80)
        self.client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            # Une dépendance indisponible doit produire un diagnostic rapide. Les délais par
            # défaut de botocore peuvent bloquer la disponibilité HTTP pendant plusieurs
            # dizaines de secondes, ce qui masque la cause et sature les workers web.
            config=Config(
                connect_timeout=0.25,
                read_timeout=0.5,
                retries={"total_max_attempts": 1, "mode": "standard"},
            ),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except self.client.exceptions.ClientError:
            pass
        parameters: dict[str, Any] = {"Bucket": self.bucket}
        if self.region != "us-east-1":
            parameters["CreateBucketConfiguration"] = {
                "LocationConstraint": self.region,
            }
        self.client.create_bucket(**parameters)

    def put_bytes(self, key: str, content: bytes, media_type: str) -> None:
        normalized = _validated_key(key).as_posix()
        self.client.put_object(
            Bucket=self.bucket,
            Key=normalized,
            Body=content,
            ContentType=media_type,
        )

    def get_bytes(self, key: str) -> bytes:
        normalized = _validated_key(key).as_posix()
        response = self.client.get_object(Bucket=self.bucket, Key=normalized)
        body = response["Body"]
        try:
            return bytes(body.read())
        finally:
            body.close()

    def delete(self, key: str) -> None:
        normalized = _validated_key(key).as_posix()
        self.client.delete_object(Bucket=self.bucket, Key=normalized)

    def check(self) -> None:
        # La pile HTTP peut attendre le délai TCP du système lorsque le conteneur cible
        # disparaît. Cette sonde bornée maintient le point de disponibilité réactif.
        with socket.create_connection(
            (self.endpoint_ip, self.endpoint_port),
            timeout=0.5,
        ):
            pass
        self.client.head_bucket(Bucket=self.bucket)


@lru_cache(maxsize=16)
def _storage_for_values(
    backend: str,
    directory: str,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    region: str,
    bucket: str,
) -> ObjectStorage:
    if backend == "filesystem":
        return FilesystemObjectStorage(Path(directory))
    if backend == "s3":
        return S3ObjectStorage(
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            bucket=bucket,
        )
    raise ValueError(f"Backend de stockage inconnu : {backend}.")


def object_storage_for(settings: Settings) -> ObjectStorage:
    """Construit le backend déclaré dans la configuration active."""

    return _storage_for_values(
        settings.object_storage_backend,
        str(settings.object_storage_directory),
        settings.s3_endpoint_url,
        settings.s3_access_key,
        settings.s3_secret_key.get_secret_value(),
        settings.s3_region,
        settings.object_storage_bucket,
    )


def get_object_storage(request: Request) -> ObjectStorage:
    """Dépendance FastAPI liée aux paramètres de l'application courante."""

    settings: Settings = request.app.state.settings
    return object_storage_for(settings)


ObjectStorageDependency = Annotated[ObjectStorage, Depends(get_object_storage)]

__all__ = [
    "FilesystemObjectStorage",
    "ObjectStorage",
    "ObjectStorageDependency",
    "S3ObjectStorage",
    "get_object_storage",
    "object_storage_for",
]
