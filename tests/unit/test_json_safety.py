"""Tests du contrat numérique et JSON strict (ADR-TEST-DB-001).

Ces tests ne nécessitent aucune base de données : ils valident le normaliseur
et le sérialiseur strict sur des structures pures, y compris les scalaires
NumPy produits par les moteurs scientifiques.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from hydro_shared.json_safety import (
    NonFiniteKind,
    normalize_json_numbers,
    strict_json_dumps,
)


class TestNormalisation:
    def test_structure_finie_est_inchangee(self) -> None:
        payload = {"a": 1, "b": [2.5, 3], "c": {"d": None, "e": "x"}}

        result = normalize_json_numbers(payload)

        assert result.value == payload
        assert result.occurrences == ()
        assert result.has_non_finite is False

    def test_nan_est_remplace_par_null_avec_occurrence(self) -> None:
        result = normalize_json_numbers({"residual": float("nan")})

        assert result.value == {"residual": None}
        assert result.has_non_finite is True
        assert result.occurrences[0].path == "$.residual"
        assert result.occurrences[0].kind is NonFiniteKind.NAN

    @pytest.mark.parametrize(
        "value,kind",
        [
            (float("inf"), NonFiniteKind.POSITIVE_INFINITY),
            (float("-inf"), NonFiniteKind.NEGATIVE_INFINITY),
        ],
    )
    def test_infinis_sont_classes(self, value: float, kind: NonFiniteKind) -> None:
        result = normalize_json_numbers({"pressure": value})

        assert result.value == {"pressure": None}
        assert result.occurrences[0].kind is kind

    def test_structures_imbriquees_et_listes(self) -> None:
        payload = {
            "stations": [
                {"name": "S1", "npsh_margin_m": float("nan")},
                {"name": "S2", "flow_m3_s": float("inf")},
            ],
            "ok": 42,
        }

        result = normalize_json_numbers(payload)

        assert result.value == {
            "stations": [
                {"name": "S1", "npsh_margin_m": None},
                {"name": "S2", "flow_m3_s": None},
            ],
            "ok": 42,
        }
        paths = {o.path for o in result.occurrences}
        assert paths == {"$.stations[0].npsh_margin_m", "$.stations[1].flow_m3_s"}

    def test_scalaires_numpy_sont_convertis(self) -> None:
        result = normalize_json_numbers({"head_m": np.float64(120.5)})

        assert result.value == {"head_m": 120.5}
        assert isinstance(result.value["head_m"], float)

    def test_scalaire_numpy_nan_est_detecte(self) -> None:
        result = normalize_json_numbers({"residual": np.float64("nan")})

        assert result.value == {"residual": None}
        assert result.occurrences[0].kind is NonFiniteKind.NAN

    def test_valeur_originale_non_mutee(self) -> None:
        original = {"residual": float("nan")}

        normalize_json_numbers(original)

        # La structure d'entrée ne doit pas être mutée par la normalisation.
        assert math.isnan(original["residual"])

    def test_type_non_json_rejete_explicitement(self) -> None:
        with pytest.raises(TypeError, match="non compatible JSON"):
            normalize_json_numbers({"objet": object()})


class TestSerialiseurStrict:
    def test_structure_finie_est_serialisee(self) -> None:
        serialized = strict_json_dumps({"a": 1, "b": 2.5})

        assert json.loads(serialized) == {"a": 1, "b": 2.5}

    @pytest.mark.parametrize(
        "value",
        [float("nan"), float("inf"), float("-inf")],
    )
    def test_valeur_non_finie_rejetee(self, value: float) -> None:
        with pytest.raises(ValueError):
            strict_json_dumps({"residual": value})

    def test_chain_defense_normalise_puis_serialise(self) -> None:
        # La chaîne défensive : normaliser puis sérialiser ne lève jamais.
        raw = {"residual": float("nan"), "ok": 1}
        normalized = normalize_json_numbers(raw)

        serialized = strict_json_dumps(normalized.value)

        assert json.loads(serialized) == {"residual": None, "ok": 1}
