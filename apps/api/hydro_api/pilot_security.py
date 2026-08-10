"""Évaluation explicite de readiness sécurité du pilote V1.

Cette fonction ne certifie pas un déploiement. Elle transforme des preuves
techniques fournies par l'équipe en blockers/warnings reproductibles avant une
première installation selon D15/D20.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from hydro_api.config import Settings

_FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class PilotSecurityEvidence:
    """Preuves externes au processus applicatif collectées pour un candidat pilote."""

    https_verified: bool = False
    backup_restore_verified: bool = False
    vulnerability_scan_passed: bool = False
    access_review_completed: bool = False
    incident_contacts_defined: bool = False
    ot_architecture_approved: bool = False


@dataclass(frozen=True, slots=True)
class PilotSecurityReadiness:
    """Résultat déterministe : blockers empêchent un pilote, warnings restent à traiter."""

    ready: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


def evaluate_pilot_security(
    settings: Settings,
    evidence: PilotSecurityEvidence,
) -> PilotSecurityReadiness:
    """Évalue les conditions minimales sans inventer de conformité externe."""

    blockers: list[str] = []
    warnings: list[str] = []

    if settings.environment not in {"staging", "production"}:
        blockers.append("Le pilote exige un environnement staging ou production.")
    if not settings.authentication_required:
        blockers.append("L'authentification doit être activée pour le pilote.")
    jwt_secret = settings.jwt_secret.get_secret_value()
    if len(jwt_secret) < 32 or jwt_secret.startswith("development-"):
        blockers.append(
            "Le secret JWT du pilote doit être privé, non-développement et >= 32 caractères."
        )
    if not _FULL_GIT_SHA.fullmatch(settings.build_git_sha):
        blockers.append("Le déploiement pilote doit publier un SHA Git complet de 40 caractères.")

    if settings.deployment_mode == "single_org" and settings.default_organization_id is None:
        blockers.append("Le mode single_org exige HYDRO_DEFAULT_ORGANIZATION_ID.")
    if settings.deployment_mode != "single_org":
        warnings.append(
            "Le pilote mono-exploitant devrait utiliser single_org, sauf architecture multi-org approuvée."
        )

    evidence_checks = (
        (evidence.https_verified, "HTTPS n'a pas encore été vérifié sur l'instance pilote."),
        (
            evidence.backup_restore_verified,
            "La sauvegarde/restauration n'a pas encore été vérifiée sur l'instance pilote.",
        ),
        (
            evidence.vulnerability_scan_passed,
            "Le scan de vulnérabilités du candidat pilote n'est pas clôturé.",
        ),
        (
            evidence.access_review_completed,
            "La revue des comptes, rôles et moindre privilège n'est pas clôturée.",
        ),
        (
            evidence.incident_contacts_defined,
            "Les contacts et la procédure d'incident du pilote ne sont pas définis.",
        ),
    )
    blockers.extend(message for passed, message in evidence_checks if not passed)

    if not evidence.ot_architecture_approved:
        warnings.append(
            "Architecture OT non approuvée : aucun connecteur SCADA/historian réel ne doit être activé."
        )

    return PilotSecurityReadiness(
        ready=not blockers,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


__all__ = [
    "PilotSecurityEvidence",
    "PilotSecurityReadiness",
    "evaluate_pilot_security",
]
