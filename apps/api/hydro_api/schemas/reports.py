"""Contrats de génération des rapports opérationnels du MVP."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

OperationalReportType = Literal[
    "project_sheet",
    "scenario_comparison",
    "station_pumps",
    "transfer_simulation",
    "material_balance",
]


class OperationalReportCreate(BaseModel):
    """Sélection explicite du modèle RPT et de sa ressource source."""

    report_type: OperationalReportType
    source_id: uuid.UUID
    template_version: str | None = Field(default=None, min_length=1, max_length=50)
    locale: Literal["fr"] = "fr"

    @model_validator(mode="after")
    def set_default_template(self) -> OperationalReportCreate:
        if self.template_version is None:
            versions = {
                "project_sheet": "rpt-01/1.0",
                "scenario_comparison": "rpt-03/1.0",
                "station_pumps": "rpt-04/1.0",
                "transfer_simulation": "rpt-05/1.0",
                "material_balance": "rpt-06/1.0",
            }
            self.template_version = versions[self.report_type]
        return self


__all__ = ["OperationalReportCreate", "OperationalReportType"]
