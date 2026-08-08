"""Validation de l'énumération et du classement des configurations de pompage."""

from __future__ import annotations

import pytest

from hydro_domain.enums import ObjectiveKind
from hydro_optimization import (
    CandidateEvaluation,
    ExhaustivePumpOptimizer,
    ObjectiveWeights,
    OptimizationConstraints,
    OptimizationRequest,
    OptimizationStatus,
)
from hydro_shared.errors import InvalidInputError, NoPhysicalSolutionError

CAPACITY = {"P1": 1.0, "P2": 1.2, "P3": 2.0}
ENERGY = {"P1": 5.0, "P2": 6.0, "P3": 20.0}


def evaluate(configuration):
    ratios = dict(configuration.speed_ratios)
    flow = sum(CAPACITY[pump] * ratios[pump] for pump in configuration.active_pump_ids)
    energy = sum(ENERGY[pump] * ratios[pump] ** 3 for pump in configuration.active_pump_ids)
    return CandidateEvaluation(
        flow_m3_s=flow,
        energy_kwh=energy,
        cost=energy * 0.2,
        minimum_pressure_pa=200_000.0 + 10_000.0 * flow,
        maximum_pressure_pa=1_000_000.0 + 20_000.0 * flow,
        starts_count=configuration.active_pump_count,
    )


def standard_request(**updates):
    arguments = {
        "pump_ids": ("P1", "P2", "P3"),
        "constraints": OptimizationConstraints(minimum_flow_m3_s=2.0),
    }
    arguments.update(updates)
    return OptimizationRequest(**arguments)


def test_enumere_toutes_les_combinaisons_et_minimise_energie():
    result = ExhaustivePumpOptimizer().optimize(standard_request(), evaluate)

    assert result.status is OptimizationStatus.OPTIMAL
    assert result.complete
    assert result.generated_count == 7
    assert result.evaluated_count == 7
    assert result.optimality_gap == 0.0
    assert result.best is not None
    assert result.best.configuration.active_pump_ids == ("P1", "P2")
    assert result.best.objective_value == pytest.approx(11.0)
    assert result.best.rank == 1
    assert result.rejected
    assert any("Débit" in reason for item in result.rejected for reason in item.reasons)


def test_minimise_nombre_de_pompes():
    request = standard_request(objective=ObjectiveKind.MIN_PUMP_COUNT)

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.best is not None
    assert result.best.configuration.active_pump_ids == ("P3",)
    assert result.best.objective_value == 1.0


def test_maximise_debit():
    request = standard_request(
        objective=ObjectiveKind.MAX_FLOW,
        constraints=OptimizationConstraints(),
    )

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.best is not None
    assert result.best.configuration.active_pump_ids == ("P1", "P2", "P3")
    assert result.best.evaluation.flow_m3_s == pytest.approx(4.2)


def test_objectif_pondere():
    request = standard_request(
        constraints=OptimizationConstraints(minimum_flow_m3_s=0.9),
        weights=ObjectiveWeights(energy=1.0, active_pumps=100.0),
    )

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.best is not None
    assert result.best.configuration.active_pump_ids == ("P1",)


def test_pompe_obligatoire_et_pompe_interdite():
    request = standard_request(
        constraints=OptimizationConstraints(
            minimum_flow_m3_s=2.0,
            required_pump_ids=frozenset({"P1"}),
            forbidden_pump_ids=frozenset({"P3"}),
        )
    )

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.best is not None
    assert result.best.configuration.active_pump_ids == ("P1", "P2")
    assert any(
        "obligatoires" in reason or "interdites" in reason
        for item in result.rejected
        for reason in item.reasons
    )


def test_vitesses_variables():
    request = OptimizationRequest(
        pump_ids=("P1", "P2"),
        speed_options=(0.75, 1.0),
        constraints=OptimizationConstraints(minimum_flow_m3_s=1.5),
    )

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.generated_count == 8
    assert result.best is not None
    assert result.best.configuration.active_pump_ids == ("P1", "P2")
    assert result.best.configuration.speed_ratios == (("P1", 0.75), ("P2", 0.75))


def test_contraintes_de_pression_expliquees():
    request = standard_request(
        constraints=OptimizationConstraints(
            minimum_flow_m3_s=2.0,
            minimum_pressure_pa=230_000.0,
        )
    )

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.best is not None
    assert result.best.configuration.active_pump_ids == ("P1", "P3")
    assert any("Pression minimale" in reason for item in result.rejected for reason in item.reasons)


