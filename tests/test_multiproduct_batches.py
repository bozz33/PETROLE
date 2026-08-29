from __future__ import annotations

import pytest

from hydro_transients import ProductBatch, build_batch_sequence


def _batch(batch_id: str, product_ref: str, volume_m3: float) -> ProductBatch:
    return ProductBatch(
        batch_id=batch_id,
        product_ref=product_ref,
        volume_m3=volume_m3,
        source_ref=f"schedule://{batch_id}",
    )


def test_batch_sequence_builds_cumulative_interfaces_without_hidden_mixing_volume() -> None:
    sequence = build_batch_sequence(
        (
            _batch("B01", "product://diesel", 1_000.0),
            _batch("B02", "product://gasoline", 500.0),
            _batch("B03", "product://jet-a1", 750.0),
        )
    )

    assert sequence.total_volume_m3 == pytest.approx(2_250.0)
    assert len(sequence.interfaces) == 2
    assert sequence.interfaces[0].upstream_batch_id == "B01"
    assert sequence.interfaces[0].downstream_batch_id == "B02"
    assert sequence.interfaces[0].cumulative_volume_m3 == pytest.approx(1_000.0)
    assert sequence.interfaces[1].cumulative_volume_m3 == pytest.approx(1_500.0)


def test_single_batch_has_no_interface() -> None:
    sequence = build_batch_sequence((_batch("B01", "product://diesel", 100.0),))
    assert sequence.interfaces == ()
    assert sequence.total_volume_m3 == pytest.approx(100.0)


def test_batch_sequence_rejects_duplicate_ids_and_non_positive_volume() -> None:
    duplicate = _batch("B01", "product://diesel", 100.0)
    with pytest.raises(ValueError, match="uniques"):
        build_batch_sequence((duplicate, duplicate))

    with pytest.raises(ValueError, match="strictement positif"):
        _batch("B02", "product://gasoline", 0.0)
