"""Porte documentaire avant publication pilote des capacités P3-D/P3-E.

Le contrat Phase 3 impose sept conditions avant qu'une prévision analytique ou
un indicateur de maintenance conditionnelle soit publiable sur un pilote. Ce
module vérifie uniquement les preuves déclarées ; il ne déduit jamais qu'une
condition scientifique, métier ou ingénieur est satisfaite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class AnalyticsPublicationRequirement(StrEnum):
    FIELD_DATA_SUFFICIENT = "field_data_sufficient"
    BUSINESS_HORIZON_AGREED = "business_horizon_agreed"
    NAIVE_BASELINE_DOCUMENTED = "naive_baseline_documented"
    SPLIT_PROTOCOL_FROZEN = "train_validation_test_protocol_frozen"
    METRICS_PREDECLARED = "metrics_chosen_before_test_observation"
    CONDITIONAL_THRESHOLDS_APPROVED = "conditional_thresholds_justified_and_approved"
    ENGINEER_REVIEW_COMPLETED = "engineer_review_variables_and_limits"


_REQUIRED: tuple[AnalyticsPublicationRequirement, ...] = (
    AnalyticsPublicationRequirement.FIELD_DATA_SUFFICIENT,
    AnalyticsPublicationRequirement.BUSINESS_HORIZON_AGREED,
    AnalyticsPublicationRequirement.NAIVE_BASELINE_DOCUMENTED,
    AnalyticsPublicationRequirement.SPLIT_PROTOCOL_FROZEN,
    AnalyticsPublicationRequirement.METRICS_PREDECLARED,
    AnalyticsPublicationRequirement.CONDITIONAL_THRESHOLDS_APPROVED,
    AnalyticsPublicationRequirement.ENGINEER_REVIEW_COMPLETED,
)


@dataclass(frozen=True, slots=True)
class AnalyticsPublicationEvidence:
    """Preuve externe attachée à une exigence de la porte Phase 3."""

    requirement: AnalyticsPublicationRequirement
    satisfied: bool
    evidence_ref: str
    protocol_or_decision_ref: str
    observed_at: datetime
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence_ref.strip() or not self.protocol_or_decision_ref.strip():
            raise ValueError("La preuve et le protocole/décision de publication sont obligatoires.")
        if self.observed_at.tzinfo is None:
            raise ValueError("La date de preuve de publication doit être timezone-aware.")
        if self.note is not None and not self.note.strip():
            raise ValueError("Une note de publication fournie ne peut pas être vide.")

    @property
    def observed_at_utc(self) -> datetime:
        return self.observed_at.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AnalyticsPublicationRequirementAssessment:
    requirement: AnalyticsPublicationRequirement
    satisfied: bool
    evidence_ref: str | None
    protocol_or_decision_ref: str | None
    observed_at: datetime | None
    note: str | None


@dataclass(frozen=True, slots=True)
class AnalyticsPublicationAssessment:
    """Verdict documentaire ; il ne constitue pas une validation industrielle."""

    publishable_for_pilot: bool
    requirements: tuple[AnalyticsPublicationRequirementAssessment, ...]
    blocking_requirements: tuple[AnalyticsPublicationRequirement, ...]


def assess_analytics_publication_gate(
    evidence: tuple[AnalyticsPublicationEvidence, ...],
) -> AnalyticsPublicationAssessment:
    """Exige une preuve positive pour chacune des sept conditions Phase 3."""

    by_requirement: dict[AnalyticsPublicationRequirement, AnalyticsPublicationEvidence] = {}
    for evidence_item in evidence:
        if evidence_item.requirement in by_requirement:
            raise ValueError(
                "Une seule preuve est autorisée par exigence de publication Phase 3 : "
                f"{evidence_item.requirement.value}."
            )
        by_requirement[evidence_item.requirement] = evidence_item

    assessments: list[AnalyticsPublicationRequirementAssessment] = []
    blocking: list[AnalyticsPublicationRequirement] = []
    for requirement in _REQUIRED:
        requirement_evidence = by_requirement.get(requirement)
        if requirement_evidence is None:
            blocking.append(requirement)
            assessments.append(
                AnalyticsPublicationRequirementAssessment(
                    requirement=requirement,
                    satisfied=False,
                    evidence_ref=None,
                    protocol_or_decision_ref=None,
                    observed_at=None,
                    note=None,
                )
            )
            continue

        if not requirement_evidence.satisfied:
            blocking.append(requirement)
        assessments.append(
            AnalyticsPublicationRequirementAssessment(
                requirement=requirement,
                satisfied=requirement_evidence.satisfied,
                evidence_ref=requirement_evidence.evidence_ref,
                protocol_or_decision_ref=requirement_evidence.protocol_or_decision_ref,
                observed_at=requirement_evidence.observed_at_utc,
                note=requirement_evidence.note,
            )
        )

    return AnalyticsPublicationAssessment(
        publishable_for_pilot=not blocking,
        requirements=tuple(assessments),
        blocking_requirements=tuple(blocking),
    )


__all__ = [
    "AnalyticsPublicationAssessment",
    "AnalyticsPublicationEvidence",
    "AnalyticsPublicationRequirement",
    "AnalyticsPublicationRequirementAssessment",
    "assess_analytics_publication_gate",
]
