"""Adaptation du workflow pour l'instance PETROLE mono-utilisateur.

La base conserve volontairement les anciens statuts ``approved`` et les dates
``approved_at`` afin d'éviter une migration destructive juste avant le MVP.
Dans une instance ``single_org``, ces champs deviennent uniquement des marqueurs
techniques de disponibilité/figement : aucune seconde personne ni action
humaine d'approbation n'est requise.

Les services multi-organisation historiques restent inchangés et peuvent être
réactivés plus tard si PETROLE est déployé dans une organisation à plusieurs
utilisateurs.
"""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.services import catalog, governance

CatalogCallable = Callable[..., Any]
GovernanceCallable = Callable[..., Any]

_ORIGINAL_CREATE_CATALOG_ITEM = catalog.create_catalog_item
_ORIGINAL_CREATE_CATALOG_VERSION = catalog.create_catalog_version
_ORIGINAL_CREATE_STANDARD = governance.create_standard
_ORIGINAL_CREATE_RULE_SET = governance.create_rule_set
_ORIGINAL_CREATE_RULE = governance.create_rule

_ENABLED = False


def _available_catalog_item(function: CatalogCallable) -> CatalogCallable:
    def wrapped(session: Session, *args: Any, **kwargs: Any):
        item = function(session, *args, **kwargs)
        if item.status == "draft":
            # ``approved`` est conservé comme valeur SQL historique. Dans le
            # mode mono-utilisateur il signifie seulement « disponible ».
            item.status = "approved"
            item.approved_at = utc_now()
            session.flush()
        return item

    return wrapped


def _active_standard(session: Session, *args: Any, **kwargs: Any):
    item = _ORIGINAL_CREATE_STANDARD(session, *args, **kwargs)
    if item.status == "draft":
        item.status = "active"
        item.approved_at = utc_now()
        session.flush()
    return item


def _available_rule_set(session: Session, *args: Any, **kwargs: Any):
    item = _ORIGINAL_CREATE_RULE_SET(session, *args, **kwargs)
    # Le statut historique ``approved`` rend le jeu immédiatement sélectionnable
    # par les projets et les calculs. ``_available_rule`` le repasse brièvement
    # en brouillon lorsqu'une nouvelle règle doit être ajoutée.
    item.status = "approved"
    item.approved_at = utc_now()
    governance.refresh_rule_set_hash(session, item)
    session.flush()
    return item


def _available_rule(session: Session, rule_set_id, *args: Any, **kwargs: Any):
    rule_set = governance.get_rule_set(session, rule_set_id)
    previous_status = rule_set.status
    previous_approved_at = rule_set.approved_at

    # Le service historique protège les jeux figés. En mono-utilisateur, on
    # ouvre uniquement le temps de la transaction d'ajout puis on le referme
    # automatiquement, sans décision humaine.
    if rule_set.status == "approved":
        rule_set.status = "draft"
        session.flush()
    try:
        rule = _ORIGINAL_CREATE_RULE(session, rule_set_id, *args, **kwargs)
    except Exception:
        rule_set.status = previous_status
        rule_set.approved_at = previous_approved_at
        session.flush()
        raise

    rule.status = "approved"
    rule.approved_at = utc_now()
    rule_set.status = "approved"
    rule_set.approved_at = previous_approved_at or utc_now()
    governance.refresh_rule_set_hash(session, rule_set)
    session.flush()
    return rule


def configure_single_user_workflow(enabled: bool) -> None:
    """Active ou restaure le workflow mono-utilisateur dans ce processus.

    ``create_application`` appelle cette fonction à chaque création d'application
    afin que les tests ``single_org`` et ``multi_org`` puissent cohabiter dans le
    même processus sans fuite globale d'état.
    """

    global _ENABLED
    _ENABLED = enabled
    if enabled:
        catalog.create_catalog_item = _available_catalog_item(_ORIGINAL_CREATE_CATALOG_ITEM)
        catalog.create_catalog_version = _available_catalog_item(_ORIGINAL_CREATE_CATALOG_VERSION)
        governance.create_standard = _active_standard
        governance.create_rule_set = _available_rule_set
        governance.create_rule = _available_rule
        return

    catalog.create_catalog_item = _ORIGINAL_CREATE_CATALOG_ITEM
    catalog.create_catalog_version = _ORIGINAL_CREATE_CATALOG_VERSION
    governance.create_standard = _ORIGINAL_CREATE_STANDARD
    governance.create_rule_set = _ORIGINAL_CREATE_RULE_SET
    governance.create_rule = _ORIGINAL_CREATE_RULE


def approval_workflow_enabled() -> bool:
    """Indique si le processus courant utilise encore le workflow historique."""

    return not _ENABLED


__all__ = ["approval_workflow_enabled", "configure_single_user_workflow"]
