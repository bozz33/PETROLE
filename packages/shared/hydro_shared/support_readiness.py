"""Contrat P8-I de readiness opérationnelle du support PETROLE.

Cette brique vérifie uniquement que les classes d'incident exigées par un
protocole disposent de runbooks versionnés, de rôles responsables et d'une
matrice d'escalade référencée. Elle ne crée pas une astreinte, ne contacte
personne et ne transforme pas une documentation complète en SLA de production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class IncidentResponsePhase(StrEnum):
    """Phases de réponse structurées par D15 §12."""

    DETECT = "detect"
    CONTAIN = "contain"
    PRESERVE = "preserve"
    ERADICATE = "eradicate"
    RESTORE = "restore"
    LEARN = "learn"
    NOTIFY = "notify"


@dataclass(frozen=True, slots=True)
class SupportRunbookDescriptor:
    """Runbook versionné associé à une classe d'incident précise."""

    incident_class_ref: str
    runbook_ref: str
    version: str
    content_sha256: str
    owner_role_ref: str
    review_ref: str
    reviewed_at: datetime
    covered_phases: tuple[IncidentResponsePhase, ...]

    def __post_init__(self) -> None:
        required = (
            self.incident_class_ref,
            self.runbook_ref,
            self.version,
            self.owner_role_ref,
            self.review_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Classe incident, runbook, version, rôle responsable et revue sont obligatoires."
            )
        normalized_sha = self.content_sha256.strip().lower()
        if not _SHA256_RE.fullmatch(normalized_sha):
            raise ValueError("Le runbook doit avoir une empreinte SHA-256 hexadécimale complète.")
        object.__setattr__(self, "content_sha256", normalized_sha)
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("La date de revue du runbook doit être timezone-aware.")
        object.__setattr__(self, "reviewed_at", self.reviewed_at.astimezone(UTC))
        phases = tuple(dict.fromkeys(self.covered_phases))
        if not phases:
            raise ValueError("Un runbook doit déclarer au moins une phase de réponse couverte.")
        object.__setattr__(self, "covered_phases", phases)


@dataclass(frozen=True, slots=True)
class IncidentClassRequirement:
    """Couverture minimale fournie par le protocole/opérateur pour une classe."""

    incident_class_ref: str
    required_phases: tuple[IncidentResponsePhase, ...]
    requirement_source_ref: str

    def __post_init__(self) -> None:
        if not self.incident_class_ref.strip() or not self.requirement_source_ref.strip():
            raise ValueError("La classe incident et la provenance de l'exigence sont obligatoires.")
        phases = tuple(dict.fromkeys(self.required_phases))
        if not phases:
            raise ValueError("Une classe d'incident doit exiger au moins une phase de réponse.")
        object.__setattr__(self, "required_phases", phases)


@dataclass(frozen=True, slots=True)
class SupportOrganizationEvidence:
    """Références organisationnelles, sans stocker de données personnelles."""

    support_policy_ref: str
    escalation_matrix_ref: str
    contact_roster_ref: str
    maintenance_policy_ref: str
    evidence_archive_ref: str

    def __post_init__(self) -> None:
        required = (
            self.support_policy_ref,
            self.escalation_matrix_ref,
            self.contact_roster_ref,
            self.maintenance_policy_ref,
            self.evidence_archive_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Politique support, escalade, contacts, maintenance et archive de preuve sont obligatoires."
            )


@dataclass(frozen=True, slots=True)
class IncidentClassCoverageAssessment:
    incident_class_ref: str
    runbook_ref: str | None
    runbook_version: str | None
    missing_phases: tuple[IncidentResponsePhase, ...]
    passed: bool
    violations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SupportReadinessAssessment:
    """Readiness documentaire/organisationnelle, distincte d'un SLA réel."""

    passed: bool
    protocol_ref: str
    assessed_at_utc: datetime
    class_assessments: tuple[IncidentClassCoverageAssessment, ...]
    violations: tuple[str, ...]
    support_policy_ref: str
    escalation_matrix_ref: str
    contact_roster_ref: str
    maintenance_policy_ref: str
    evidence_archive_ref: str


