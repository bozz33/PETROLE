"""Validation du Tank & Transfer Core.

Les cas couvrent VAL-TNK-002, VAL-TNK-004 et VAL-TNK-006 à VAL-TNK-008.
"""

from __future__ import annotations

import math

import pytest

from hydro_domain.enums import TransferStopReason
from hydro_domain.tanks import StrappingTable, Tank, TankLevels
from hydro_shared.codes import ViolationCode, WarningCode
from hydro_shared.errors import InvalidInputError
from hydro_tanks import (
    TankTransferEngine,
    TransferBalanceInput,
    TransferOperatingPoint,
    TransferRequest,
    VolumeMeasurement,
    compute_transfer_balance,
    constant_operating_point,
)


@pytest.fixture
def tanks() -> tuple[Tank, Tank]:
    """Deux bacs cylindriques identiques, avec marges de sécurité connues."""

    table = StrappingTable.from_vertical_cylinder(diameter_m=10.0, height_m=10.0)
    levels = TankLevels(
        minimum_m=1.0,
        low_m=1.5,
        normal_m=5.0,
        high_m=7.0,
        high_high_m=9.0,
    )
    source = Tank(
        id="TK-S",
        name="Bac source",
        strapping=table,
        levels=levels,
        current_level_m=8.0,
        fluid_id="diesel",
    )
    destination = Tank(
        id="TK-D",
        name="Bac destination",
        strapping=table,
        levels=levels,
        current_level_m=2.0,
        compatible_fluid_ids=("diesel",),
    )
    return source, destination


def test_transfert_volume_constant_et_bilan_exact(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.1,
        target_volume_m3=100.0,
        time_step_s=333.0,
        loss_fraction=0.01,
    )

    result = TankTransferEngine().simulate(
        request,
        constant_operating_point(
            0.1,
            discharge_pressure_pa=800_000.0,
            absorbed_power_w=50_000.0,
        ),
    )

    assert result.stop_reason is TransferStopReason.TARGET_VOLUME_REACHED
    assert result.target_reached
    assert result.duration_s == pytest.approx(1_000.0)
    assert result.withdrawn_volume_m3 == pytest.approx(100.0)
    assert result.received_volume_m3 == pytest.approx(99.0)
    assert result.losses_m3 == pytest.approx(1.0)
    assert result.balance_residual_m3 == pytest.approx(0.0, abs=1e-10)
    assert result.energy_j == pytest.approx(50_000_000.0)
    assert not result.violation_codes


def test_objectif_niveau_atteint_au_temps_interpole(tanks):
    source, destination = tanks
    area_m2 = math.pi * 10.0**2 / 4.0
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.2,
        target_destination_level_m=3.0,
        time_step_s=300.0,
    )

    result = TankTransferEngine().simulate(request)

    assert result.stop_reason is TransferStopReason.TARGET_LEVEL_REACHED
    assert result.destination_final.current_level_m == pytest.approx(3.0)
    assert result.received_volume_m3 == pytest.approx(area_m2)
    assert result.duration_s == pytest.approx(area_m2 / 0.2)


def test_objectif_duree(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.05,
        target_duration_s=125.0,
        time_step_s=60.0,
    )

    result = TankTransferEngine().simulate(request)

    assert result.stop_reason is TransferStopReason.DURATION_REACHED
    assert result.duration_s == pytest.approx(125.0)
    assert result.withdrawn_volume_m3 == pytest.approx(6.25)


def test_niveau_tres_haut_localise_dans_le_pas(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.01,
        target_duration_s=10_000.0,
        time_step_s=1_000.0,
    )

    result = TankTransferEngine().simulate(
        request,
        constant_operating_point(1.0),
    )

    available = destination.available_capacity_m3
    assert result.stop_reason is TransferStopReason.DESTINATION_HIGH_LEVEL
    assert result.destination_final.current_level_m == pytest.approx(9.0)
    assert result.duration_s == pytest.approx(available)
    assert result.samples[-1].time_s < 1_000.0
    assert WarningCode.NEAR_LIMIT.value in result.warning_codes


def test_capacite_insuffisante_bloquee_avant_demarrage(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.1,
        target_volume_m3=10_000.0,
    )

    result = TankTransferEngine().simulate(request)

    assert result.stop_reason is TransferStopReason.NOT_FEASIBLE
    assert not result.preflight_feasible
    assert result.duration_s == 0.0
    assert result.withdrawn_volume_m3 == 0.0
    assert any("capacité" in message or "soutirable" in message for message in result.messages)


