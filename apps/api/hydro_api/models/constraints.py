"""Contraintes SQLAlchemy dérivées des contrats publics du domaine.

Les statuts de calcul sont définis une seule fois dans :class:`SimulationStatus`.
Ce module remplace la contrainte historique déclarée dans le modèle par une
contrainte construite depuis cette énumération, afin que les métadonnées
SQLAlchemy, Alembic et le contrat API restent alignés.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Table

from hydro_shared.codes import SimulationStatus


def calculation_status_expression() -> str:
    """Produit l'expression SQL de la contrainte des statuts de calcul."""

    values = ", ".join(f"'{status.value}'" for status in SimulationStatus)
    return f"status IN ({values})"


def align_calculation_status_constraint(table: Table) -> None:
    """Aligne la contrainte de la table avec l'énumération publique.

    SQLAlchemy permet officiellement d'ajouter et de retirer des objets
    ``Constraint`` des métadonnées d'une ``Table``. L'opération est idempotente
    et exécutée lors de l'import du paquet de modèles, avant l'utilisation des
    métadonnées par Alembic ou par les services.
    """

    expected_expression = calculation_status_expression()
    existing_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name in {"status_valid", "ck_calculation_runs_status_valid"}
    ]

    if len(existing_constraints) == 1:
        current_expression = str(existing_constraints[0].sqltext)
        if current_expression == expected_expression:
            return

    for constraint in existing_constraints:
        table.constraints.remove(constraint)

    table.append_constraint(
        CheckConstraint(
            expected_expression,
            name="status_valid",
        )
    )


__all__ = [
    "align_calculation_status_constraint",
    "calculation_status_expression",
]
