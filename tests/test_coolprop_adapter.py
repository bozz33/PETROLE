from __future__ import annotations

import pytest

from hydro_gas import (
    CoolPropEvaluationEnvelope,
    CoolPropPureFluidDefinition,
    evaluate_coolprop_properties,
)


def _definition() -> CoolPropPureFluidDefinition:
    return CoolPropPureFluidDefinition(
        fluid="Water",
        backend="HEOS",
        source_ref="project://fluid/water-reference",
        envelope=CoolPropEvaluationEnvelope(
            minimum_temperature_k=280.0,
            maximum_temperature_k=350.0,
            minimum_pressure_pa=80_000.0,
            maximum_pressure_pa=2_000_000.0,
            source_ref="project://fluid/water-reference/domain",
        ),
    )


def test_coolprop_adapter_returns_si_properties_and_runtime_provenance() -> None:
    result = evaluate_coolprop_properties(
        _definition(),
        temperature_k=300.0,
        pressure_pa=101_325.0,
    )

    assert result.coolprop_fluid_key == "HEOS::Water"
    assert result.coolprop_version
    assert result.coolprop_gitrevision
    assert result.density_kg_m3 == pytest.approx(996.56, rel=2e-3)
    assert result.dynamic_viscosity_pa_s == pytest.approx(8.54e-4, rel=2e-2)
    assert result.kinematic_viscosity_m2_s == pytest.approx(
        result.dynamic_viscosity_pa_s / result.density_kg_m3
    )
    assert result.vapor_pressure_pa == pytest.approx(3_537.0, rel=2e-2)
    assert result.definition_source_ref == "project://fluid/water-reference"


def test_coolprop_adapter_refuses_state_outside_project_envelope_before_backend_call() -> None:
    with pytest.raises(ValueError, match="hors du domaine projet"):
        evaluate_coolprop_properties(
            _definition(),
            temperature_k=360.0,
            pressure_pa=101_325.0,
        )


def test_coolprop_pure_adapter_rejects_mixture_syntax() -> None:
    with pytest.raises(ValueError, match="purs/pseudo-purs"):
        CoolPropPureFluidDefinition(
            fluid="Methane[0.9]&Ethane[0.1]",
            backend="HEOS",
            source_ref="lab://gas/sample-A",
            envelope=CoolPropEvaluationEnvelope(
                minimum_temperature_k=250.0,
                maximum_temperature_k=350.0,
                minimum_pressure_pa=100_000.0,
                maximum_pressure_pa=10_000_000.0,
                source_ref="lab://gas/sample-A/domain",
            ),
        )
