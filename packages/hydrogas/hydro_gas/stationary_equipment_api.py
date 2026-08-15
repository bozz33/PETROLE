"""Façade publique stable du moteur stationnaire gaz + compresseurs actifs.

Les modules internes restent séparés par responsabilité scientifique. Cette
façade fournit un point d'import explicite aux couches API/UI et aux intégrations
sans transformer le paquet racine en registre de détails d'implémentation.
"""

from hydro_gas.compressor_limits import (
    CompressorEnvelopeFlowLimits,
    compressor_envelope_flow_limits_at_speed,
)
from hydro_gas.compressor_map import CompressorMapFlowDomain, compressor_map_flow_domain_at_speed
from hydro_gas.coolprop_compressor_adapter import CoolPropCompressorFluidDefinition
from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryActiveCompressorThermodynamicAssessment,
    StationaryCompressorThermodynamicInput,
    StationaryCompressorThermodynamicResult,
    evaluate_stationary_active_compressor_thermodynamics,
)
from hydro_gas.stationary_equipment_benchmark_adapter import (
    StationaryEquipmentBenchmarkBinding,
    StationaryEquipmentBenchmarkObservationBundle,
    StationaryEquipmentBenchmarkQuantity,
    build_stationary_equipment_benchmark_observations,
)
from hydro_gas.stationary_equipment_benchmark_evidence import (
    STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
    StationaryEquipmentBenchmarkEvidenceArtifact,
    export_stationary_equipment_benchmark_evidence,
)
from hydro_gas.stationary_equipment_bounds import (
    StationaryActiveCompressorNumericalBounds,
    StationaryCompressorFlowBound,
    build_stationary_active_compressor_numerical_bounds,
)
from hydro_gas.stationary_equipment_candidate import (
    StationaryActiveCompressorCandidateState,
    StationaryActiveCompressorUnknownState,
    materialize_stationary_active_compressor_candidate,
)
from hydro_gas.stationary_equipment_evaluation import (
    StationaryActiveCompressorEvaluation,
    evaluate_stationary_active_compressor_unknown_state,
)
from hydro_gas.stationary_equipment_numerical_evaluation import (
    StationaryActiveCompressorNumericalEvaluation,
    evaluate_stationary_active_compressor_numerical_vector,
)
from hydro_gas.stationary_equipment_numerics import (
    StationaryActiveCompressorNumericalScale,
    StationaryActiveCompressorNumericalVector,
    decode_stationary_active_compressor_numerical_vector,
    encode_stationary_active_compressor_residuals,
    encode_stationary_active_compressor_unknown_state,
)
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryActiveCompressorUnknownLayout,
    StationaryCompressorSpeedControl,
    build_stationary_active_compressor_unknown_layout,
)
from hydro_gas.stationary_equipment_residual import (
    StationaryCompressorMapBinding,
    StationaryCompressorOperatingInput,
    StationaryEquipmentResidualAssembly,
    assemble_stationary_equipment_residuals,
)
from hydro_gas.stationary_equipment_result_export import (
    MIXED_STATIONARY_GAS_EXPORT_VERSION,
    MIXED_STATIONARY_GAS_RESULT_MODEL_VERSION,
    export_stationary_active_compressor_solve_result_json,
)
from hydro_gas.stationary_equipment_result_tables import (
    StationaryActiveCompressorResultTables,
    StationaryGasBoundaryResultRow,
    StationaryGasCompressorResultRow,
    StationaryGasNodeResultRow,
    StationaryGasPipeResultRow,
    build_stationary_active_compressor_result_tables,
)
from hydro_gas.stationary_equipment_solver import (
    ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF,
    ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF,
    ScipyActiveCompressorLeastSquaresTrfConfiguration,
    StationaryActiveCompressorConvergenceAssessment,
    StationaryActiveCompressorGovernedSolveResult,
    StationaryActiveCompressorSolveResult,
    assess_stationary_active_compressor_convergence,
    solve_stationary_active_compressor_with_approved_inputs,
)
from hydro_gas.stationary_equipment_solver_governance import (
    ApprovedStationaryEquipmentConvergenceCriterion,
    PreRegisteredStationaryEquipmentConvergenceCriterion,
    materialize_approved_stationary_equipment_convergence_criterion,
)
from hydro_gas.stationary_equipment_solver_inputs import (
    ApprovedStationaryEquipmentInitialGuessArtifact,
    ApprovedStationaryEquipmentScaleArtifact,
    PreRegisteredStationaryEquipmentInitialGuessArtifact,
    PreRegisteredStationaryEquipmentScaleArtifact,
    materialize_approved_stationary_equipment_initial_guess,
    materialize_approved_stationary_equipment_scale,
    stationary_active_compressor_layout_sha256,
)
from hydro_gas.stationary_station_thermodynamics import (
    StationaryCompressorStationThermodynamicSummary,
    aggregate_stationary_compressor_thermodynamics,
)

