"""Tests des contraintes SQLAlchemy dérivées des contrats publics."""

from __future__ import annotations

from sqlalchemy import CheckConstraint

from hydro_api.models import CalculationRun
from hydro_api.models.constraints import calculation_status_expression
from hydro_shared.codes import SimulationStatus


def test_contrainte_statut_calcul_alignee_sur_enumeration() -> None:
    constraints = [
        constraint
        for constraint in CalculationRun.__table__.constraints
        if isinstance(constraint, CheckConstraint)
        and constraint.name in {"status_valid", "ck_calculation_runs_status_valid"}
    ]

    assert len(constraints) == 1
    expression = str(constraints[0].sqltext)
    assert expression == calculation_status_expression()
    for status in SimulationStatus:
        assert status.value in expression
    assert SimulationStatus.NUMERIC_ERROR.value in expression
