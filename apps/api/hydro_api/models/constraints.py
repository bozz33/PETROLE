"""Contraintes SQLAlchemy dérivées des contrats publics du domaine.

Les statuts de calcul sont définis une seule fois dans :class:`SimulationStatus`.
Ce module maintient également les adaptations de métadonnées rendues nécessaires
par les sources industrielles read-only : contrairement à un import de fichier,
une acquisition OPC UA/historian possède un lignage propre et ne doit jamais
recevoir un faux ``dataset_id`` uniquement pour satisfaire le schéma.
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


def align_industrial_dataset_nullability(*tables: Table) -> None:
    """Autorise ``dataset_id=NULL`` pour le lignage industriel read-only.

    La migration ``d8f1a6c3e590`` ouvre ces colonnes afin qu'un flux OPC UA ou
    historian soit rattaché à son tag/import sans fabriquer de dataset fichier.
    Cette fonction aligne les métadonnées ORM avec ce contrat avant leur lecture
    par Alembic. Elle ne retire ni clé étrangère, ni identifiant d'import, ni
    provenance brute.
    """

    for table in tables:
        dataset_column = table.c.get("dataset_id")
        if dataset_column is None:
            raise ValueError(f"La table {table.name} ne possède pas de colonne dataset_id.")
        dataset_column.nullable = True


__all__ = [
    "align_calculation_status_constraint",
    "align_industrial_dataset_nullability",
    "calculation_status_expression",
]
