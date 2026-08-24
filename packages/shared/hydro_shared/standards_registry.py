"""Gouvernance des références normatives et jeux de règles PETROLE.

Le registre conserve uniquement des métadonnées de référence et l'identité des
jeux de règles internes approuvés. Il n'embarque ni texte normatif protégé, ni
clause reconstruite depuis une page publique.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class StandardEditionReference:
    """Référence d'une édition normative légalement identifiée."""

    standard_code: str
    edition: str
    publisher: str
    source_ref: str
    acquired_for_project: bool
    reviewed_by: str | None = None
    review_date: date | None = None

    def __post_init__(self) -> None:
        required = (self.standard_code, self.edition, self.publisher, self.source_ref)
        if any(not value.strip() for value in required):
            raise ValueError("Code, édition, éditeur et référence source sont obligatoires.")
        if (self.reviewed_by is None) != (self.review_date is None):
            raise ValueError("Le réviseur et la date de revue doivent être renseignés ensemble.")
        if self.reviewed_by is not None and not self.reviewed_by.strip():
            raise ValueError("L'identité du réviseur ne peut pas être vide.")

    @property
    def approved_for_rule_binding(self) -> bool:
        """Une édition doit être acquise et revue avant de lier des règles contractuelles."""

        return self.acquired_for_project and self.reviewed_by is not None


@dataclass(frozen=True, slots=True)
class InternalRuleSetBinding:
    """Lien entre règles internes versionnées et édition source approuvée."""

    ruleset_id: str
    ruleset_version: str
    standard_code: str
    standard_edition: str
    implementation_ref: str
    approval_ref: str

    def __post_init__(self) -> None:
        values = (
            self.ruleset_id,
            self.ruleset_version,
            self.standard_code,
            self.standard_edition,
            self.implementation_ref,
            self.approval_ref,
        )
        if any(not value.strip() for value in values):
            raise ValueError("Toutes les références d'un binding de règles sont obligatoires.")


def bind_ruleset_to_standard(
    *,
    standard: StandardEditionReference,
    ruleset_id: str,
    ruleset_version: str,
    implementation_ref: str,
    approval_ref: str,
) -> InternalRuleSetBinding:
    """Crée un binding uniquement pour une édition acquise et revue."""

    if not standard.approved_for_rule_binding:
        raise PermissionError(
            "Une édition normative doit être acquise légalement et revue avant de lier des règles."
        )
    return InternalRuleSetBinding(
        ruleset_id=ruleset_id,
        ruleset_version=ruleset_version,
        standard_code=standard.standard_code,
        standard_edition=standard.edition,
        implementation_ref=implementation_ref,
        approval_ref=approval_ref,
    )


def binding_matches_standard(
    binding: InternalRuleSetBinding,
    standard: StandardEditionReference,
) -> bool:
    """Détecte explicitement un changement d'édition nécessitant une nouvelle revue."""

    return (
        binding.standard_code == standard.standard_code
        and binding.standard_edition == standard.edition
    )


__all__ = [
    "InternalRuleSetBinding",
    "StandardEditionReference",
    "bind_ruleset_to_standard",
    "binding_matches_standard",
]
