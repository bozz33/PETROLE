from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from hydro_api.errors import ResourceConflictError
from hydro_api.industrial.time_series_projection import IndustrialBatchSample, ingest_industrial_batch
from hydro_api.models import MeasurementTag, Organization, SampleNormalized, SampleRaw, Site

_SOURCE_HASH = "sha256:" + "a" * 64
_TIMESTAMP = datetime(2026, 8, 11, 5, 45, tzinfo=UTC)


def _tag(session: Session) -> MeasurementTag:
    organization = Organization(
        name="Opérateur industriel",
        slug="operateur-industriel",
        default_locale="fr",
        default_unit_system="SI",
    )
    session.add(organization)
    session.flush()
    site = Site(
        organization_id=organization.id,
        name="Site A",
        code="SITE-A",
        status="active",
    )
    session.add(site)
    session.flush()
    tag = MeasurementTag(
        organization_id=organization.id,
        site_id=site.id,
        asset_instance_id=None,
        external_name="PT-101",
        name="Pression refoulement",
        measurement_type="pressure",
        dimension="pressure",
        source_unit="bar",
        si_unit="Pa",
        source="opcua-site-a",
        status="active",
        metadata_payload={},
    )
    session.add(tag)
    session.flush()
    return tag


def _sample(
    sequence: int,
    value: object,
    *,
    source_unit: str = "bar",
    quality: str = "good",
) -> IndustrialBatchSample:
    return IndustrialBatchSample(
        sequence_number=sequence,
        source_timestamp=_TIMESTAMP,
        server_timestamp=_TIMESTAMP,
        source_value=value,
        source_unit=source_unit,
        quality=quality,  # type: ignore[arg-type]
        source_quality_code=f"opcua:{quality}",
        quality_mapping_ref="mapping://opcua/status-severity/v1",
        raw_payload={"value": value, "status": quality},
    )


def test_industrial_batch_preserves_raw_then_projects_si(pg_session: Session) -> None:
    tag = _tag(pg_session)

    result = ingest_industrial_batch(
        pg_session,
        tag_id=tag.id,
        idempotency_key="opcua-site-a/PT-101/100-101",
        processing_version="industrial-projection/1.0",
        source_hash=_SOURCE_HASH,
        source_ref="opcua://site-a/nsu=urn:site-a;s=PT-101",
        samples=(_sample(100, 10.0), _sample(101, 11.0, quality="bad")),
    )

    assert result.replayed is False
    assert result.row_count == 2
    assert result.accepted_count == 2
    assert result.rejected_count == 0
    raws = list(
        pg_session.scalars(
            select(SampleRaw)
            .where(SampleRaw.time_series_import_id == result.import_id)
            .order_by(SampleRaw.sequence_number)
        )
    )
    normalized = list(
        pg_session.scalars(
            select(SampleNormalized)
            .where(SampleNormalized.time_series_import_id == result.import_id)
            .order_by(SampleNormalized.timestamp, SampleNormalized.id)
        )
    )
    assert len(raws) == 2
    assert all(raw.dataset_id is None and raw.dataset_row_id is None for raw in raws)
    assert raws[0].source_value == 10.0
    assert raws[0].raw_payload["source_payload"] == {"value": 10.0, "status": "good"}
    assert len(normalized) == 2
    assert sorted(sample.value_si for sample in normalized) == pytest.approx([1_000_000.0, 1_100_000.0])
    assert {sample.quality for sample in normalized} == {"good", "bad"}


def test_invalid_projection_keeps_raw_and_records_rejection(pg_session: Session) -> None:
    tag = _tag(pg_session)

    result = ingest_industrial_batch(
        pg_session,
        tag_id=tag.id,
        idempotency_key="opcua-site-a/PT-101/200",
        processing_version="industrial-projection/1.0",
        source_hash=_SOURCE_HASH,
        source_ref="opcua://site-a/PT-101",
        samples=(_sample(200, 145.0, source_unit="psi"),),
    )

    assert result.accepted_count == 0
    assert result.rejected_count == 1
    raw = pg_session.scalar(
        select(SampleRaw).where(SampleRaw.time_series_import_id == result.import_id)
    )
    assert raw is not None
    assert raw.source_value == 145.0
    assert raw.source_unit == "psi"
    assert (
        pg_session.scalar(
            select(SampleNormalized).where(
                SampleNormalized.time_series_import_id == result.import_id
            )
        )
        is None
    )


def test_industrial_batch_replay_is_idempotent(pg_session: Session) -> None:
    tag = _tag(pg_session)
    kwargs = {
        "tag_id": tag.id,
        "idempotency_key": "hist-site-a/PT-101/batch-42",
        "processing_version": "industrial-projection/1.0",
        "source_hash": _SOURCE_HASH,
        "source_ref": "historian://site-a/PT-101",
        "samples": (_sample(42, 9.5),),
    }

    first = ingest_industrial_batch(pg_session, **kwargs)
    replay = ingest_industrial_batch(pg_session, **kwargs)

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.import_id == first.import_id
    raw_count = len(
        list(
            pg_session.scalars(
                select(SampleRaw).where(SampleRaw.time_series_import_id == first.import_id)
            )
        )
    )
    assert raw_count == 1


def test_reusing_batch_key_with_changed_source_is_rejected(pg_session: Session) -> None:
    tag = _tag(pg_session)
    ingest_industrial_batch(
        pg_session,
        tag_id=tag.id,
        idempotency_key="opcua-site-a/PT-101/stable-key",
        processing_version="industrial-projection/1.0",
        source_hash=_SOURCE_HASH,
        source_ref="opcua://site-a/PT-101",
        samples=(_sample(1, 10.0),),
    )

    with pytest.raises(ResourceConflictError, match="autre version ou source"):
        ingest_industrial_batch(
            pg_session,
            tag_id=tag.id,
            idempotency_key="opcua-site-a/PT-101/stable-key",
            processing_version="industrial-projection/2.0",
            source_hash="sha256:" + "b" * 64,
            source_ref="opcua://site-a/PT-101",
            samples=(_sample(1, 10.0),),
        )


def test_duplicate_sequence_inside_batch_is_rejected_before_persistence(pg_session: Session) -> None:
    tag = _tag(pg_session)
    with pytest.raises(ValueError, match="Chaque séquence"):
        ingest_industrial_batch(
            pg_session,
            tag_id=tag.id,
            idempotency_key="opcua-site-a/PT-101/duplicate",
            processing_version="industrial-projection/1.0",
            source_hash=_SOURCE_HASH,
            source_ref="opcua://site-a/PT-101",
            samples=(_sample(7, 10.0), _sample(7, 10.1)),
        )
