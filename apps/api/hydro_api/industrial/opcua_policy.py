"""Politique de sécurité du futur client OPC UA PETROLE.

Cette couche est indépendante d'une bibliothèque OPC UA particulière. Elle
fige d'abord les opérations autorisées par le produit afin qu'un futur adapter
ne puisse pas élargir silencieusement le périmètre vers la commande procédé.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class OpcUaOperation(StrEnum):
    """Opérations abstraites auxquelles un adapter OPC UA peut demander accès."""

    BROWSE = "browse"
    READ = "read"
    SUBSCRIBE = "subscribe"
    HISTORY_READ = "history_read"
    WRITE = "write"
    CALL = "call"
    PUBLISH_EVENT = "publish_event"
    ACKNOWLEDGE = "acknowledge"


READ_ONLY_OPERATIONS = frozenset(
    {
        OpcUaOperation.BROWSE,
        OpcUaOperation.READ,
        OpcUaOperation.SUBSCRIBE,
        OpcUaOperation.HISTORY_READ,
    }
)


class OpcUaEndpointPolicy(BaseModel):
    """Configuration minimale d'un endpoint analytique OPC UA.

    `security_mode` est volontairement figé à SignAndEncrypt pour les
    environnements pilote/production. Les identifiants de nœud doivent garder
    l'URI de namespace, pas seulement un index numérique susceptible de changer.
    """

    endpoint_url: str = Field(min_length=1, max_length=500)
    security_mode: str = "SignAndEncrypt"
    security_policy_uri: str = Field(min_length=1, max_length=500)
    application_uri: str = Field(min_length=1, max_length=500)
    certificate_ref: str = Field(min_length=1, max_length=500)
    trust_store_ref: str = Field(min_length=1, max_length=500)
    allowed_namespace_uris: list[str] = Field(min_length=1)
    allowed_operations: list[OpcUaOperation] = Field(
        default_factory=lambda: [
            OpcUaOperation.BROWSE,
            OpcUaOperation.READ,
            OpcUaOperation.SUBSCRIBE,
            OpcUaOperation.HISTORY_READ,
        ]
    )

    @field_validator(
        "endpoint_url",
        "security_policy_uri",
        "application_uri",
        "certificate_ref",
        "trust_store_ref",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Cette valeur ne peut pas être vide.")
        return normalized

    @field_validator("allowed_namespace_uris")
    @classmethod
    def normalize_namespaces(cls, values: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if not normalized:
            raise ValueError("Au moins un URI de namespace OPC UA doit être autorisé.")
        return normalized

    @model_validator(mode="after")
    def enforce_read_only(self) -> "OpcUaEndpointPolicy":
        if self.security_mode != "SignAndEncrypt":
            raise ValueError("Le pilote OPC UA exige security_mode=SignAndEncrypt.")
        forbidden = set(self.allowed_operations) - READ_ONLY_OPERATIONS
        if forbidden:
            names = ", ".join(sorted(operation.value for operation in forbidden))
            raise ValueError(f"Opérations OPC UA interdites par le périmètre PETROLE : {names}.")
        return self


def assert_read_only_operation(operation: OpcUaOperation) -> None:
    """Refuse toute opération qui pourrait modifier ou commander le procédé."""

    if operation not in READ_ONLY_OPERATIONS:
        raise PermissionError(
            f"L'opération OPC UA « {operation.value} » est interdite : PETROLE est read-only."
        )


__all__ = [
    "OpcUaEndpointPolicy",
    "OpcUaOperation",
    "READ_ONLY_OPERATIONS",
    "assert_read_only_operation",
]