__all__ = [
    "ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF",
    "ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF",
    "MIXED_STATIONARY_GAS_EXPORT_VERSION",
    "MIXED_STATIONARY_GAS_RESULT_MODEL_VERSION",
    "STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION",
    "ApprovedStationaryEquipmentConvergenceCriterion",
    "ApprovedStationaryEquipmentInitialGuessArtifact",
    "ApprovedStationaryEquipmentScaleArtifact",
    "CompressorEnvelopeFlowLimits",
    "CompressorMapFlowDomain",
    "CoolPropCompressorFluidDefinition",
    "PreRegisteredStationaryEquipmentConvergenceCriterion",
    "PreRegisteredStationaryEquipmentInitialGuessArtifact",
    "PreRegisteredStationaryEquipmentScaleArtifact",
    "ScipyActiveCompressorLeastSquaresTrfConfiguration",
    "StationaryActiveCompressorCandidateState",
    "StationaryActiveCompressorConvergenceAssessment",
    "StationaryActiveCompressorEvaluation",
    "StationaryActiveCompressorGovernedSolveResult",
    "StationaryActiveCompressorNumericalBounds",
    "StationaryActiveCompressorNumericalEvaluation",
    "StationaryActiveCompressorNumericalScale",
    "StationaryActiveCompressorNumericalVector",
    "StationaryActiveCompressorProblem",
    "StationaryActiveCompressorResultTables",
    "StationaryActiveCompressorSolveResult",
    "StationaryActiveCompressorThermodynamicAssessment",
    "StationaryActiveCompressorUnknownLayout",
    "StationaryActiveCompressorUnknownState",
    "StationaryCompressorFlowBound",
    "StationaryCompressorMapBinding",
    "StationaryCompressorOperatingInput",
    "StationaryCompressorSpeedControl",
    "StationaryCompressorStationThermodynamicSummary",
    "StationaryCompressorThermodynamicInput",
    "StationaryCompressorThermodynamicResult",
    "StationaryEquipmentBenchmarkBinding",
    "StationaryEquipmentBenchmarkEvidenceArtifact",
    "StationaryEquipmentBenchmarkObservationBundle",
    "StationaryEquipmentBenchmarkQuantity",
    "StationaryEquipmentResidualAssembly",
    "StationaryGasBoundaryResultRow",
    "StationaryGasCompressorResultRow",
    "StationaryGasNodeResultRow",
    "StationaryGasPipeResultRow",
    "aggregate_stationary_compressor_thermodynamics",
    "assemble_stationary_equipment_residuals",
    "assess_stationary_active_compressor_convergence",
    "build_stationary_active_compressor_numerical_bounds",
    "build_stationary_active_compressor_result_tables",
    "build_stationary_active_compressor_unknown_layout",
    "build_stationary_equipment_benchmark_observations",
    "compressor_envelope_flow_limits_at_speed",
    "compressor_map_flow_domain_at_speed",
    "decode_stationary_active_compressor_numerical_vector",
    "encode_stationary_active_compressor_residuals",
    "encode_stationary_active_compressor_unknown_state",
    "evaluate_stationary_active_compressor_numerical_vector",
    "evaluate_stationary_active_compressor_thermodynamics",
    "evaluate_stationary_active_compressor_unknown_state",
    "export_stationary_active_compressor_solve_result_json",
    "export_stationary_equipment_benchmark_evidence",
    "materialize_approved_stationary_equipment_convergence_criterion",
    "materialize_approved_stationary_equipment_initial_guess",
    "materialize_approved_stationary_equipment_scale",
    "materialize_stationary_active_compressor_candidate",
    "solve_stationary_active_compressor_with_approved_inputs",
    "stationary_active_compressor_layout_sha256",
]
