from __future__ import annotations

import pytest

from hydro_api.industrial.opcua_config import OpcUaNodeMapping, OpcUaReadOnlyConnectorConfig


def _mapping(tag: str = "tag://PT-101", node_id: str = "nsu=urn:site-A;s=PT-101") -> OpcUaNodeMapping:
    return OpcUaNodeMapping(
        tag_ref=tag,
        namespace_uri="urn:site-A:process",
        node_id=node_id,
        source_ref="engineering://opcua-node-list/rev-4",
    )


def test_opcua_config_requires_sign_and_encrypt_and_external_secret_refs() -> None:
    config = OpcUaReadOnlyConnectorConfig(
        connector_id="opcua-site-A",
        endpoint_url="opc.tcp://gateway.site-a.internal:4840",
        security_policy_uri="http://opcfoundation.org/UA/SecurityPolicy#Aes256_Sha256_RsaPss",
        application_certificate_ref="certificate://opcua/site-A/client",
        private_key_secret_ref="secret://vault/opcua/site-A/client-key",
        trust_list_ref="trust-list://opcua/site-A/v3",
        identity_secret_ref="secret://vault/opcua/site-A/service-user",
        node_mappings=(_mapping(),),
        configuration_source_ref="config://opcua/site-A/v5",
    )

    assert config.security_mode == "SignAndEncrypt"
    assert config.node_mappings[0].namespace_uri == "urn:site-A:process"


def test_opcua_config_rejects_non_opc_tcp_endpoint_and_weaker_security_mode() -> None:
    kwargs = dict(
        connector_id="opcua-site-A",
        security_policy_uri="policy://required",
        application_certificate_ref="certificate://client",
        private_key_secret_ref="secret://key",
        trust_list_ref="trust-list://v1",
        identity_secret_ref=None,
        node_mappings=(_mapping(),),
        configuration_source_ref="config://opcua/site-A/v1",
    )
    with pytest.raises(ValueError, match="opc.tcp"):
        OpcUaReadOnlyConnectorConfig(endpoint_url="https://host:4840", **kwargs)
    with pytest.raises(ValueError, match="SignAndEncrypt"):
        OpcUaReadOnlyConnectorConfig(
            endpoint_url="opc.tcp://host:4840",
            security_mode="Sign",
            **kwargs,
        )


def test_opcua_config_rejects_embedded_private_key_material() -> None:
    with pytest.raises(ValueError, match="jamais embarquer"):
        OpcUaReadOnlyConnectorConfig(
            connector_id="opcua-site-A",
            endpoint_url="opc.tcp://host:4840",
            security_policy_uri="policy://required",
            application_certificate_ref="certificate://client",
            private_key_secret_ref="-----BEGIN PRIVATE KEY-----",
            trust_list_ref="trust-list://v1",
            identity_secret_ref=None,
            node_mappings=(_mapping(),),
            configuration_source_ref="config://opcua/site-A/v1",
        )


def test_opcua_config_rejects_duplicate_tag_or_source_node_mapping() -> None:
    duplicate_tag = (_mapping(), _mapping(node_id="nsu=urn:site-A;s=PT-102"))
    with pytest.raises(ValueError, match="tag PETROLE"):
        OpcUaReadOnlyConnectorConfig(
            connector_id="opcua-site-A",
            endpoint_url="opc.tcp://host:4840",
            security_policy_uri="policy://required",
            application_certificate_ref="certificate://client",
            private_key_secret_ref="secret://key",
            trust_list_ref="trust-list://v1",
            identity_secret_ref=None,
            node_mappings=duplicate_tag,
            configuration_source_ref="config://opcua/site-A/v1",
        )

    first = _mapping(tag="tag://PT-101")
    duplicate_node = OpcUaNodeMapping(
        tag_ref="tag://PT-102",
        namespace_uri=first.namespace_uri,
        node_id=first.node_id,
        source_ref=first.source_ref,
    )
    with pytest.raises(ValueError, match="nœud OPC UA"):
        OpcUaReadOnlyConnectorConfig(
            connector_id="opcua-site-A",
            endpoint_url="opc.tcp://host:4840",
            security_policy_uri="policy://required",
            application_certificate_ref="certificate://client",
            private_key_secret_ref="secret://key",
            trust_list_ref="trust-list://v1",
            identity_secret_ref=None,
            node_mappings=(first, duplicate_node),
            configuration_source_ref="config://opcua/site-A/v1",
        )
