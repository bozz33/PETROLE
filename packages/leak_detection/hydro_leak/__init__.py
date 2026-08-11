"""Fondations d'évaluation de la détection de fuite PETROLE."""

from hydro_leak.digital_twin import (
    DigitalTwinSnapshot,
    TwinStateVariable,
    build_twin_snapshot,
    state_delta,
)
from hydro_leak.event_matching import (
    EventMatchingPolicy,
    EventMatchingResult,
    LeakAlertObservation,
    LeakEventLabel,
    MatchedLeakEvent,
    match_alerts_to_events,
)
from hydro_leak.evidence_fusion import (
    EvidenceContribution,
    EvidenceFusionResult,
    EvidenceSignal,
    fuse_evidence,
)
from hydro_leak.localization import LeakLocationEstimate
from hydro_leak.material_balance import (
    MaterialBalanceResult,
    MaterialBalanceWindow,
    compute_material_balance,
)
from hydro_leak.metrics import DetectionPerformance, detection_performance
from hydro_leak.residuals import (
    MeasurementModelResidual,
    MeasurementModelResidualInput,
    compute_measurement_model_residual,
)

__all__ = [
    "DetectionPerformance",
    "DigitalTwinSnapshot",
    "EventMatchingPolicy",
    "EventMatchingResult",
    "EvidenceContribution",
    "EvidenceFusionResult",
    "EvidenceSignal",
    "LeakAlertObservation",
    "LeakEventLabel",
    "LeakLocationEstimate",
    "MatchedLeakEvent",
    "MaterialBalanceResult",
    "MaterialBalanceWindow",
    "MeasurementModelResidual",
    "MeasurementModelResidualInput",
    "TwinStateVariable",
    "build_twin_snapshot",
    "compute_material_balance",
    "compute_measurement_model_residual",
    "detection_performance",
    "fuse_evidence",
    "match_alerts_to_events",
    "state_delta",
]
