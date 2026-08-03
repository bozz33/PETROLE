"""Matrice de cent entrées invalides exigée par D05 § 12.

Chaque cas traverse un schéma public de l'API. Le contrôle vérifie deux propriétés : l'entrée
est refusée avec une erreur structurée Pydantic, puis une entrée saine produit exactement le
même modèle qu'avant l'échec. Cette seconde assertion protège contre une mutation partielle
ou une corruption d'état pendant la validation.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from hydro_api.schemas.network import NetworkEdgeCreate, NetworkNodeCreate
from hydro_api.schemas.operations import (
    OptimizationCreate,
    TankCreate,
    TransferCreate,
)


@dataclass(frozen=True, slots=True)
class InvalidInputCase:
    """Entrée invalide et modèle public chargé de la refuser."""

    identifier: str
    model: type[BaseModel]
    valid_payload: dict[str, Any]
    invalid_payload: dict[str, Any]


def _changed(payload: dict[str, Any], **changes: Any) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    result.update(changes)
    return result


ORG_ID = uuid.UUID(int=1)
SITE_ID = uuid.UUID(int=2)
SOURCE_ID = uuid.UUID(int=3)
DESTINATION_ID = uuid.UUID(int=4)

VALID_NODE = {
    "code": "N-001",
    "name": "Nœud valide",
    "kind": "junction",
    "elevation_m": 10.0,
}

VALID_EDGE = {
    "from_node_id": SOURCE_ID,
    "to_node_id": DESTINATION_ID,
    "code": "T-001",
    "name": "Tronçon valide",
    "sequence": 1,
    "length_m": 100.0,
    "inner_diameter_m": 0.5,
    "roughness_m": 4.5e-5,
    "mawp_pa": 8.0e6,
    "profile": [
        {"chainage_m": 0.0, "elevation_m": 10.0},
        {"chainage_m": 100.0, "elevation_m": 12.0},
    ],
}

VALID_TANK = {
    "organization_id": ORG_ID,
    "site_id": SITE_ID,
    "name": "Bac valide",
    "code": "B-001",
    "current_level_m": 5.0,
    "dead_volume_m3": 0.0,
    "levels": {
        "minimum_m": 1.0,
        "low_m": 2.0,
        "normal_m": 5.0,
        "high_m": 8.0,
        "high_high_m": 9.0,
    },
    "strapping": [
        {"height_m": 0.0, "volume_m3": 0.0},
        {"height_m": 10.0, "volume_m3": 1_000.0},
    ],
}

VALID_TRANSFER = {
    "source_tank_id": SOURCE_ID,
    "destination_tank_id": DESTINATION_ID,
    "fluid_id": "JET-A1",
    "requested_flow_m3_s": 0.1,
    "target_volume_m3": 100.0,
    "time_step_s": 60.0,
    "maximum_duration_s": 86_400.0,
    "loss_fraction": 0.0,
}

VALID_OPTIMIZATION = {
    "objective": "min_energy",
    "pump_ids": ["P-001", "P-002"],
    "speed_options": [0.8, 0.9, 1.0],
    "reference_duration_s": 3_600.0,
    "maximum_configurations": 100_000,
    "constraints": {},
}


def _node_cases() -> list[InvalidInputCase]:
    bad_codes = [
        "",
        " ",
        " A",
        "A B",
        "#",
        "@",
        "/",
        "\\",
        "A*",
        "A?",
        "A!",
        "É",
        "-A",
        "_A",
        ".A",
        "A|B",
        "A:B",
        "A<B",
        "A>B",
        "A" * 81,
    ]
    return [
        InvalidInputCase(
            f"NODE-{index:02d}",
            NetworkNodeCreate,
            VALID_NODE,
            _changed(VALID_NODE, code=value),
        )
        for index, value in enumerate(bad_codes, start=1)
    ]


def _edge_cases() -> list[InvalidInputCase]:
    changes = [
        {"length_m": 0.0},
        {"length_m": -1.0},
        {"inner_diameter_m": 0.0},
        {"inner_diameter_m": -0.5},
        {"roughness_m": -1.0e-9},
        {"roughness_m": -1.0},
        {"mawp_pa": 0.0},
        {"mawp_pa": -1.0},
        {"sequence": 0},
        {"sequence": -1},
        {"to_node_id": SOURCE_ID},
        {"profile": []},
        {"profile": [{"chainage_m": 0.0, "elevation_m": 0.0}]},
        {
            "profile": [
                {"chainage_m": 0.0, "elevation_m": 0.0},
                {"chainage_m": 0.0, "elevation_m": 1.0},
            ]
        },
        {
            "profile": [
                {"chainage_m": 1.0, "elevation_m": 0.0},
                {"chainage_m": 100.0, "elevation_m": 1.0},
            ]
        },
        {
            "profile": [
                {"chainage_m": 0.0, "elevation_m": 0.0},
                {"chainage_m": 99.0, "elevation_m": 1.0},
            ]
        },
        {
            "profile": [
                {"chainage_m": -1.0, "elevation_m": 0.0},
                {"chainage_m": 100.0, "elevation_m": 1.0},
            ]
        },
        {
            "profile": [
                {"chainage_m": 0.0, "elevation_m": 0.0},
                {"chainage_m": 50.0, "elevation_m": 1.0},
                {"chainage_m": 40.0, "elevation_m": 2.0},
            ]
        },
        {
            "profile": [
                {"chainage_m": 0.0, "elevation_m": 0.0, "latitude": 91.0},
                {"chainage_m": 100.0, "elevation_m": 1.0},
            ]
        },
        {
            "profile": [
                {"chainage_m": 0.0, "elevation_m": 0.0, "longitude": 181.0},
                {"chainage_m": 100.0, "elevation_m": 1.0},
            ]
        },
    ]
    return [
        InvalidInputCase(
            f"EDGE-{index:02d}",
            NetworkEdgeCreate,
            VALID_EDGE,
            _changed(VALID_EDGE, **change),
        )
        for index, change in enumerate(changes, start=1)
    ]


def _tank_cases() -> list[InvalidInputCase]:
    changes = [
        {"name": ""},
        {"name": "N" * 201},
        {"code": ""},
        {"code": "B" * 51},
        {"tank_type": "inconnu"},
        {"status": "inconnu"},
        {"current_level_m": -1.0},
        {"dead_volume_m3": -1.0},
        {"fluid_id": "F" * 101},
        {"compatible_fluid_ids": [f"F-{index}" for index in range(101)]},
        {"strapping": []},
        {"strapping": [{"height_m": 0.0, "volume_m3": 0.0}]},
        {
            "strapping": [
                {"height_m": -1.0, "volume_m3": 0.0},
                {"height_m": 10.0, "volume_m3": 1_000.0},
            ]
        },
        {
            "strapping": [
                {"height_m": 0.0, "volume_m3": -1.0},
                {"height_m": 10.0, "volume_m3": 1_000.0},
            ]
        },
        {"levels": _changed(VALID_TANK["levels"], minimum_m=-1.0)},
        {"levels": _changed(VALID_TANK["levels"], low_m=-1.0)},
        {"levels": _changed(VALID_TANK["levels"], normal_m=-1.0)},
        {"levels": _changed(VALID_TANK["levels"], high_m=-1.0)},
        {"levels": _changed(VALID_TANK["levels"], high_high_m=0.0)},
        {"levels": _changed(VALID_TANK["levels"], high_high_m=-1.0)},
    ]
    return [
        InvalidInputCase(
            f"TANK-{index:02d}",
            TankCreate,
            VALID_TANK,
            _changed(VALID_TANK, **change),
        )
        for index, change in enumerate(changes, start=1)
    ]


def _transfer_cases() -> list[InvalidInputCase]:
    changes = [
        {"requested_flow_m3_s": 0.0},
        {"requested_flow_m3_s": -1.0},
        {"target_volume_m3": 0.0},
        {"target_volume_m3": -1.0},
        {"target_volume_m3": None, "target_destination_level_m": 0.0},
        {"target_volume_m3": None, "target_destination_level_m": -1.0},
        {"target_volume_m3": None, "target_duration_s": 0.0},
        {"target_volume_m3": None, "target_duration_s": -1.0},
        {"time_step_s": 0.0},
        {"time_step_s": -1.0},
        {"maximum_duration_s": 0.0},
        {"maximum_duration_s": -1.0},
        {"maximum_flow_m3_s": 0.0},
        {"maximum_flow_m3_s": -1.0},
        {"loss_fraction": -0.1},
        {"loss_fraction": 1.0},
        {"discharge_pressure_pa": -1.0},
        {"absorbed_power_w": -1.0},
        {"target_volume_m3": None},
        {"target_destination_level_m": 5.0, "target_duration_s": 1_000.0},
    ]
    return [
        InvalidInputCase(
            f"TRANSFER-{index:02d}",
            TransferCreate,
            VALID_TRANSFER,
            _changed(VALID_TRANSFER, **change),
        )
        for index, change in enumerate(changes, start=1)
    ]


def _optimization_cases() -> list[InvalidInputCase]:
    changes = [
        {"objective": "inconnu"},
        {"speed_options": []},
        {"speed_options": [1.0] * 11},
        {"speed_options": ["invalide"]},
        {"reference_duration_s": 0.0},
        {"reference_duration_s": -1.0},
        {"reference_duration_s": None},
        {"energy_price_per_kwh": -1.0},
        {"maximum_configurations": 0},
        {"maximum_configurations": 1_000_001},
        {"maximum_configurations": "invalide"},
        {"maximum_evaluations": 0},
        {"maximum_evaluations": 1_000_001},
        {"constraints": {"minimum_flow_m3_s": -1.0}},
        {"constraints": {"maximum_flow_m3_s": -1.0}},
        {"constraints": {"minimum_pressure_pa": -1.0}},
        {"constraints": {"maximum_pressure_pa": -1.0}},
        {"constraints": {"maximum_active_pumps": -1}},
        {"constraints": []},
        {"constraints": {"allow_violations": "invalide"}},
    ]
    return [
        InvalidInputCase(
            f"OPT-{index:02d}",
            OptimizationCreate,
            VALID_OPTIMIZATION,
            _changed(VALID_OPTIMIZATION, **change),
        )
        for index, change in enumerate(changes, start=1)
    ]


INVALID_CASES = (
    *_node_cases(),
    *_edge_cases(),
    *_tank_cases(),
    *_transfer_cases(),
    *_optimization_cases(),
)


def test_matrice_contient_exactement_cent_entrees_invalides() -> None:
    assert len(INVALID_CASES) == 100
    assert len({case.identifier for case in INVALID_CASES}) == 100


@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda case: case.identifier)
def test_entree_invalide_est_diagnostiquee_sans_corruption(case: InvalidInputCase) -> None:
    before = case.model.model_validate(copy.deepcopy(case.valid_payload)).model_dump(mode="json")

    with pytest.raises(ValidationError):
        case.model.model_validate(copy.deepcopy(case.invalid_payload))

    after = case.model.model_validate(copy.deepcopy(case.valid_payload)).model_dump(mode="json")
    assert after == before
