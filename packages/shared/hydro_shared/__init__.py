"""Briques transverses de la plateforme : unités, codes, diagnostics, empreintes et journaux.

Ce paquet ne dépend ni du web, ni de la base de données. Il est utilisable par le noyau
scientifique comme par le backend (D11 § 4, règle de dépendance).
"""

from hydro_shared.codes import (
    ErrorCode,
    SimulationStatus,
    ViolationCode,
    WarningCode,
)
from hydro_shared.diagnostics import (
    Diagnostic,
    Severity,
    SolverDiagnostics,
    ValidationReport,
    Violation,
)
from hydro_shared.errors import (
    DimensionalityMismatchError,
    HydroError,
    InvalidInputError,
    NoPhysicalSolutionError,
    NotConvergedError,
    UnknownUnitError,
)
from hydro_shared.hashing import canonical_json, sha256_of
from hydro_shared.units import (
    UNIT_REGISTRY,
    Dimension,
    Measure,
    convert,
    format_si,
    si_unit_for,
    to_si,
)
from hydro_shared.versioning import ENGINE_VERSION, PLATFORM_VERSION, engine_fingerprint

__all__ = [
    "ENGINE_VERSION",
    "PLATFORM_VERSION",
    "UNIT_REGISTRY",
    "Diagnostic",
    "Dimension",
    "DimensionalityMismatchError",
    "ErrorCode",
    "HydroError",
    "InvalidInputError",
    "Measure",
    "NoPhysicalSolutionError",
    "NotConvergedError",
    "Severity",
    "SimulationStatus",
    "SolverDiagnostics",
    "UnknownUnitError",
    "ValidationReport",
    "Violation",
    "ViolationCode",
    "WarningCode",
    "canonical_json",
    "convert",
    "engine_fingerprint",
    "format_si",
    "sha256_of",
    "si_unit_for",
    "to_si",
]