def assess_support_readiness(
    *,
    protocol_ref: str,
    requirements: tuple[IncidentClassRequirement, ...],
    runbooks: tuple[SupportRunbookDescriptor, ...],
    organization: SupportOrganizationEvidence,
    assessed_at: datetime,
) -> SupportReadinessAssessment:
    """Vérifie la couverture sans inventer classes, phases ou horaires de support."""

    if not protocol_ref.strip():
        raise ValueError("La référence du protocole de support est obligatoire.")
    if assessed_at.tzinfo is None or assessed_at.utcoffset() is None:
        raise ValueError("L'instant d'évaluation du support doit être timezone-aware.")
    if not requirements:
        raise ValueError("Au moins une classe d'incident requise doit être définie.")

    requirement_refs = tuple(item.incident_class_ref for item in requirements)
    if len(requirement_refs) != len(set(requirement_refs)):
        raise ValueError("Chaque classe d'incident ne peut avoir qu'une exigence de couverture.")

    runbook_refs = tuple(item.runbook_ref for item in runbooks)
    if len(runbook_refs) != len(set(runbook_refs)):
        raise ValueError("Chaque référence de runbook doit être unique.")
    runbook_classes = tuple(item.incident_class_ref for item in runbooks)
    if len(runbook_classes) != len(set(runbook_classes)):
        raise ValueError("Une classe d'incident ne peut être liée qu'à un runbook actif.")

    runbook_by_class = {item.incident_class_ref: item for item in runbooks}
    class_assessments: list[IncidentClassCoverageAssessment] = []
    global_violations: list[str] = []

    for requirement in requirements:
        runbook = runbook_by_class.get(requirement.incident_class_ref)
        if runbook is None:
            class_assessments.append(
                IncidentClassCoverageAssessment(
                    incident_class_ref=requirement.incident_class_ref,
                    runbook_ref=None,
                    runbook_version=None,
                    missing_phases=requirement.required_phases,
                    passed=False,
                    violations=("runbook_missing",),
                )
            )
            global_violations.append(
                f"runbook_missing:{requirement.incident_class_ref}"
            )
            continue

        missing_phases = tuple(
            phase for phase in requirement.required_phases if phase not in runbook.covered_phases
        )
        violations = (
            tuple(f"phase_missing:{phase.value}" for phase in missing_phases)
            if missing_phases
            else ()
        )
        if violations:
            global_violations.extend(
                f"{violation}:{requirement.incident_class_ref}" for violation in violations
            )
        class_assessments.append(
            IncidentClassCoverageAssessment(
                incident_class_ref=requirement.incident_class_ref,
                runbook_ref=runbook.runbook_ref,
                runbook_version=runbook.version,
                missing_phases=missing_phases,
                passed=not violations,
                violations=violations,
            )
        )

    required_classes = set(requirement_refs)
    orphan_runbooks = sorted(set(runbook_classes) - required_classes)
    for incident_class_ref in orphan_runbooks:
        global_violations.append(f"runbook_without_active_requirement:{incident_class_ref}")

    return SupportReadinessAssessment(
        passed=not global_violations,
        protocol_ref=protocol_ref,
        assessed_at_utc=assessed_at.astimezone(UTC),
        class_assessments=tuple(class_assessments),
        violations=tuple(global_violations),
        support_policy_ref=organization.support_policy_ref,
        escalation_matrix_ref=organization.escalation_matrix_ref,
        contact_roster_ref=organization.contact_roster_ref,
        maintenance_policy_ref=organization.maintenance_policy_ref,
        evidence_archive_ref=organization.evidence_archive_ref,
    )


__all__ = [
    "IncidentClassCoverageAssessment",
    "IncidentClassRequirement",
    "IncidentResponsePhase",
    "SupportOrganizationEvidence",
    "SupportReadinessAssessment",
    "SupportRunbookDescriptor",
    "assess_support_readiness",
]
