"""Fondations scientifiques du domaine gaz PETROLE.

Le paquet est volontairement séparé de ``hydroliquid`` : un réseau gaz ne doit
pas être modélisé en remplaçant simplement la densité d'un liquide.
"""

from hydro_gas.benchmark_protocol import (
    ApprovedGasBenchmarkCriteria,
    GasBenchmarkCriterionState,
    GasBenchmarkProtocolContext,
    PreRegisteredGasBenchmarkCriterion,
    materialize_approved_gas_benchmark_criteria,
)
from hydro_gas.composition import GasComponentFraction, GasComposition
from hydro_gas.compressor_limits import (
    CompressorEnvelopeAssessment,
    CompressorFlowLimitPoint,
    CompressorOperatingEnvelope,
    assess_compressor_envelope,
)
from hydro_gas.compressor_map import (
    CompressorMap,
    CompressorMapPoint,
    CompressorOperatingPoint,
    CompressorSpeedLine,
    interpolate_compressor_map,
)
from hydro_gas.constitutive_models import (
    GasConstitutiveManifest,
    GasConstitutiveManifestAssessment,
    GasConstitutiveQualification,
    GasPipeConstitutiveBinding,
    GasPipeConstitutiveModelDescriptor,
    assess_constitutive_manifest,
)
from hydro_gas.coolprop_adapter import (
    CoolPropEvaluationEnvelope,
    CoolPropPropertyResult,
    CoolPropPureFluidDefinition,
    evaluate_coolprop_properties,
)
from hydro_gas.energy_optimization import (
    GasDispatchConstraintEvidence,
    GasEnergyDispatchCandidate,
    GasEnergySelectionResult,
    GasEnergySelectionStatus,
    RankedGasEnergyCandidate,
    RejectedGasEnergyCandidate,
    select_minimum_energy_dispatch,
)
from hydro_gas.linepack import GasLinepackCell, GasLinepackResult, compute_segmented_linepack
from hydro_gas.network_balance import (
    GasBoundaryMassFlow,
    GasNetworkMassBalanceResult,
    GasNodeMassBalance,
    GasPipeMassFlow,
    SteadyGasNetwork,
    SteadyGasNode,
    SteadyGasPipe,
    assess_stationary_mass_balance,
)
from hydro_gas.properties import GasState, gas_density_from_z, linepack_mass
from hydro_gas.result_export import GasResultExportArtifact, export_gas_results_json
from hydro_gas.station import (
    CompressorStationConfiguration,
    CompressorUnitConfiguration,
    CompressorUnitRole,
    StationCoolerConfiguration,
    StationValveConfiguration,
    StationValveRole,
)
from hydro_gas.weymouth_network_residual import (
    GasNodePressure,
    WeymouthNetworkCandidateState,
    WeymouthNetworkResidualAssembly,
    assemble_weymouth_network_residuals,
)
from hydro_gas.weymouth_parameter_artifact import (
    WEYMOUTH_SI_MODEL_ID,
    WEYMOUTH_SI_MODEL_VERSION,
    WEYMOUTH_SI_PARAMETER_SCHEMA_VERSION,
    WeymouthSiParameterArtifact,
    build_weymouth_si_binding,
    export_weymouth_si_parameter_artifact,
    weymouth_si_reference_descriptor,
)
from hydro_gas.weymouth_si import (
    WeymouthSiObservation,
    WeymouthSiPipeParameters,
    WeymouthSiResidual,
    evaluate_weymouth_si_residual,
)

__all__ = [
    "WEYMOUTH_SI_MODEL_ID",
    "WEYMOUTH_SI_MODEL_VERSION",
    "WEYMOUTH_SI_PARAMETER_SCHEMA_VERSION",
    "ApprovedGasBenchmarkCriteria",
    "CompressorEnvelopeAssessment",
    "CompressorFlowLimitPoint",
    "CompressorMap",
    "CompressorMapPoint",
    "CompressorOperatingEnvelope",
    "CompressorOperatingPoint",
    "CompressorSpeedLine",
    "CompressorStationConfiguration",
    "CompressorUnitConfiguration",
    "CompressorUnitRole",
    "CoolPropEvaluationEnvelope",
    "CoolPropPropertyResult",
    "CoolPropPureFluidDefinition",
    "GasBenchmarkCriterionState",
    "GasBenchmarkProtocolContext",
    "GasBoundaryMassFlow",
    "GasComponentFraction",
    "GasComposition",
    "GasConstitutiveManifest",
    "GasConstitutiveManifestAssessment",
    "GasConstitutiveQualification",
    "GasDispatchConstraintEvidence",
    "GasEnergyDispatchCandidate",
    "GasEnergySelectionResult",
    "GasEnergySelectionStatus",
    "GasLinepackCell",
    "GasLinepackResult",
    "GasNetworkMassBalanceResult",
    "GasNodeMassBalance",
    "GasNodePressure",
    "GasPipeConstitutiveBinding",
    "GasPipeConstitutiveModelDescriptor",
    "GasPipeMassFlow",
    "GasResultExportArtifact",
    "GasState",
    "PreRegisteredGasBenchmarkCriterion",
    "RankedGasEnergyCandidate",
    "RejectedGasEnergyCandidate",
    "StationCoolerConfiguration",
    "StationValveConfiguration",
    "StationValveRole",
    "SteadyGasNetwork",
    "SteadyGasNode",
    "SteadyGasPipe",
    "WeymouthNetworkCandidateState",
    "WeymouthNetworkResidualAssembly",
    "WeymouthSiObservation",
    "WeymouthSiParameterArtifact",
    "WeymouthSiPipeParameters",
    "WeymouthSiResidual",
    "assemble_weymouth_network_residuals",
    "assess_compressor_envelope",
    "assess_constitutive_manifest",
    "assess_stationary_mass_balance",
    "build_weymouth_si_binding",
    "compute_segmented_linepack",
    "evaluate_coolprop_properties",
    "evaluate_weymouth_si_residual",
    "export_gas_results_json",
    "export_weymouth_si_parameter_artifact",
    "gas_density_from_z",
    "interpolate_compressor_map",
    "linepack_mass",
    "materialize_approved_gas_benchmark_criteria",
    "select_minimum_energy_dispatch",
    "weymouth_si_reference_descriptor",
]
