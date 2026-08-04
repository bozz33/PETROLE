"""Modèles SQLAlchemy exposés à Alembic et aux services."""

from typing import cast

from sqlalchemy import Table

from hydro_api.models.catalog import CatalogItem
from hydro_api.models.constraints import align_calculation_status_constraint
from hydro_api.models.core import (
    AuditEvent,
    BackgroundJob,
    CalculationRun,
    Dataset,
    DatasetImport,
    DatasetRow,
    GeneratedReport,
    ModelVersion,
    OptimizationRun,
    Organization,
    OrganizationMembership,
    Project,
    RefreshSession,
    ScenarioComparison,
    ScenarioRecord,
    Site,
    StoredFile,
    TankRecord,
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

# La contrainte de statut est dérivée de l'énumération publique afin d'éviter
# toute divergence entre le contrat API, les métadonnées et les migrations.
# ``CalculationRun.__table__`` est typé ``FromClause`` par SQLAlchemy, mais
# l'objet concret est une ``Table`` à l'exécution ; le ``cast`` explicite le
# garantit sans ``type: ignore``.
align_calculation_status_constraint(cast("Table", CalculationRun.__table__))

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
    "ScenarioComparison",
    "ScenarioRecord",
    "Site",
    "StandardReference",
    "StoredFile",
    "TankRecord",
    "TransferRun",
    "UserAccount",
]
