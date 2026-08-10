"""Fondations scientifiques du domaine gaz PETROLE.

Le paquet est volontairement séparé de ``hydroliquid`` : un réseau gaz ne doit
pas être modélisé en remplaçant simplement la densité d'un liquide.
"""

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
from hydro_gas.coolprop_adapter import (
    CoolPropEvaluationEnvelope,
    CoolPropPropertyResult,
    CoolPropPureFluidDefinition,
    evaluate_coolprop_properties,
)
from hydro_gas.properties import GasState, gas_density_from_z, linepack_mass

__all__ = [
    "CompressorEnvelopeAssessment",
    "CompressorFlowLimitPoint",
    "CompressorMap",
    "CompressorMapPoint",
    "CompressorOperatingEnvelope",
    "CompressorOperatingPoint",
    "CompressorSpeedLine",
    "CoolPropEvaluationEnvelope",
    "CoolPropPropertyResult",
    "CoolPropPureFluidDefinition",
    "GasComponentFraction",
    "GasComposition",
    "GasState",
    "assess_compressor_envelope",
    "evaluate_coolprop_properties",
    "gas_density_from_z",
    "interpolate_compressor_map",
    "linepack_mass",
]
