"""Modèles SQLAlchemy exposés à Alembic et aux services."""

from typing import cast

from sqlalchemy import Table

from hydro_api.models.catalog import CatalogItem
from hydro_api.models.constraints import (
    align_calculation_status_constraint,
    align_industrial_dataset_nullability,
)
from hydro_api.models.core import (
    AuditEvent,
    BackgroundJob,
    CalculationRun,
    Dataset,
    DatasetImport,
    DatasetRow,
    GeneratedReport,
    MeasurementComparison,
    MeasurementModelMapping,
    MeasurementResidual,
    MeasurementTag,
    ModelVersion,
    OptimizationRun,
    Organization,
    OrganizationMembership,
    Project,
    RefreshSession,
    SampleNormalized,
    SampleRaw,
    ScenarioComparison,
    ScenarioRecord,
    Site,
    StoredFile,
    TankRecord,
    TimeSeriesImport,
    TransferRun,
    UserAccount,
)
from hydro_api.models.governance import (
    RuleDefinition,
    RuleEvaluation,
    RuleSet,
    RuleSetStandard,
    StandardReference,
)
from hydro_api.models.network import AssetInstance, NetworkEdge, NetworkNode

# Les adaptations de métadonnées sont appliquées avant qu'Alembic ou les
# services n'utilisent Base.metadata. Elles maintiennent une source de vérité
# commune entre contrat API, modèle SQLAlchemy et migrations.
align_calculation_status_constraint(cast("Table", CalculationRun.__table__))
align_industrial_dataset_nullability(
    cast("Table", TimeSeriesImport.__table__),
    cast("Table", SampleRaw.__table__),
    cast("Table", MeasurementResidual.__table__),
)

__all__ = [
    "AssetInstance",
    "AuditEvent",
    "BackgroundJob",
    "CalculationRun",
    "CatalogItem",
    "Dataset",
    "DatasetImport",
    "DatasetRow",
    "GeneratedReport",
    "MeasurementComparison",
    "MeasurementModelMapping",
    "MeasurementResidual",
    "MeasurementTag",
    "ModelVersion",
    "NetworkEdge",
    "NetworkNode",
    "OptimizationRun",
    "Organization",
    "OrganizationMembership",
    "Project",
    "RefreshSession",
    "RuleDefinition",
    "RuleEvaluation",
    "RuleSet",
    "RuleSetStandard",
    "SampleNormalized",
    "SampleRaw",
    "ScenarioComparison",
    "ScenarioRecord",
    "Site",
    "StandardReference",
    "StoredFile",
    "TankRecord",
    "TimeSeriesImport",
    "TransferRun",
    "UserAccount",
]
