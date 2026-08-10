"""Registre de preuves du pilote selon D20.

Le module vérifie la complétude et l'état documentaire des tests PIL-01 à
PIL-12. Il ne décide jamais automatiquement GO/NO-GO : cette décision reste
une revue explicite impliquant l'opérateur, les experts et les responsables du
site selon les critères approuvés pour le pilote.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PilotTestCode(StrEnum):
    """Campagne de tests définie par D20 §8."""

    PIL_01 = "PIL-01"
    PIL_02 = "PIL-02"
    PIL_03 = "PIL-03"
    PIL_04 = "PIL-04"
    PIL_05 = "PIL-05"
    PIL_06 = "PIL-06"
    PIL_07 = "PIL-07"
    PIL_08 = "PIL-08"
    PIL_09 = "PIL-09"
    PIL_10 = "PIL-10"
    PIL_11 = "PIL-11"
    PIL_12 = "PIL-12"


class PilotEvidenceStatus(StrEnum):
    """État factuel d'un test, distinct de la décision finale du pilote."""

    NOT_RUN = "not_run"
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class PilotTestEvidence:
    """Preuve versionnée pour un test de la campagne D20."""

    code: PilotTestCode
    status: PilotEvidenceStatus
    evidence_ref: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.status in {PilotEvidenceStatus.PASS, PilotEvidenceStatus.FAIL}:
            if self.evidence_ref is None or not self.evidence_ref.strip():
                raise ValueError(
                    "Un test exécuté PASS/FAIL doit référencer une preuve archivée."
                )
        if self.evidence_ref is not None and not self.evidence_ref.strip():
            raise ValueError("Une référence de preuve ne peut pas être vide.")
        if self.note is not None and not self.note.strip():
            raise ValueError("Une note de preuve ne peut pas être vide.")


@dataclass(frozen=True, slots=True)
class PilotCampaignEvidence:
    """Dossier minimal de campagne préparant la revue de décision D20."""

    site_reference: str
    baseline_reference: str
    protocol_reference: str
    tests: tuple[PilotTestEvidence, ...]

    def __post_init__(self) -> None:
        references = (
            self.site_reference,
            self.baseline_reference,
            self.protocol_reference,
        )
        if any(not reference.strip() for reference in references):
            raise ValueError("Site, baseline et protocole doivent être référencés.")
        codes = [evidence.code for evidence in self.tests]
        if len(codes) != len(set(codes)):
            raise ValueError("Chaque code PIL ne peut apparaître qu'une fois dans la campagne.")


@dataclass(frozen=True, slots=True)
class PilotCampaignAssessment:
    """État de complétude avant revue humaine GO/NO-GO."""

    ready_for_decision_review: bool
    missing_tests: tuple[PilotTestCode, ...]
    not_run_tests: tuple[PilotTestCode, ...]
    blocked_tests: tuple[PilotTestCode, ...]
    failed_tests: tuple[PilotTestCode, ...]
    passed_tests: tuple[PilotTestCode, ...]


def assess_pilot_campaign(campaign: PilotCampaignEvidence) -> PilotCampaignAssessment:
    """Vérifie la campagne sans transformer les résultats en décision GO/NO-GO.

    Une campagne devient prête pour la revue de décision lorsque les douze tests
    sont présents et qu'aucun n'est encore `not_run` ou `blocked`. Des FAIL
    peuvent donc être présents : ils doivent justement être examinés pour une
    décision REWORK, NO-GO ou autre issue prévue par D20.
    """

    by_code = {evidence.code: evidence for evidence in campaign.tests}
    all_codes = tuple(PilotTestCode)
    missing = tuple(code for code in all_codes if code not in by_code)
    not_run = tuple(
        code
        for code in all_codes
        if code in by_code and by_code[code].status is PilotEvidenceStatus.NOT_RUN
    )
    blocked = tuple(
        code
        for code in all_codes
        if code in by_code and by_code[code].status is PilotEvidenceStatus.BLOCKED
    )
    failed = tuple(
        code
        for code in all_codes
        if code in by_code and by_code[code].status is PilotEvidenceStatus.FAIL
    )
    passed = tuple(
        code
        for code in all_codes
        if code in by_code and by_code[code].status is PilotEvidenceStatus.PASS
    )
    return PilotCampaignAssessment(
        ready_for_decision_review=not missing and not not_run and not blocked,
        missing_tests=missing,
        not_run_tests=not_run,
        blocked_tests=blocked,
        failed_tests=failed,
        passed_tests=passed,
    )


__all__ = [
    "PilotCampaignAssessment",
    "PilotCampaignEvidence",
    "PilotEvidenceStatus",
    "PilotTestCode",
    "PilotTestEvidence",
    "assess_pilot_campaign",
]