def test_produit_incompatible_bloque(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="essence",
        requested_flow_m3_s=0.1,
        target_volume_m3=10.0,
    )

    result = TankTransferEngine().simulate(request)

    assert result.stop_reason is TransferStopReason.NOT_FEASIBLE
    assert ViolationCode.TANK_PRODUCT_INCOMPATIBLE.value in result.violation_codes


def test_debit_dynamique_superieur_a_la_limite(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.1,
        maximum_flow_m3_s=0.2,
        target_volume_m3=10.0,
    )

    result = TankTransferEngine().simulate(
        request,
        constant_operating_point(0.25),
    )

    assert result.stop_reason is TransferStopReason.HYDRAULIC_CONSTRAINT
    assert result.withdrawn_volume_m3 == 0.0
    assert any("dépasse" in message for message in result.messages)


def test_contrainte_hydraulique_apres_un_pas(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.1,
        target_volume_m3=50.0,
        time_step_s=10.0,
    )

    def resolver(state):
        if state.time_s >= 10.0:
            return TransferOperatingPoint(
                flow_m3_s=0.0,
                feasible=False,
                detail="Pression disponible insuffisante.",
            )
        return TransferOperatingPoint(flow_m3_s=0.1)

    result = TankTransferEngine().simulate(request, resolver)

    assert result.stop_reason is TransferStopReason.HYDRAULIC_CONSTRAINT
    assert result.withdrawn_volume_m3 == pytest.approx(1.0)
    assert result.messages[-1] == "Pression disponible insuffisante."


def test_alerte_niveau_haut(tanks):
    source, destination = tanks
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="diesel",
        requested_flow_m3_s=0.5,
        target_destination_level_m=7.5,
        time_step_s=1_000.0,
    )

    result = TankTransferEngine().simulate(request)

    assert result.stop_reason is TransferStopReason.TARGET_LEVEL_REACHED
    assert WarningCode.NEAR_LIMIT.value in result.warning_codes
    assert result.destination_final.current_level_m == pytest.approx(7.5)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({}, "Un seul objectif"),
        (
            {"target_volume_m3": 1.0, "target_duration_s": 10.0},
            "Un seul objectif",
        ),
        ({"target_volume_m3": -1.0}, "strictement positive"),
    ],
)
def test_demande_invalide_rejetee(tanks, updates, message):
    source, destination = tanks
    arguments = {
        "source": source,
        "destination": destination,
        "fluid_id": "diesel",
        "requested_flow_m3_s": 0.1,
        **updates,
    }
    with pytest.raises(InvalidInputError, match=message):
        TransferRequest(**arguments)


def test_bilan_matiere_avec_incertitudes():
    data = TransferBalanceInput(
        source_opening=VolumeMeasurement(1_000.0, 1.0, "Source ouverture"),
        source_closing=VolumeMeasurement(900.0, 1.0, "Source fermeture"),
        destination_opening=VolumeMeasurement(200.0, 1.0, "Destination ouverture"),
        destination_closing=VolumeMeasurement(298.0, 1.0, "Destination fermeture"),
        metered_volume=VolumeMeasurement(99.0, 0.5, "Compteur"),
        accounted_losses=VolumeMeasurement(1.0, 1.0, "Pertes"),
    )

    result = compute_transfer_balance(data)

    assert result.source_withdrawal_m3 == pytest.approx(100.0)
    assert result.destination_receipt_m3 == pytest.approx(98.0)
    assert result.system_imbalance_m3 == pytest.approx(1.0)
    assert result.meter_source_difference_m3 == pytest.approx(-1.0)
    assert result.meter_destination_difference_m3 == pytest.approx(1.0)
    assert result.combined_standard_uncertainty_m3 == pytest.approx(math.sqrt(5.0))
    assert result.expanded_uncertainty_m3 == pytest.approx(2.0 * math.sqrt(5.0))
    assert result.within_tolerance


def test_bilan_hors_tolerance_sans_incertitude():
    data = TransferBalanceInput(
        source_opening=VolumeMeasurement(100.0),
        source_closing=VolumeMeasurement(0.0),
        destination_opening=VolumeMeasurement(0.0),
        destination_closing=VolumeMeasurement(98.0),
        metered_volume=VolumeMeasurement(100.0),
        relative_tolerance=0.001,
    )

    result = compute_transfer_balance(data)

    assert result.system_imbalance_m3 == pytest.approx(2.0)
    assert result.acceptance_limit_m3 == pytest.approx(0.1)
    assert not result.within_tolerance


def test_incertitude_negative_rejetee():
    with pytest.raises(InvalidInputError, match="incertitude-type"):
        VolumeMeasurement(10.0, -0.1)
