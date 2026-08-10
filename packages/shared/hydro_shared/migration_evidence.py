"""Évaluation factuelle d'une migration applicative/base de données.

Le module ne lance ni Alembic ni une restauration. Il enregistre les preuves
d'un exercice sur un environnement représentatif et refuse de qualifier une
migration sans stratégie de retour arrière explicitement testée.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RollbackStrategy(StrEnum):
    """Stratégie effectivement testée pour revenir au service précédent."""

    ALEMBIC_DOWNGRADE = "alembic_downgrade"
    DATABASE_RESTORE = "database_restore"


@dataclass(frozen=True, slots=True)
class MigrationCompatibilityEvidence:
    """Preuves observées d'un exercice upgrade/rollback."""

    from_release: str
    to_release: str
    from_revision: str
    to_revision: str
    environment_ref: str
    evidence_archive_ref: str
    upgrade_applied: bool
    new_release_readiness_verified: bool
    data_integrity_after_upgrade_verified: bool
    rollback_strategy: RollbackStrategy
    rollback_executed: bool
    previous_release_readiness_verified: bool
    data_integrity_after_rollback_verified: bool

    def __post_init__(self) -> None:
        required = (
            self.from_release,
            self.to_release,
            self.from_revision,
            self.to_revision,
            self.environment_ref,
            self.evidence_archive_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Releases, révisions, environnement et archive de preuve sont obligatoires.")
        if self.from_release == self.to_release and self.from_revision == self.to_revision:
            raise ValueError("L'exercice de migration doit représenter un changement réel.")


@dataclass(frozen=True, slots=True)
class MigrationCompatibilityAssessment:
    """Verdict du drill de migration, sans prétention de compatibilité universelle."""

    passed: bool
    violations: tuple[str, ...]
    rollback_strategy: RollbackStrategy


def assess_migration_compatibility(
    evidence: MigrationCompatibilityEvidence,
) -> MigrationCompatibilityAssessment:
    """Exige une preuve positive pour chaque étape critique du drill."""

    checks = (
        (evidence.upgrade_applied, "upgrade_not_applied"),
        (evidence.new_release_readiness_verified, "new_release_readiness_not_verified"),
        (evidence.data_integrity_after_upgrade_verified, "upgrade_data_integrity_not_verified"),
        (evidence.rollback_executed, "rollback_not_executed"),
        (
            evidence.previous_release_readiness_verified,
            "previous_release_readiness_not_verified",
        ),
        (
            evidence.data_integrity_after_rollback_verified,
            "rollback_data_integrity_not_verified",
        ),
    )
    violations = tuple(code for passed, code in checks if not passed)
    return MigrationCompatibilityAssessment(
        passed=not violations,
        violations=violations,
        rollback_strategy=evidence.rollback_strategy,
    )


__all__ = [
    "MigrationCompatibilityAssessment",
    "MigrationCompatibilityEvidence",
    "RollbackStrategy",
    "assess_migration_compatibility",
]
