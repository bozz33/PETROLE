"""Tests du contrat de sécurité OPC UA avant choix d'un adapter réseau."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hydro_api.industrial.opcua_policy import (
    OpcUaEndpointPolicy,
    OpcUaOperation,
    assert_read_only_operation,
)


def _policy(**overrides) -> OpcUaEndpointPolicy:
    payload = {
        "endpoint_url": "opc.tcp://simulator.local:4840",
        "security_mode": "SignAndEncrypt",
        "security_policy_uri": "urn:petrole:test:approved-policy",
        "application_uri": "urn:petrole:gateway:test",
        "certificate_ref": "secret://opcua/client-cert",
        "trust_store_ref": "secret://opcua/trust-store",
        "allowed_namespace_uris": ["urn:operator:process"],
    }
    payload.update(overrides)
    return OpcUaEndpointPolicy.model_validate(payload)


def test_default_opcua_policy_is_read_only() -> None:
    policy = _policy()
    assert set(policy.allowed_operations) == {
        OpcUaOperation.BROWSE,
        OpcUaOperation.READ,
        OpcUaOperation.SUBSCRIBE,
        OpcUaOperation.HISTORY_READ,
        OpcUaOperation.REPUBLISH,
        OpcUaOperation.SUBSCRIPTION_ACKNOWLEDGE,
    }
    for operation in policy.allowed_operations:
        assert_read_only_operation(operation)


@pytest.mark.parametrize(
    "operation",
    [
        OpcUaOperation.WRITE,
        OpcUaOperation.CALL,
        OpcUaOperation.PUBLISH_EVENT,
        OpcUaOperation.ACKNOWLEDGE,
    ],
)
def test_process_modifying_operations_are_rejected(operation: OpcUaOperation) -> None:
    with pytest.raises(PermissionError, match="PETROLE est read-only"):
        assert_read_only_operation(operation)

    with pytest.raises(ValidationError, match="interdites"):
        _policy(allowed_operations=[OpcUaOperation.READ, operation])


@pytest.mark.parametrize(
    "operation",
    [OpcUaOperation.REPUBLISH, OpcUaOperation.SUBSCRIPTION_ACKNOWLEDGE],
)
def test_subscription_recovery_operations_remain_read_only(operation: OpcUaOperation) -> None:
    assert_read_only_operation(operation)
    policy = _policy(allowed_operations=[OpcUaOperation.READ, operation])
    assert operation in policy.allowed_operations


def test_pilot_policy_requires_sign_and_encrypt_and_namespace_uri() -> None:
    with pytest.raises(ValidationError, match="SignAndEncrypt"):
        _policy(security_mode="Sign")

    with pytest.raises(ValidationError, match="namespace"):
        _policy(allowed_namespace_uris=["   "])
