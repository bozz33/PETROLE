"""Tests de génération et de traçabilité de la note de calcul RPT-02."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

from pypdf import PdfReader
from tests.factories import entree_canonique, pipeline, station_serie

from hydro_reporting import (
    HydraulicReportData,
    OperationalReportData,
    ReportTable,
    build_hydraulic_calculation_pdf,
    build_operational_report_pdf,
)
from hydroliquid import LongDistanceLiquidEngine


def _report_data() -> HydraulicReportData:
    canonical = entree_canonique(conduite=pipeline(stations=(station_serie(),)))
    engine = LongDistanceLiquidEngine()
    result = engine.simulate(canonical)
    result_payload = result.as_dict()
    result_payload["explanation"] = engine.explain(result).as_dict()
    return HydraulicReportData(
        report_id="11111111-1111-1111-1111-111111111111",
        calculation_id="22222222-2222-2222-2222-222222222222",
        project_name="Oléoduc de validation",
        project_code="PL-VAL",
        model_name="Baseline",
        model_version=3,
        scenario_name="Régime nominal",
        generated_at=datetime(2026, 8, 2, 12, 30, tzinfo=UTC),
        input_payload=canonical.as_dict(),
        result_payload=result_payload,
    )


def test_pdf_est_lisible_complet_et_trace():
    content = build_hydraulic_calculation_pdf(_report_data())

    reader = PdfReader(BytesIO(content))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert content.startswith(b"%PDF-")
    assert len(content) > 50_000
    assert len(reader.pages) >= 4
    assert "NOTE DE CALCUL" in extracted
    assert "PL-VAL" in extracted
    assert "Traçabilité et reproductibilité" in extracted
    assert "Méthode numérique" in extracted
    assert "Contrôles et marges" in extracted
    assert "sha256:" in extracted
    assert "Vérification ingénieur requise" in extracted


def test_pdf_est_binaire_deterministe_pour_les_memes_entrees():
    data = _report_data()

    assert build_hydraulic_calculation_pdf(data) == build_hydraulic_calculation_pdf(data)


def test_rapport_operationnel_est_lisible_et_deterministe():
    data = OperationalReportData(
        code="RPT-05",
        title="Simulation de transfert",
        subject="Évolution vérifiable d'un transfert entre deux réservoirs.",
        generated_at=datetime(2026, 8, 2, 12, 30, tzinfo=UTC),
        reference="33333333-3333-3333-3333-333333333333",
        template_version="rpt-05/1.0",
        metadata={"Bac source": "TK-101", "Bac destination": "TK-102"},
        key_values=(("Volume soutiré m³", 1250.5), ("Objectif atteint", True)),
        tables=(
            ReportTable(
                title="Échantillons temporels",
                headers=("Temps s", "Niveau source m", "Niveau destination m"),
                rows=((0, 8.5, 2.0), (3600, 7.1, 3.4)),
            ),
        ),
        observations=("Le résidu du bilan reste inférieur à la tolérance.",),
    )

    first = build_operational_report_pdf(data)
    second = build_operational_report_pdf(data)
    reader = PdfReader(BytesIO(first))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert first == second
    assert first.startswith(b"%PDF-")
    assert "RPT-05" in extracted
    assert "Simulation de transfert" in extracted
    assert "Échantillons temporels" in extracted
    assert "validation de l'ingénieur" in extracted.lower()
