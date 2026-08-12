"""Routes Phase 3 — analytics de séries temporelles."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from hydro_api.database.session import get_session
from hydro_api.schemas.analytics import TimeSeriesAnalyticsRead
from hydro_api.schemas.time_series import SampleQuality
from hydro_api.services import analytics, analytics_exports

router = APIRouter(tags=["Analytics"])
DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]


def _analyze(
    session: Session,
    *,
    tag_id: uuid.UUID,
    processing_version: str,
    start_timestamp: datetime | None,
    end_timestamp: datetime | None,
    qualities: list[SampleQuality] | None,
    bucket_seconds: int,
    expected_interval_seconds: float | None,
) -> dict[str, Any]:
    return analytics.analyze_time_series(
        session,
        tag_id=tag_id,
        processing_version=processing_version.strip(),
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        qualities=qualities,
        bucket_seconds=bucket_seconds,
        expected_interval_seconds=expected_interval_seconds,
    )


@router.get(
    "/analytics/measurement-tags/{tag_id}/series",
    response_model=TimeSeriesAnalyticsRead,
    summary="Agréger une série temporelle SI et calculer sa tendance descriptive",
)
def analyze_measurement_tag_series(
    tag_id: uuid.UUID,
    session: DatabaseSession,
    processing_version: Annotated[str, Query(min_length=1, max_length=80)],
    start_timestamp: datetime | None = None,
    end_timestamp: datetime | None = None,
    qualities: Annotated[list[SampleQuality] | None, Query()] = None,
    bucket_seconds: Annotated[int, Query(ge=1, le=31_536_000)] = 3600,
    expected_interval_seconds: Annotated[float | None, Query(gt=0)] = None,
) -> dict[str, Any]:
    """Retourne des agrégats UTC sans réécrire ni interpoler les mesures."""

    return _analyze(
        session,
        tag_id=tag_id,
        processing_version=processing_version,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        qualities=qualities,
        bucket_seconds=bucket_seconds,
        expected_interval_seconds=expected_interval_seconds,
    )


@router.get(
    "/analytics/measurement-tags/{tag_id}/series/export.json",
    response_class=Response,
    summary="Exporter l'analyse temporelle en JSON canonique versionné",
)
def export_measurement_tag_series_json(
    tag_id: uuid.UUID,
    session: DatabaseSession,
    processing_version: Annotated[str, Query(min_length=1, max_length=80)],
    start_timestamp: datetime | None = None,
    end_timestamp: datetime | None = None,
    qualities: Annotated[list[SampleQuality] | None, Query()] = None,
    bucket_seconds: Annotated[int, Query(ge=1, le=31_536_000)] = 3600,
    expected_interval_seconds: Annotated[float | None, Query(gt=0)] = None,
) -> Response:
    """Sérialise exactement le résultat analytique sans recalcul supplémentaire."""

    payload = _analyze(
        session,
        tag_id=tag_id,
        processing_version=processing_version,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        qualities=qualities,
        bucket_seconds=bucket_seconds,
        expected_interval_seconds=expected_interval_seconds,
    )
    artifact = analytics_exports.export_analytics_json(payload)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "X-Content-SHA256": artifact.sha256,
        },
    )


@router.get(
    "/analytics/measurement-tags/{tag_id}/series/export.csv",
    response_class=Response,
    summary="Exporter les buckets analytiques en CSV versionné",
)
def export_measurement_tag_series_csv(
    tag_id: uuid.UUID,
    session: DatabaseSession,
    processing_version: Annotated[str, Query(min_length=1, max_length=80)],
    start_timestamp: datetime | None = None,
    end_timestamp: datetime | None = None,
    qualities: Annotated[list[SampleQuality] | None, Query()] = None,
    bucket_seconds: Annotated[int, Query(ge=1, le=31_536_000)] = 3600,
    expected_interval_seconds: Annotated[float | None, Query(gt=0)] = None,
) -> Response:
    """Exporte les buckets tels que calculés par la route d'analyse."""

    payload = _analyze(
        session,
        tag_id=tag_id,
        processing_version=processing_version,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        qualities=qualities,
        bucket_seconds=bucket_seconds,
        expected_interval_seconds=expected_interval_seconds,
    )
    artifact = analytics_exports.export_analytics_buckets_csv(payload)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "X-Content-SHA256": artifact.sha256,
        },
    )


__all__ = ["router"]
