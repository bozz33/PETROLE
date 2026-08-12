"""Normalisation read-only d'un DataValue OPC UA vers le pipeline PETROLE.

Référence : OPC UA 10000-4 §7.11 (DataValue), version 1.05.07 consultée
pendant l'implémentation. Le StatusCode est conservé intégralement et sa
sévérité pilote uniquement l'utilisabilité de la valeur, jamais une commande.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class OpcUaStatusSeverity(StrEnum):
    """Sévérité portée par les deux bits de poids fort d'un StatusCode OPC UA."""

    GOOD = "good"
    UNCERTAIN = "uncertain"
    BAD = "bad"


@dataclass(frozen=True, slots=True)
class OpcUaDataValue:
    """DataValue reçu du connecteur avant conversion métier."""

    value: float | int | bool | str | None
    status_code: int
    source_timestamp: datetime | None
    server_timestamp: datetime | None

    def __post_init__(self) -> None:
        if self.status_code < 0 or self.status_code > 0xFFFFFFFF:
            raise ValueError("Un StatusCode OPC UA doit tenir sur 32 bits non signés.")
        for timestamp in (self.source_timestamp, self.server_timestamp):
            if timestamp is not None and timestamp.tzinfo is None:
                raise ValueError("Les timestamps OPC UA doivent être timezone-aware.")


@dataclass(frozen=True, slots=True)
class NormalizedOpcUaDataValue:
    """Valeur analytique conservant qualité et double horodatage."""

    value: float | int | bool | str | None
    usable: bool
    quality: OpcUaStatusSeverity
    status_code: int
    source_timestamp: datetime | None
    server_timestamp: datetime | None


def status_severity(status_code: int) -> OpcUaStatusSeverity:
    """Décode la sévérité OPC UA depuis les bits 31..30 du StatusCode."""

    if status_code < 0 or status_code > 0xFFFFFFFF:
        raise ValueError("Un StatusCode OPC UA doit tenir sur 32 bits non signés.")
    severity_bits = status_code & 0xC0000000
    if severity_bits == 0x00000000:
        return OpcUaStatusSeverity.GOOD
    if severity_bits == 0x40000000:
        return OpcUaStatusSeverity.UNCERTAIN
    return OpcUaStatusSeverity.BAD


def _as_utc(timestamp: datetime | None) -> datetime | None:
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        raise ValueError("Les timestamps OPC UA doivent être timezone-aware.")
    return timestamp.astimezone(UTC)


def normalize_data_value(data_value: OpcUaDataValue) -> NormalizedOpcUaDataValue:
    """Préserve le lignage OPC UA et neutralise uniquement une valeur Bad.

    OPC UA exige qu'un client contrôle au minimum la sévérité du StatusCode
    avant d'utiliser une valeur. Une valeur `Uncertain` reste visible mais
    explicitement marquée, tandis qu'une valeur `Bad` n'est pas utilisée dans
    les calculs analytiques.
    """

    severity = status_severity(data_value.status_code)
    usable = severity is not OpcUaStatusSeverity.BAD and data_value.value is not None
    return NormalizedOpcUaDataValue(
        value=data_value.value if usable else None,
        usable=usable,
        quality=severity,
        status_code=data_value.status_code,
        source_timestamp=_as_utc(data_value.source_timestamp),
        server_timestamp=_as_utc(data_value.server_timestamp),
    )


__all__ = [
    "NormalizedOpcUaDataValue",
    "OpcUaDataValue",
    "OpcUaStatusSeverity",
    "normalize_data_value",
    "status_severity",
]
