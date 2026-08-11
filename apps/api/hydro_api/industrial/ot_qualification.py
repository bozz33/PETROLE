"""Gate documentaire OT-0 à OT-5 défini par D15.

Ce module n'exécute aucune connexion industrielle et ne transforme pas une
preuve de test en certification. Il vérifie uniquement que les étapes requises
possèdent une preuve référencée et un résultat observé explicitement déclaré.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class OtQualificationStage(StrEnum):
    """Étapes read-only de la feuille de route OT D15."""

    OT_0 = "OT-0"
    OT_1 = "OT-1"
    OT_2 = "OT-2"
    OT_3 = "OT-3"
    OT_4 = "OT-4"
    OT_5 = "OT-5"


_STAGE_ORDER: tuple[OtQualificationStage, ...] = (
    OtQualificationStage.OT_0,
    OtQualificationStage.OT_1,
    OtQualificationStage.OT_2,
    OtQualificationStage.OT_3,
    OtQualificationStage.OT_4,
    OtQualificationStage.OT_5,
)

_STAGE_LABELS: dict[OtQualificationStage, str] = {
    OtQualificationStage.OT_0: "Atelier opérateur : architecture, protocoles, politiques",
    OtQualificationStage.OT_1: "POC hors ligne sur simulateur OPC UA",
    OtQualificationStage.OT_2: "Passerelle en laboratoire et tests de sécurité",
    OtQualificationStage.OT_3: "Connexion à une réplique/historian de test",
    OtQualificationStage.OT_4: "Pilote en lecture seule en DMZ",
    OtQualificationStage.OT_5: "Qualification disponibilité et données",
}


class OtGateStatus(StrEnum):
    MISSING = "missing"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OtStageEvidence:
    """Résultat observé d'une étape selon un protocole externe référencé."""

    stage: OtQualificationStage
    evidence_ref: str
    protocol_ref: str
    environment_ref: str
    observed_at: datetime
    passed: bool
    findings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        references = (self.evidence_ref, self.protocol_ref, self.environment_ref)
        if any(not value.strip() for value in references):
            raise ValueError("Preuve, protocole et environnement OT sont obligatoires.")
        if self.observed_at.tzinfo is None:
            raise ValueError("La date d'observation OT doit être timezone-aware.")
        if any(not finding.strip() for finding in self.findings):
            raise ValueError("Une observation OT ne peut contenir de finding vide.")

    @property
    def observed_at_utc(self) -> datetime:
        return self.observed_at.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class OtStageAssessment:
    stage: OtQualificationStage
    label: str
    status: OtGateStatus
    evidence_ref: str | None
    protocol_ref: str | None
    environment_ref: str | None
    observed_at: datetime | None
    findings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OtQualificationAssessment:
    """État du gate demandé, sans conclusion réglementaire ou de sûreté."""

    target_stage: OtQualificationStage
    passed: bool
    stages: tuple[OtStageAssessment, ...]
    blocking_stages: tuple[OtQualificationStage, ...]


def required_stages_through(target_stage: OtQualificationStage) -> tuple[OtQualificationStage, ...]:
    """Retourne la séquence D15 depuis OT-0 jusqu'à la cible incluse."""

    target_index = _STAGE_ORDER.index(target_stage)
    return _STAGE_ORDER[: target_index + 1]


def assess_ot_qualification(
    evidence: tuple[OtStageEvidence, ...],
    *,
    target_stage: OtQualificationStage = OtQualificationStage.OT_5,
) -> OtQualificationAssessment:
    """Évalue la présence et le résultat des preuves jusqu'à une étape cible."""

    by_stage: dict[OtQualificationStage, OtStageEvidence] = {}
    for item in evidence:
        if item.stage in by_stage:
            raise ValueError(f"Une seule preuve OT est autorisée par étape : {item.stage.value}.")
        by_stage[item.stage] = item

    assessments: list[OtStageAssessment] = []
    blocking: list[OtQualificationStage] = []
    for stage in required_stages_through(target_stage):
        item = by_stage.get(stage)
        if item is None:
            status = OtGateStatus.MISSING
            blocking.append(stage)
            assessments.append(
                OtStageAssessment(
                    stage=stage,
                    label=_STAGE_LABELS[stage],
                    status=status,
                    evidence_ref=None,
                    protocol_ref=None,
                    environment_ref=None,
                    observed_at=None,
                    findings=(),
                )
            )
            continue

        status = OtGateStatus.PASSED if item.passed else OtGateStatus.FAILED
        if status is OtGateStatus.FAILED:
            blocking.append(stage)
        assessments.append(
            OtStageAssessment(
                stage=stage,
                label=_STAGE_LABELS[stage],
                status=status,
                evidence_ref=item.evidence_ref,
                protocol_ref=item.protocol_ref,
                environment_ref=item.environment_ref,
                observed_at=item.observed_at_utc,
                findings=item.findings,
            )
        )

    return OtQualificationAssessment(
        target_stage=target_stage,
        passed=not blocking,
        stages=tuple(assessments),
        blocking_stages=tuple(blocking),
    )


__all__ = [
    "OtGateStatus",
    "OtQualificationAssessment",
    "OtQualificationStage",
    "OtStageAssessment",
    "OtStageEvidence",
    "assess_ot_qualification",
    "required_stages_through",
]
