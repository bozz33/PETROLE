"""Sélection exacte de la configuration de pompage par programmation en nombres entiers.

La documentation du MVP prévoit une voie Pyomo à côté de l'énumération. Ce
module la fournit sans travestir la physique : le comportement hydraulique d'une
configuration reste évalué par le moteur de simulation, car il n'admet pas de
formulation algébrique fermée. Ce qui est confié à Pyomo, c'est le problème
réellement linéaire qui subsiste — choisir une configuration parmi celles
évaluées, sous les contraintes d'exploitation, en minimisant l'objectif retenu.

Sur un même espace de recherche, cette voie doit retrouver l'optimum de
l'énumération : un test de concordance le vérifie. Elle n'apporte pas de gain de
temps sur le périmètre borné du MVP ; elle apporte une formulation explicite du
problème de décision, vérifiable indépendamment du parcours d'énumération.
"""

from __future__ import annotations

from hydro_optimization.optimizer import (
    CandidateEvaluator,
    ExhaustivePumpOptimizer,
    OptimizationRequest,
    OptimizationResult,
    RankedCandidate,
)
from hydro_shared.errors import HydroError

#: Solveur MILP embarqué avec la plateforme.
DEFAULT_SOLVER = "appsi_highs"


class PyomoSolverUnavailableError(HydroError):
    """Aucun solveur MILP exploitable n'est disponible dans l'environnement."""


class PyomoSelectionOptimizer:
    """Choisit la configuration retenue par un programme en nombres entiers.

    L'énumération filtrée reste chargée de produire et d'évaluer les candidats ;
    seule la décision finale est posée comme un problème d'optimisation explicite.
    """

    def __init__(self, solver_name: str = DEFAULT_SOLVER) -> None:
        self.solver_name = solver_name

    def optimize(
        self,
        request: OptimizationRequest,
        evaluator: CandidateEvaluator,
    ) -> OptimizationResult:
        """Retourne le même dossier que l'énumération, décision posée par Pyomo."""

        base = ExhaustivePumpOptimizer().optimize(request, evaluator)
        if not base.ranked:
            return base

        selected = self._select(base.ranked)
        if selected is base.ranked[0]:
            return base

        # Le classement reste celui de l'objectif ; seule la tête change si le
        # programme retient un autre candidat de valeur identique.
        reordered = (
            selected,
            *(candidate for candidate in base.ranked if candidate is not selected),
        )
        ranked = tuple(
            RankedCandidate(
                rank=rank,
                configuration=candidate.configuration,
                evaluation=candidate.evaluation,
                objective_value=candidate.objective_value,
            )
            for rank, candidate in enumerate(reordered, start=1)
        )
        return OptimizationResult(
            status=base.status,
            ranked=ranked,
            rejected=base.rejected,
            generated_count=base.generated_count,
            evaluated_count=base.evaluated_count,
            complete=base.complete,
            optimality_gap=base.optimality_gap,
            solver_name=f"pyomo_{self.solver_name}",
        )

    def _select(self, ranked: tuple[RankedCandidate, ...]) -> RankedCandidate:
        """Pose et résout le choix d'une configuration unique."""

        try:
            import pyomo.environ as pyo
        except ImportError as error:  # pragma: no cover - dépendance déclarée
            raise PyomoSolverUnavailableError(
                "Pyomo n'est pas installé dans cet environnement."
            ) from error

        solver = pyo.SolverFactory(self.solver_name)
        if not solver.available(exception_flag=False):
            raise PyomoSolverUnavailableError(
                f"Le solveur « {self.solver_name} » n'est pas disponible.",
                solver=self.solver_name,
            )

        indices = range(len(ranked))
        model = pyo.ConcreteModel(name="selection_configuration_pompage")
        model.candidates = pyo.Set(initialize=list(indices))
        model.retained = pyo.Var(model.candidates, domain=pyo.Binary)
        model.unique_choice = pyo.Constraint(
            expr=sum(model.retained[index] for index in indices) == 1
        )
        model.objective = pyo.Objective(
            expr=sum(ranked[index].objective_value * model.retained[index] for index in indices),
            sense=pyo.minimize,
        )

        outcome = solver.solve(model)
        condition = outcome.solver.termination_condition
        if condition not in {
            pyo.TerminationCondition.optimal,
            pyo.TerminationCondition.feasible,
        }:
            raise PyomoSolverUnavailableError(
                "Le programme de sélection n'a pas abouti.",
                termination_condition=str(condition),
            )

        for index in indices:
            if pyo.value(model.retained[index]) > 0.5:
                return ranked[index]
        raise PyomoSolverUnavailableError("Le programme de sélection n'a retenu aucun candidat.")


__all__ = ["DEFAULT_SOLVER", "PyomoSelectionOptimizer", "PyomoSolverUnavailableError"]
