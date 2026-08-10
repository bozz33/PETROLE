"""Routes Phase 3 — analytics de séries temporelles."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from hydro_api.database.session import get_session
from hydro_api.schemas.analytics import TimeSeriesAnalyticsRead
from hydro_api.schemas.time_series import SampleQuality
from hydro_api.services import analytics

router = APIRouter(tags=["Analytics"])
DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]


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
):
    """Retourne des agrégats UTC sans réécrire ni interpoler les mesures."""

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


__all__ = ["router"]
