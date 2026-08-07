"""Tests du dossier de validation scientifique exécutable."""

from __future__ import annotations

import json

import pytest

from hydro_api.routers.health import published_scientific_validation
from hydro_shared.versioning import ENGINE_VERSION
from hydro_validation.cli import main
from hydro_validation.runner import render_markdown, run_validation_suite, select_cases


@pytest.mark.scientific
def test_all_registered_validation_cases_pass() -> None:
    result = run_validation_suite()

    assert len(result.cases) == 41
    assert result.passed
    assert result.passed_count == 41
    assert result.failed_count == 0
    assert len(result.sha256) == 64
    assert len(result.proof_hash) == 64


@pytest.mark.scientific
def test_empreinte_des_resultats_est_reproductible() -> None:
    """Deux exécutions du même code produisent la même empreinte de résultats."""

    premiere = run_validation_suite()
    seconde = run_validation_suite()

    assert premiere.proof_hash == seconde.proof_hash
    # L'empreinte d'exécution intègre l'horodatage : elle ne peut pas coïncider.
    assert premiere.sha256 != seconde.sha256


@pytest.mark.scientific
def test_attestation_publiee_correspond_a_une_execution_reelle() -> None:
    """L'attestation servie par l'API doit refléter la suite réellement exécutée.

    Ce contrôle interdit toute valeur figée à la main dans le fichier publié avec
    l'image : un écart de comptage, de moteur ou d'empreinte fait échouer la
    qualification avant la mise en production.
    """

    publiee = published_scientific_validation()
    result = run_validation_suite()

    assert publiee.suite == "scientific-validation"
    assert publiee.passed == result.passed_count
    assert publiee.total == len(result.cases)
    assert publiee.proof_hash == result.proof_hash
    assert publiee.engine_version == ENGINE_VERSION


def test_case_selection_accepts_shell_patterns() -> None:
    selected = select_cases(["val-pmp-*"])

    assert len(selected) == 5
    assert all(case.id.startswith("VAL-PMP-") for case in selected)


def test_porte_scientifique_mvp_couvre_v001_a_v020() -> None:
    selected = select_cases(["V-*"])

    assert [case.id for case in selected] == [f"V-{index:03d}" for index in range(1, 21)]
    result = run_validation_suite(["V-*"])
    assert result.passed
    assert result.passed_count == 20


def test_benchmarks_externes_sont_tous_reproductibles() -> None:
    result = run_validation_suite(["EXT-*"])

    assert len(result.cases) == 7
    assert result.passed
    transition = next(case for case in result.cases if case.case_id == "EXT-PP-STANET-01")
    assert "Écart de modèle B" in transition.observations[0].detail


def test_markdown_report_contains_traceability() -> None:
    result = run_validation_suite(["VAL-LIQ-001"])
    report = render_markdown(result)

    assert "Rapport de validation scientifique" in report
    assert "VAL-LIQ-001" in report
    assert result.sha256 in report
    assert "Ce rapport prouve uniquement" in report


def test_cli_writes_markdown_and_json_evidence(tmp_path, capsys) -> None:
    report_path = tmp_path / "rapport.md"
    json_path = tmp_path / "preuve.json"

    exit_code = main(
        [
            "--case",
            "VAL-PMP-*",
            "--report",
            str(report_path),
            "--json",
            str(json_path),
        ]
    )

    assert exit_code == 0
    assert "Validation VALIDÉ" in capsys.readouterr().out
    assert "VAL-PMP-002" in report_path.read_text(encoding="utf-8")
    evidence = json.loads(json_path.read_text(encoding="utf-8"))
    assert evidence["passed"] is True
    assert evidence["passed_count"] == 5
    assert len(evidence["sha256"]) == 64


def test_cli_returns_two_when_selection_is_empty(capsys) -> None:
    exit_code = main(["--case", "VAL-INCONNU-*"])

    assert exit_code == 2
    assert "Aucun cas" in capsys.readouterr().out
