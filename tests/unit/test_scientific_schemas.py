"""Tests unitaires des sous-schémas scientifiques typés (API).

Ces tests valident que les contrats documentés dans l'OpenAPI reflètent bien
les exigences des moteurs : courbes de pompe, propriétés de fluide, conditions
aux limites, configuration des stations. Ils ne nécessitent aucune base de
données et restent dans la suite rapide (``not slow``).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hydro_api.schemas.catalog import CatalogItemCreate
from hydro_api.schemas.core import ScenarioCreate
from hydro_api.schemas.network import NetworkNodeCreate
from hydro_api.schemas.scientific import (
    FluidInput,
    PropertyTableInput,
    PumpCurveInput,
    PumpModelInput,
    ScenarioPayloadInput,
    StationConfigurationInput,
)


def _curve() -> dict:
    return {
        "flows_m3_s": [0.1, 0.3, 0.5],
        "heads_m": [40.0, 32.0, 20.0],
        "efficiencies": [0.55, 0.78, 0.70],
        "npshr_m": [2.0, 3.5, 5.5],
    }


class TestPumpCurveInput:
    def test_courbe_valide(self) -> None:
        curve = PumpCurveInput(**_curve())
        assert len(curve.flows_m3_s) == 3

    def test_courbe_trop_courte(self) -> None:
        with pytest.raises(ValidationError):
            PumpCurveInput(flows_m3_s=[0.1], heads_m=[40.0])

    def test_series_de_longueurs_incoherentes(self) -> None:
        with pytest.raises(ValidationError, match="efficiencies"):
            PumpCurveInput(flows_m3_s=[0.1, 0.3], heads_m=[40.0, 32.0], efficiencies=[0.5])

    def test_interpolation_invalide(self) -> None:
        with pytest.raises(ValidationError):
            PumpCurveInput(flows_m3_s=[0.1, 0.3], heads_m=[40.0, 32.0], interpolation="cubic")


class TestPumpModelInput:
    def test_modele_valide(self) -> None:
        model = PumpModelInput(curve=_curve(), motor_rated_power_w=1_500_000)
        assert model.npsh_margin_m == 0.5
        assert model.min_speed_ratio == 0.7

    def test_courbe_obligatoire(self) -> None:
        with pytest.raises(ValidationError):
            PumpModelInput()  # type: ignore[call-arg]


class TestFluidInput:
    def test_fluide_densite_scalaire(self) -> None:
        fluid = FluidInput(category="crude", density_kg_m3=850.0, kinematic_viscosity_m2_s=1e-5)
        assert fluid.density_kg_m3 == 850.0

    def test_fluide_table_de_densite(self) -> None:
        fluid = FluidInput(
            category="gasoline",
            density_table={
                "points": [
                    {"temperature_k": 288.0, "value": 740.0},
                    {"temperature_k": 293.0, "value": 735.0},
                ]
            },
        )
        assert fluid.density_table is not None
        assert len(fluid.density_table.points) == 2

    def test_fluide_sans_source_de_densite_refuse(self) -> None:
        with pytest.raises(ValidationError, match="masse volumique"):
            FluidInput(category="custom", kinematic_viscosity_m2_s=1e-6)

    def test_table_temperatures_non_croissantes(self) -> None:
        with pytest.raises(ValidationError, match="croissantes"):
            PropertyTableInput(
                points=[
                    {"temperature_k": 300.0, "value": 700.0},
                    {"temperature_k": 290.0, "value": 710.0},
                ]
            )


class TestScenarioPayloadInput:
    def test_conditions_limites_coherentes(self) -> None:
        payload = ScenarioPayloadInput(
            imposed_flow_m3_s=0.42,
            inlet_pressure_pa=5.0e5,
            solver={"friction_model": "colebrook_white", "max_iterations": 50},
        )
        assert payload.imposed_flow_m3_s == 0.42
        assert payload.solver.friction_model == "colebrook_white"
        assert payload.solver.max_iterations == 50

    def test_surcharges_pompe(self) -> None:
        payload = ScenarioPayloadInput(
            pump_overrides=[{"pump_id": "P1", "running": False}],
        )
        assert payload.pump_overrides[0].pump_id == "P1"
        assert payload.pump_overrides[0].running is False


class TestStationConfigurationInput:
    def test_configuration_par_defaut(self) -> None:
        cfg = StationConfigurationInput()
        assert cfg.arrangement == "series"
        assert cfg.suction_line_k == 0.0
        assert cfg.drive_efficiency == 1.0

    def test_npsh_parametre(self) -> None:
        cfg = StationConfigurationInput(
            suction_line_k=0.5,
            suction_line_diameter_m=0.6,
            discharge_pressure_max_pa=8.0e6,
        )
        assert cfg.suction_line_diameter_m == 0.6


class TestPayloadsIntegresDansRessources:
    """Vérifie que les unions typées sont acceptées par les schémas de ressource."""

    def test_noeud_station_avec_configuration_typée(self) -> None:
        node = NetworkNodeCreate(
            code="ST01",
            name="Station amont",
            kind="station",
            payload={"arrangement": "parallel", "suction_line_diameter_m": 0.8},
        )
        # Le payload doit être sérialisable en dict (persistance JSONB).
        dumped = node.model_dump()
        assert isinstance(dumped["payload"], dict)
        assert dumped["payload"]["arrangement"] == "parallel"

    def test_noeud_sans_configuration_accepte_dict_vide(self) -> None:
        node = NetworkNodeCreate(code="J01", name="Jonction", kind="junction")
        assert node.payload == {}

    def test_scenario_avec_payload_scientifique(self) -> None:
        scenario = ScenarioCreate(
            name="Cas nominal",
            payload={"imposed_flow_m3_s": 0.5, "inlet_pressure_pa": 4.0e5},
        )
        dumped = scenario.model_dump()
        assert isinstance(dumped["payload"], dict)

    def test_catalog_item_pump_typé(self) -> None:
        import uuid

        item = CatalogItemCreate(
            organization_id=uuid.uuid4(),
            code="PUMP01",
            name="Pompe centrifuge 200",
            payload=_curve(),
        )
        dumped = item.model_dump()
        assert isinstance(dumped["payload"], dict)
        assert "flows_m3_s" in dumped["payload"]
