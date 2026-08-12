"""Configuration déclarative d'un connecteur OPC UA PETROLE read-only.

D15 impose SignAndEncrypt, certificats, trust-list, mapping stable namespace
URI + NodeId et secrets externalisés. Ce module valide le contrat sans choisir
ni SDK OPC UA, ni credential, ni certificat concret à la place de l'opérateur.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class OpcUaNodeMapping:
    """Association stable entre un tag PETROLE et un nœud OPC UA source."""

    tag_ref: str
    namespace_uri: str
    node_id: str
    source_ref: str

    def __post_init__(self) -> None:
        values = (self.tag_ref, self.namespace_uri, self.node_id, self.source_ref)
        if any(not value.strip() for value in values):
            raise ValueError("Tag, namespace URI, NodeId et provenance sont obligatoires.")


@dataclass(frozen=True, slots=True)
class OpcUaReadOnlyConnectorConfig:
    """Contrat de connexion sans secret embarqué et sans capacité Write."""

    connector_id: str
    endpoint_url: str
    security_policy_uri: str
    application_certificate_ref: str
    private_key_secret_ref: str
    trust_list_ref: str
    identity_secret_ref: str | None
    node_mappings: tuple[OpcUaNodeMapping, ...]
    configuration_source_ref: str
    security_mode: str = "SignAndEncrypt"

    def __post_init__(self) -> None:
        required = (
            self.connector_id,
            self.endpoint_url,
            self.security_policy_uri,
            self.application_certificate_ref,
            self.private_key_secret_ref,
            self.trust_list_ref,
            self.configuration_source_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Les références de configuration OPC UA obligatoires ne peuvent être vides."
            )
        parsed = urlsplit(self.endpoint_url)
        if parsed.scheme.lower() != "opc.tcp" or not parsed.hostname or parsed.port is None:
            raise ValueError(
                "L'endpoint OPC UA doit être une URL opc.tcp:// avec hôte et port explicites."
            )
        if self.security_mode != "SignAndEncrypt":
            raise ValueError(
                "PETROLE exige le mode OPC UA SignAndEncrypt pour le connecteur industriel."
            )
        if self.identity_secret_ref is not None and not self.identity_secret_ref.strip():
            raise ValueError("La référence de secret d'identité ne peut pas être vide.")
        if not self.node_mappings:
            raise ValueError("Le connecteur OPC UA doit déclarer au moins un mapping de nœud.")
        tag_refs = [mapping.tag_ref for mapping in self.node_mappings]
        if len(tag_refs) != len(set(tag_refs)):
            raise ValueError("Un tag PETROLE ne peut être mappé qu'une fois dans un connecteur.")
        source_nodes = [(mapping.namespace_uri, mapping.node_id) for mapping in self.node_mappings]
        if len(source_nodes) != len(set(source_nodes)):
            raise ValueError(
                "Un nœud OPC UA source ne peut être mappé qu'une fois dans un connecteur."
            )
        secret_refs = (self.private_key_secret_ref, self.identity_secret_ref)
        if any(ref is not None and "-----BEGIN" in ref for ref in secret_refs):
            raise ValueError(
                "La configuration doit référencer les secrets, jamais embarquer une clé privée."
            )


__all__ = ["OpcUaNodeMapping", "OpcUaReadOnlyConnectorConfig"]