def test_absence_de_solution_faisable():
    request = standard_request(constraints=OptimizationConstraints(minimum_flow_m3_s=10.0))

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.status is OptimizationStatus.INFEASIBLE
    assert result.best is None
    assert len(result.rejected) == result.generated_count


def test_arret_anticipe_conserve_meilleure_solution_et_gap():
    request = standard_request(
        constraints=OptimizationConstraints(),
        maximum_evaluations=1,
        objective_lower_bound=0.0,
    )

    result = ExhaustivePumpOptimizer().optimize(request, evaluate)

    assert result.status is OptimizationStatus.STOPPED_WITH_SOLUTION
    assert not result.complete
    assert result.evaluated_count == 1
    assert result.best is not None
    assert result.optimality_gap == pytest.approx(1.0)
    assert any(
        "limite d'évaluations" in reason for item in result.rejected for reason in item.reasons
    )


def test_erreur_metier_evaluation_devient_rejet():
    request = OptimizationRequest(pump_ids=("P1",))

    def impossible(_configuration):
        raise NoPhysicalSolutionError("Aucun point de fonctionnement physique.")

    result = ExhaustivePumpOptimizer().optimize(request, impossible)

    assert result.status is OptimizationStatus.INFEASIBLE
    assert result.evaluated_count == 1
    assert "Évaluation impossible" in result.rejected[0].reasons[0]


def test_resultat_deterministe():
    optimizer = ExhaustivePumpOptimizer()
    request = standard_request()

    first = optimizer.optimize(request, evaluate)
    second = optimizer.optimize(request, evaluate)

    assert [item.configuration.id for item in first.ranked] == [
        item.configuration.id for item in second.ranked
    ]
    assert [item.objective_value for item in first.ranked] == [
        item.objective_value for item in second.ranked
    ]


@pytest.mark.parametrize(
    "arguments",
    [
        {"pump_ids": ("P1", "P1")},
        {"pump_ids": ("P2", "P1")},
        {"pump_ids": ("P1",), "speed_options": (1.0, 0.8)},
        {
            "pump_ids": ("P1",),
            "constraints": OptimizationConstraints(required_pump_ids=frozenset({"P2"})),
        },
    ],
)
def test_espace_de_recherche_invalide(arguments):
    with pytest.raises(InvalidInputError):
        OptimizationRequest(**arguments)


def test_metrique_objectif_absente_rejetee():
    request = OptimizationRequest(
        pump_ids=("P1",),
        objective=ObjectiveKind.MIN_COST,
    )

    result = ExhaustivePumpOptimizer().optimize(
        request,
        lambda _configuration: CandidateEvaluation(flow_m3_s=1.0),
    )

    assert result.status is OptimizationStatus.INFEASIBLE
    assert "Coût absent" in result.rejected[0].reasons[-1]


@pytest.mark.scientific
def test_voie_pyomo_retrouve_l_optimum_de_l_enumeration() -> None:
    """La sélection par programmation entière doit converger vers le même choix.

    La physique reste évaluée par simulation : Pyomo ne pose que le problème de
    décision réellement linéaire, choisir une configuration parmi celles évaluées.
    """

    from hydro_optimization.pyomo_selection import (
        PyomoSelectionOptimizer,
        PyomoSolverUnavailableError,
    )

    request = OptimizationRequest(
        pump_ids=("P1", "P2", "P3"),
        speed_options=(0.8, 1.0),
        objective=ObjectiveKind.MIN_ENERGY,
    )

    def evaluate(configuration) -> CandidateEvaluation:
        # Énergie décroissante avec le nombre de pompes actives, pour que
        # l'optimum soit non trivial et unique.
        active = configuration.active_pump_count
        return CandidateEvaluation(
            flow_m3_s=0.05 * max(active, 1),
            energy_kwh=100.0
            - 7.5 * active
            + 0.5 * sum(ratio for _, ratio in configuration.speed_ratios),
            cost=None,
            minimum_pressure_pa=300_000.0,
            maximum_pressure_pa=5_000_000.0,
            starts_count=active,
            converged=True,
        )

    enumerated = ExhaustivePumpOptimizer().optimize(request, evaluate)
    try:
        selected = PyomoSelectionOptimizer().optimize(request, evaluate)
    except PyomoSolverUnavailableError as error:  # pragma: no cover - dépend de l'image
        pytest.skip(f"Solveur MILP indisponible : {error}")

    assert enumerated.ranked
    assert selected.ranked
    assert selected.ranked[0].objective_value == pytest.approx(enumerated.ranked[0].objective_value)
    assert selected.ranked[0].configuration.id == enumerated.ranked[0].configuration.id
