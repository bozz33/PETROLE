from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

from pypdf import PdfReader

from hydro_optimization.calibration import (
    CalibratedParameter,
    CalibrationResult,
    ErrorMetrics,
)
from hydro_reporting.calibration import CalibrationReportData, build_calibration_report_pdf


def test_rpt08_contains_split_metrics_and_non_certification_status() -> None:
    result = CalibrationResult(
        parameters=(
            CalibratedParameter(
                name="roughness_m",
                value=4.5e-5,
                lower_bound=1.0e-5,
                upper_bound=1.0e-4,
                unit="m",
            ),
        ),
        calibration_metrics=ErrorMetrics(
            sample_count=12,
            mae_si=1200.0,
            rmse_si=1500.0,
            bias_si=-300.0,
            maximum_absolute_error_si=2600.0,
        ),
        validation_metrics=ErrorMetrics(
            sample_count=5,
            mae_si=1600.0,
            rmse_si=1900.0,
            bias_si=450.0,
            maximum_absolute_error_si=3100.0,
        ),
        validation_regimes=("high-flow",),
        converged=True,
        function_evaluations=17,
        termination_message="convergence test",
    )
    pdf = build_calibration_report_pdf(
        CalibrationReportData(
            generated_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            reference="CAL-TEST-001",
            source_reference="dataset://pilot/test-001",
            calibration_regimes=("low-flow", "medium-flow"),
            result=result,
        )
    )

    assert pdf.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "RPT-08" in text
    assert "Calibration et validation tenue à part" in text
    assert "IMPLEMENTED_NOT_FIELD_VALIDATED" in text
    assert "roughness_m" in text
    assert "high-flow" in text
    assert "convergence numérique" in text.lower()
