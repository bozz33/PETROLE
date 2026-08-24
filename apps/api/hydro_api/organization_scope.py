"""Résolution de portée organisationnelle pour déploiements PETROLE.

En mode ``single_org``, l'organisation est une clé d'isolation interne : une
requête peut omettre l'identifiant, mais ne peut jamais sélectionner une autre
organisation. Les modes multi-org/saas exigent au contraire une portée
explicitement résolue par la couche d'authentification/autorisation.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

DeploymentMode = Literal["single_org", "multi_org", "saas"]


def resolve_organization_scope(
    *,
    deployment_mode: DeploymentMode,
    default_organization_id: UUID | None,
    requested_organization_id: UUID | None,
) -> UUID:
    """Retourne l'organisation interne autorisée pour la requête.

    Cette fonction ne remplace pas RBAC/OIDC. Elle impose uniquement le contrat
    de portée du déploiement et empêche un changement d'organisation piloté par
    l'utilisateur dans une instance mono-exploitant.
    """

    if deployment_mode == "single_org":
        if default_organization_id is None:
            raise ValueError("Le mode single_org exige une organisation interne par défaut.")
        if (
            requested_organization_id is not None
            and requested_organization_id != default_organization_id
        ):
            raise PermissionError(
                "Une instance single_org ne permet pas de sélectionner une autre organisation."
            )
        return default_organization_id

    if requested_organization_id is None:
        raise ValueError(
            "Les modes multi_org/saas exigent une organisation résolue par l'identité courante."
        )
    return requested_organization_id


__all__ = ["DeploymentMode", "resolve_organization_scope"]
