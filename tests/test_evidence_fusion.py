from __future__ import annotations

import pytest

from hydro_leak import EvidenceSignal, fuse_evidence


def test_evidence_fusion_returns_explainable_weighted_score() -> None:
    result = fuse_evidence(
        (
            EvidenceSignal(
                detector_id="material-balance",
                score=0.8,
                weight=2.0,
                source_ref="analysis://balance/window-001",
            ),
            EvidenceSignal(
                detector_id="pressure-residual",
                score=0.2,
                weight=1.0,
                source_ref="analysis://pressure/window-001",
            ),
        )
    )

    assert result.score == pytest.approx(0.6)
    assert result.total_weight == pytest.approx(3.0)
    assert result.contributions[0].normalized_weight == pytest.approx(2.0 / 3.0)
    assert result.contributions[0].contribution == pytest.approx(0.8 * 2.0 / 3.0)
    assert result.contributions[1].contribution == pytest.approx(0.2 / 3.0)


def test_evidence_fusion_rejects_duplicate_detector_contributions() -> None:
    signal = EvidenceSignal(
        detector_id="material-balance",
        score=0.5,
        weight=1.0,
        source_ref="analysis://balance/window-001",
    )
    with pytest.raises(ValueError, match="qu'une fois"):
        fuse_evidence((signal, signal))


def test_evidence_signal_rejects_score_outside_unit_interval() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        EvidenceSignal(
            detector_id="detector",
            score=1.1,
            weight=1.0,
            source_ref="analysis://detector/window-001",
        )
