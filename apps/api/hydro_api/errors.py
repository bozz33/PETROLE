"""Erreurs applicatives traduites en réponses RFC 7807."""

from __future__ import annotations


class ResourceNotFoundError(Exception):
    """Ressource absente ou inaccessible dans le périmètre demandé."""

    def __init__(self, resource: str, identifier: object) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} {identifier} introuvable.")


class ResourceConflictError(Exception):
    """Mutation impossible à cause de l'état ou d'une unicité."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
