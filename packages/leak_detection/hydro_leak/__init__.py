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
from hydro_leak.validation_campaign import (
    LeakValidationAssessment,
    LeakValidationCriteria,
    LeakValidationCriterionResult,
    assess_validation_criteria,
)
from hydro_leak.validation_dataset import (
    ExcludedLeakEvent,
    LeakValidationDatasetPartition,
    freeze_leak_validation_dataset,
)

__all__ = [
    "DetectionPerformance",
    "DigitalTwinSnapshot",
    "EventMatchingPolicy",
    "EventMatchingResult",
    "EvidenceContribution",
    "EvidenceFusionResult",
    "EvidenceSignal",
    "ExcludedLeakEvent",
    "LeakAlertObservation",
    "LeakEventLabel",
    "LeakLocationEstimate",
    "LeakValidationAssessment",
    "LeakValidationCriteria",
    "LeakValidationCriterionResult",
    "LeakValidationDatasetPartition",
    "MatchedLeakEvent",
    "MaterialBalanceResult",
    "MaterialBalanceWindow",
    "MeasurementModelResidual",
    "MeasurementModelResidualInput",
    "TwinStateVariable",
    "assess_validation_criteria",
    "build_twin_snapshot",
    "compute_material_balance",
    "compute_measurement_model_residual",
    "detection_performance",
    "freeze_leak_validation_dataset",
    "fuse_evidence",
    "match_alerts_to_events",
    "state_delta",
]
