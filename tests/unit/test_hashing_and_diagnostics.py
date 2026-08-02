"""Tests de la sérialisation canonique, des empreintes et des diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from hydro_shared.codes import (
    MANDATORY_CHECKS,
    ErrorCode,
    SimulationStatus,
    ViolationCode,
    WarningCode,
)
from hydro_shared.diagnostics import (
    Diagnostic,
    Location,
    Severity,
    SolverDiagnostics,
    ValidationReport,
    Violation,
)
from hydro_shared.hashing import canonical_json, sha256_of, short_hash


class TestCanonicalisation:
    def test_ordre_des_cles_sans_effet(self):
        a = {"b": 1, "a": 2, "c": {"z": 1, "y": 2}}
        b = {"c": {"y": 2, "z": 1}, "a": 2, "b": 1}
        assert canonical_json(a) == canonical_json(b)
        assert sha256_of(a) == sha256_of(b)

    def test_empreinte_stable_entre_appels(self):
        payload = {"flow_m3_s": 1.4204, "segments": [1, 2, 3]}
        assert sha256_of(payload) == sha256_of(payload)

    def test_entrees_differentes_empreintes_differentes(self):
        assert sha256_of({"q": 1.0}) != sha256_of({"q": 1.0000001})

    def test_dernier_bit_de_mantisse_ignore(self):
        """Une différence sous la précision d'un float64 ne change pas l'empreinte."""
        base = 1.0 / 3.0
        assert sha256_of({"x": base}) == sha256_of({"x": base + 1e-18})

    def test_non_finis_serialises_explicitement(self):
        assert '"NaN"' in canonical_json({"x": math.nan})
        assert '"Infinity"' in canonical_json({"x": math.inf})
        assert '"-Infinity"' in canonical_json({"x": -math.inf})

    def test_dataclass_supportee(self):
        @dataclass
        class Entree:
            debit: float
            libelle: str

        assert sha256_of(Entree(1.0, "essai")) == sha256_of({"debit": 1.0, "libelle": "essai"})

    def test_enum_serialise_par_valeur(self):
        assert canonical_json(SimulationStatus.CONVERGED) == '"SIM_CONVERGED"'

    def test_type_non_serialisable_rejete(self):
        with pytest.raises(TypeError):
            canonical_json({"x": object()})

    def test_short_hash(self):
        assert len(short_hash(sha256_of({"a": 1}))) == 12


class TestStatuts:
    def test_statuts_terminaux(self):
        assert not SimulationStatus.QUEUED.is_terminal
        assert not SimulationStatus.RUNNING.is_terminal
        assert SimulationStatus.CONVERGED.is_terminal
        assert SimulationStatus.NOT_CONVERGED.is_terminal

    def test_seuls_les_statuts_converges_portent_des_resultats(self):
        assert SimulationStatus.CONVERGED.has_results
        assert SimulationStatus.CONVERGED_WARN.has_results
        assert not SimulationStatus.NOT_CONVERGED.has_results
        assert not SimulationStatus.NO_PHYSICAL_SOLUTION.has_results

    def test_les_douze_controles_obligatoires_sont_declares(self):
        """§ 5.8 : les contrôles C-001 à C-012 doivent tous être répertoriés."""
        assert sorted(MANDATORY_CHECKS) == [f"C-{i:03d}" for i in range(1, 13)]

    def test_codes_stables(self):
        assert ErrorCode.UNIT_UNKNOWN.value == "ERR_UNIT_UNKNOWN"
        assert ViolationCode.CAVITATION.value == "VIOL_CAVITATION"
        assert WarningCode.EXTRAPOLATION.value == "WARN_EXTRAPOLATION"


class TestViolations:
    def test_ecart_et_ecart_relatif(self):
        v = Violation(
            code=ViolationCode.PRESSURE_HIGH,
            severity=Severity.CRITICAL,
            message="Pression maximale dépassée",
            value=8.4e6,
            limit=8.0e6,
            unit="Pa",
            check_id="C-004",
        )
        assert v.deviation == pytest.approx(4.0e5)
        assert v.relative_deviation == pytest.approx(0.05)

    def test_ecart_absent_si_limite_manquante(self):
        v = Violation(
            code=ViolationCode.MASS_BALANCE,
            severity=Severity.CRITICAL,
            message="Bilan de masse",
        )
        assert v.deviation is None
        assert v.relative_deviation is None

    def test_localisation_lisible(self):
        loc = Location(object_type="edge", object_id="e1", object_label="Tronçon 3", chainage_m=125_000.0)
        described = loc.describe()
        assert "Tronçon 3" in described
        assert "125.000 km" in described


class TestValidationReport:
    def test_rapport_vide_est_valide(self):
        report = ValidationReport()
        assert report.is_valid
        assert report.severity is Severity.INFO

    def test_une_violation_critique_invalide_le_rapport(self):
        report = ValidationReport()
        report.add_violation(
            Violation(
                code=ViolationCode.CAVITATION,
                severity=Severity.CRITICAL,
                message="NPSH insuffisant",
                check_id="C-003",
            )
        )
        assert not report.is_valid
        assert report.severity is Severity.CRITICAL

    def test_un_avertissement_ne_bloque_pas(self):
        report = ValidationReport()
        report.add_warning(
            Diagnostic(code=WarningCode.EXTRAPOLATION, message="Propriété extrapolée")
        )
        assert report.is_valid
        assert report.severity is Severity.WARNING

    def test_extend_fusionne(self):
        a = ValidationReport()
        a.add_warning(Diagnostic(code=WarningCode.NEAR_LIMIT, message="proche limite"))
        b = ValidationReport()
        b.add_error(
            Violation(
                code=ViolationCode.POWER, severity=Severity.CRITICAL, message="puissance dépassée"
            )
        )
        a.extend(b)
        assert not a.is_valid
        assert len(a.warnings) == 1
        assert len(a.errors) == 1


class TestSolverDiagnostics:
    def test_bilan_de_masse_hors_tolerance_detecte(self):
        """NFR-SCI-005 : un bilan hors tolérance interdit de déclarer le résultat valide."""
        diag = SolverDiagnostics(
            method="newton", converged=True, mass_balance_residual=1e-3, mass_balance_tolerance=1e-6
        )
        assert not diag.mass_balance_ok

    def test_bilan_absent_est_non_applicable(self):
        assert SolverDiagnostics(method="analytique").mass_balance_ok

    def test_journal_d_iterations(self):
        diag = SolverDiagnostics(method="brent")
        diag.record_iteration(1, residual=1e-2, flow=1.2)
        diag.record_iteration(2, residual=1e-5, flow=1.42)
        assert diag.as_dict()["iteration_count_logged"] == 2
        assert diag.iteration_log[1]["residual"] == pytest.approx(1e-5)
