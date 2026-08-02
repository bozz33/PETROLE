"""Tests des unités et de la cohérence dimensionnelle (D18 § 3, famille « Unités »).

Ces tests couvrent l'exigence FR-GEN-003 : conversion vers le SI interne avec conservation de
la valeur d'origine, et le rejet explicite des unités inconnues ou incompatibles (DQ-001).
"""

from __future__ import annotations

import math

import pytest

from hydro_shared.errors import DimensionalityMismatchError, UnknownUnitError
from hydro_shared.units import (
    SI_UNITS,
    Dimension,
    Measure,
    convert,
    format_si,
    from_si,
    is_compatible,
    si_unit_for,
    to_si,
)


class TestConversionsVersLeSI:
    @pytest.mark.parametrize(
        ("value", "unit", "dimension", "expected"),
        [
            (1.0, "bar", Dimension.PRESSURE, 1.0e5),
            (1.0, "MPa", Dimension.PRESSURE, 1.0e6),
            (1.0, "kPa", Dimension.PRESSURE, 1.0e3),
            (1.0, "psi", Dimension.PRESSURE, 6894.757293168361),
            (3600.0, "m ** 3 / hour", Dimension.VOLUMETRIC_FLOW, 1.0),
            (1.0, "km", Dimension.LENGTH, 1000.0),
            (1.0, "mm", Dimension.DIAMETER, 1.0e-3),
            (1.0, "cSt", Dimension.KINEMATIC_VISCOSITY, 1.0e-6),
            (1.0, "cP", Dimension.DYNAMIC_VISCOSITY, 1.0e-3),
            (1.0, "kW", Dimension.POWER, 1.0e3),
            (1.0, "kWh", Dimension.ENERGY, 3.6e6),
            (1.0, "hour", Dimension.TIME, 3600.0),
        ],
    )
    def test_conversion_exacte(self, value, unit, dimension, expected):
        assert to_si(value, unit, dimension) == pytest.approx(expected, rel=1e-12)

    def test_temperature_celsius_est_un_decalage_pas_un_facteur(self):
        """Les températures sont converties avec leur origine, pas par simple facteur."""
        assert to_si(0.0, "degC", Dimension.TEMPERATURE) == pytest.approx(273.15)
        assert to_si(20.0, "degC", Dimension.TEMPERATURE) == pytest.approx(293.15)
        assert from_si(293.15, "degC", Dimension.TEMPERATURE) == pytest.approx(20.0)

    def test_aller_retour_si(self):
        for dimension, si in SI_UNITS.items():
            if dimension is Dimension.TEMPERATURE:
                continue  # traité séparément : unité à origine décalée
            assert to_si(1.0, si, dimension) == pytest.approx(1.0)

    def test_si_unit_for(self):
        assert si_unit_for(Dimension.PRESSURE) == "Pa"
        assert si_unit_for(Dimension.VOLUMETRIC_FLOW) == "m ** 3 / s"


class TestRejets:
    def test_unite_inconnue_leve_err_unit_unknown(self):
        with pytest.raises(UnknownUnitError) as excinfo:
            to_si(1.0, "barils_par_lune", Dimension.VOLUMETRIC_FLOW)
        assert excinfo.value.code == "ERR_UNIT_UNKNOWN"
        assert "barils_par_lune" in str(excinfo.value)

    def test_unite_incompatible_leve_dimension_mismatch(self):
        with pytest.raises(DimensionalityMismatchError) as excinfo:
            to_si(1.0, "kg", Dimension.PRESSURE)
        assert excinfo.value.code == "ERR_UNIT_DIMENSION_MISMATCH"
        assert excinfo.value.context["expected"] == "Pa"

    def test_is_compatible(self):
        assert is_compatible("bar", Dimension.PRESSURE)
        assert is_compatible("psi", Dimension.PRESSURE)
        assert not is_compatible("m", Dimension.PRESSURE)
        assert not is_compatible("unite_imaginaire", Dimension.PRESSURE)

    def test_conversion_directe_incompatible(self):
        with pytest.raises(DimensionalityMismatchError):
            convert(1.0, "bar", "m ** 3")


class TestMeasure:
    def test_conserve_la_saisie_d_origine(self):
        """FR-GEN-003 : la valeur d'origine et son unité ne sont jamais perdues."""
        m = Measure.of(60.0, "bar", Dimension.PRESSURE)
        assert m.value_si == pytest.approx(6.0e6)
        assert m.original_value == 60.0
        assert m.original_unit == "bar"
        assert m.si_unit == "Pa"

    def test_measure_si_reste_identique(self):
        m = Measure.si(101325.0, Dimension.PRESSURE)
        assert m.value_si == 101325.0
        assert m.original_unit == "Pa"

    def test_to_reconvertit(self):
        m = Measure.of(1.0, "MPa", Dimension.PRESSURE)
        assert m.to("bar") == pytest.approx(10.0)

    def test_as_dict_expose_les_deux_representations(self):
        d = Measure.of(1000.0, "m ** 3 / hour", Dimension.VOLUMETRIC_FLOW).as_dict()
        assert d["unit_si"] == "m ** 3 / s"
        assert d["original_unit"] == "m ** 3 / hour"
        assert d["value_si"] == pytest.approx(1000.0 / 3600.0)

    def test_measure_est_immuable(self):
        m = Measure.of(1.0, "bar", Dimension.PRESSURE)
        with pytest.raises(AttributeError):
            m.value_si = 2.0  # type: ignore[misc]


class TestAffichage:
    def test_unite_toujours_visible(self):
        """NFR-UX-002 : les unités doivent toujours accompagner les valeurs."""
        rendered = format_si(6.0e6, Dimension.PRESSURE, "bar")
        assert "60" in rendered
        assert "bar" in rendered

    def test_affichage_par_defaut_en_si(self):
        assert "Pa" in format_si(101325.0, Dimension.PRESSURE)

    def test_pas_de_nan_silencieux(self):
        rendered = format_si(math.nan, Dimension.PRESSURE)
        assert "nan" in rendered.lower()
