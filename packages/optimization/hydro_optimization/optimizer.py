"""Énumération et classement des configurations de pompage.

Pour les petits ensembles du MVP, toutes les combinaisons marche/arrêt et les vitesses
autorisées sont évaluées dans un ordre déterministe. Les configurations rejetées restent
dans le résultat avec leurs motifs. Une énumération terminée fournit une preuve d'optimalité
sur l'ensemble discret exploré et un écart d'optimalité nul.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from hydro_domain.enums import ObjectiveKind
from hydro_shared.errors import HydroError, InvalidInputError


class OptimizationStatus(StrEnum):
    """Statut stable d'une recherche de configuration."""

    OPTIMAL = "OPT_OPTIMAL"
    INFEASIBLE = "OPT_INFEASIBLE"
    STOPPED_WITH_SOLUTION = "OPT_STOPPED_WITH_SOLUTION"
    STOPPED_WITHOUT_SOLUTION = "OPT_STOPPED_WITHOUT_SOLUTION"


@dataclass(frozen=True, slots=True)
class PumpConfiguration:
    """Décisions marche/arrêt et rapport de vitesse de chaque pompe active."""

    active_pump_ids: tuple[str, ...]
    speed_ratios: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        if tuple(sorted(set(self.active_pump_ids))) != self.active_pump_ids:
            raise InvalidInputError(
                "Les identifiants de pompes actives doivent être uniques et triés.",
                active_pump_ids=self.active_pump_ids,
            )
        speed_ids = tuple(identifier for identifier, _ in self.speed_ratios)
        if speed_ids != self.active_pump_ids:
            raise InvalidInputError(
                "Une vitesse doit être fournie pour chaque pompe active, dans le même ordre.",
                active_pump_ids=self.active_pump_ids,
                speed_ids=speed_ids,
            )
        if any(not math.isfinite(ratio) or ratio <= 0 for _, ratio in self.speed_ratios):
            raise InvalidInputError(
                "Les rapports de vitesse doivent être strictement positifs et finis.",
                speed_ratios=self.speed_ratios,
            )

    @property
    def id(self) -> str:
        if not self.active_pump_ids:
            return "aucune-pompe"
        return "+".join(
            f"{pump_id}@{speed_ratio:.6g}" for pump_id, speed_ratio in self.speed_ratios
        )

    @property
    def active_pump_count(self) -> int:
        return len(self.active_pump_ids)

    def speed_ratio_for(self, pump_id: str) -> float | None:
        return dict(self.speed_ratios).get(pump_id)


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    """Grandeurs retournées par le moteur hydraulique pour une configuration."""

    flow_m3_s: float
    energy_kwh: float | None = None
    cost: float | None = None
    minimum_pressure_pa: float | None = None
    maximum_pressure_pa: float | None = None
    starts_count: int = 0
    availability_penalty: float = 0.0
    converged: bool = True
    violation_codes: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    metadata: dict[str, str | float | int | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        numeric_values = (
            self.flow_m3_s,
            self.energy_kwh,
            self.cost,
            self.minimum_pressure_pa,
            self.maximum_pressure_pa,
            self.availability_penalty,
        )
        if any(value is not None and not math.isfinite(value) for value in numeric_values):
            raise InvalidInputError(
                "L'évaluation d'une configuration contient une valeur non finie."
            )
        if self.flow_m3_s < 0:
            raise InvalidInputError(
                "Le débit évalué ne peut pas être négatif.",
                flow_m3_s=self.flow_m3_s,
            )
        if self.energy_kwh is not None and self.energy_kwh < 0:
            raise InvalidInputError(
                "L'énergie évaluée ne peut pas être négative.",
                energy_kwh=self.energy_kwh,
            )
        if self.cost is not None and self.cost < 0:
            raise InvalidInputError(
                "Le coût évalué ne peut pas être négatif.",
                cost=self.cost,
            )
        if self.starts_count < 0:
            raise InvalidInputError(
                "Le nombre de démarrages ne peut pas être négatif.",
                starts_count=self.starts_count,
            )


@dataclass(frozen=True, slots=True)
class OptimizationConstraints:
    """Contraintes opérationnelles appliquées à chaque candidat."""

    minimum_flow_m3_s: float | None = None
    maximum_flow_m3_s: float | None = None
    minimum_pressure_pa: float | None = None
    maximum_pressure_pa: float | None = None
    maximum_active_pumps: int | None = None
    required_pump_ids: frozenset[str] = frozenset()
    forbidden_pump_ids: frozenset[str] = frozenset()
    allow_violations: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("minimum_flow_m3_s", self.minimum_flow_m3_s),
            ("maximum_flow_m3_s", self.maximum_flow_m3_s),
            ("minimum_pressure_pa", self.minimum_pressure_pa),
            ("maximum_pressure_pa", self.maximum_pressure_pa),
        ):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise InvalidInputError(
                    f"La contrainte {name} doit être positive ou nulle et finie.",
                    field=name,
                    value=value,
                )
        if (
            self.minimum_flow_m3_s is not None
            and self.maximum_flow_m3_s is not None
            and self.minimum_flow_m3_s > self.maximum_flow_m3_s
        ):
            raise InvalidInputError("Le débit minimal dépasse le débit maximal.")
        if (
            self.minimum_pressure_pa is not None
            and self.maximum_pressure_pa is not None
            and self.minimum_pressure_pa > self.maximum_pressure_pa
        ):
            raise InvalidInputError("La pression minimale dépasse la pression maximale.")
        if self.maximum_active_pumps is not None and self.maximum_active_pumps < 0:
            raise InvalidInputError(
                "Le nombre maximal de pompes doit être positif ou nul.",
                maximum_active_pumps=self.maximum_active_pumps,
            )
        overlap = self.required_pump_ids & self.forbidden_pump_ids
        if overlap:
            raise InvalidInputError(
                "Une pompe ne peut pas être obligatoire et interdite.",
                pump_ids=sorted(overlap),
            )


@dataclass(frozen=True, slots=True)
class ObjectiveWeights:
    """Pondérations d'une fonction objectif composite.

    Les métriques doivent être préalablement ramenées à des échelles comparables par
    l'appelant. Un poids nul exclut la métrique correspondante.
    """

    energy: float = 0.0
    cost: float = 0.0
    active_pumps: float = 0.0
    starts: float = 0.0
    availability: float = 0.0
    violations: float = 0.0

    def __post_init__(self) -> None:
        values = (
            self.energy,
            self.cost,
            self.active_pumps,
            self.starts,
            self.availability,
            self.violations,
        )
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise InvalidInputError(
                "Les pondérations doivent être positives ou nulles et finies.",
                weights=values,
            )
        if not any(value > 0 for value in values):
            raise InvalidInputError("Au moins une pondération doit être strictement positive.")


@dataclass(frozen=True, slots=True)
class OptimizationRequest:
    """Espace discret, objectif et limites de la recherche."""

    pump_ids: tuple[str, ...]
    speed_options: tuple[float, ...] = (1.0,)
    objective: ObjectiveKind = ObjectiveKind.MIN_ENERGY
    weights: ObjectiveWeights | None = None
    constraints: OptimizationConstraints = OptimizationConstraints()
    allow_no_pump: bool = False
    maximum_configurations: int = 100_000
    maximum_evaluations: int | None = None
    objective_lower_bound: float | None = None

    def __post_init__(self) -> None:
        if not self.pump_ids:
            raise InvalidInputError("Au moins une pompe est requise pour l'optimisation.")
        if tuple(sorted(set(self.pump_ids))) != self.pump_ids:
            raise InvalidInputError(
                "Les identifiants de pompe doivent être uniques et triés.",
                pump_ids=self.pump_ids,
            )
        if not self.speed_options:
            raise InvalidInputError("Au moins un rapport de vitesse est requis.")
        if tuple(sorted(set(self.speed_options))) != self.speed_options:
            raise InvalidInputError(
                "Les rapports de vitesse doivent être uniques et triés.",
                speed_options=self.speed_options,
            )
        if any(not math.isfinite(value) or value <= 0 for value in self.speed_options):
            raise InvalidInputError(
                "Les rapports de vitesse doivent être strictement positifs et finis.",
                speed_options=self.speed_options,
            )
        if self.maximum_configurations <= 0:
            raise InvalidInputError(
                "La limite de configurations doit être strictement positive.",
                maximum_configurations=self.maximum_configurations,
            )
        if self.maximum_evaluations is not None and self.maximum_evaluations <= 0:
            raise InvalidInputError(
                "La limite d'évaluations doit être strictement positive.",
                maximum_evaluations=self.maximum_evaluations,
            )
        unknown_required = self.constraints.required_pump_ids - set(self.pump_ids)
        unknown_forbidden = self.constraints.forbidden_pump_ids - set(self.pump_ids)
        if unknown_required or unknown_forbidden:
            raise InvalidInputError(
                "Une contrainte cite une pompe absente de l'espace de recherche.",
                unknown_pump_ids=sorted(unknown_required | unknown_forbidden),
            )
        if self.objective_lower_bound is not None and not math.isfinite(self.objective_lower_bound):
            raise InvalidInputError("La borne inférieure de l'objectif doit être finie.")


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Candidat faisable, métriques et rang final."""

    rank: int
    configuration: PumpConfiguration
    evaluation: CandidateEvaluation
    objective_value: float


@dataclass(frozen=True, slots=True)
class RejectedCandidate:
    """Configuration non retenue et motifs vérifiables."""

    configuration: PumpConfiguration
    reasons: tuple[str, ...]
    evaluation: CandidateEvaluation | None = None


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Classement complet et informations d'optimalité."""

    status: OptimizationStatus
    ranked: tuple[RankedCandidate, ...]
    rejected: tuple[RejectedCandidate, ...]
    generated_count: int
    evaluated_count: int
    complete: bool
    optimality_gap: float | None
    solver_name: str = "enumeration_filtree"

    @property
    def best(self) -> RankedCandidate | None:
        return self.ranked[0] if self.ranked else None


CandidateEvaluator = Callable[[PumpConfiguration], CandidateEvaluation]


class ExhaustivePumpOptimizer:
    """Optimiseur déterministe par énumération filtrée."""

    def optimize(
        self,
        request: OptimizationRequest,
        evaluator: CandidateEvaluator,
    ) -> OptimizationResult:
        """Évalue, filtre et classe toutes les configurations autorisées."""

        configurations = tuple(self._generate_configurations(request))
        if len(configurations) > request.maximum_configurations:
            raise InvalidInputError(
                "L'espace combinatoire dépasse la limite configurée.",
                generated_count=len(configurations),
                maximum_configurations=request.maximum_configurations,
            )

        feasible: list[tuple[PumpConfiguration, CandidateEvaluation, float]] = []
        rejected: list[RejectedCandidate] = []
        evaluated_count = 0
        complete = True

        for index, configuration in enumerate(configurations):
            preflight = self._configuration_reasons(configuration, request.constraints)
            if preflight:
                rejected.append(RejectedCandidate(configuration=configuration, reasons=preflight))
                continue
            if (
                request.maximum_evaluations is not None
                and evaluated_count >= request.maximum_evaluations
            ):
                complete = False
                for remaining in configurations[index:]:
                    rejected.append(
                        RejectedCandidate(
                            configuration=remaining,
                            reasons=("Non évaluée : limite d'évaluations atteinte.",),
                        )
                    )
                break
            try:
                evaluation = evaluator(configuration)
            except HydroError as error:
                evaluated_count += 1
                rejected.append(
                    RejectedCandidate(
                        configuration=configuration,
                        reasons=(f"Évaluation impossible : {error}",),
                    )
                )
                continue
            evaluated_count += 1
            reasons = self._evaluation_reasons(configuration, evaluation, request.constraints)
            objective_error = self._objective_error(request, evaluation)
            if objective_error is not None:
                reasons = (*reasons, objective_error)
            if reasons:
                rejected.append(
                    RejectedCandidate(
                        configuration=configuration,
                        evaluation=evaluation,
                        reasons=reasons,
                    )
                )
                continue
            feasible.append(
                (
                    configuration,
                    evaluation,
                    self._objective_value(request, configuration, evaluation),
                )
            )

        feasible.sort(key=lambda item: (item[2], item[0].id))
        ranked = tuple(
            RankedCandidate(
                rank=rank,
                configuration=configuration,
                evaluation=evaluation,
                objective_value=objective_value,
            )
            for rank, (configuration, evaluation, objective_value) in enumerate(feasible, start=1)
        )

        if complete and ranked:
            status = OptimizationStatus.OPTIMAL
            gap = 0.0
        elif complete:
            status = OptimizationStatus.INFEASIBLE
            gap = None
        elif ranked:
            status = OptimizationStatus.STOPPED_WITH_SOLUTION
            gap = self._partial_gap(ranked[0].objective_value, request.objective_lower_bound)
        else:
            status = OptimizationStatus.STOPPED_WITHOUT_SOLUTION
            gap = None

        return OptimizationResult(
            status=status,
            ranked=ranked,
            rejected=tuple(rejected),
            generated_count=len(configurations),
            evaluated_count=evaluated_count,
            complete=complete,
            optimality_gap=gap,
        )

    @staticmethod
    def _generate_configurations(
        request: OptimizationRequest,
    ) -> Iterable[PumpConfiguration]:
        for mask in itertools.product((False, True), repeat=len(request.pump_ids)):
            active = tuple(
                pump_id for pump_id, enabled in zip(request.pump_ids, mask, strict=True) if enabled
            )
            if not active and not request.allow_no_pump:
                continue
            for speeds in itertools.product(request.speed_options, repeat=len(active)):
                yield PumpConfiguration(
                    active_pump_ids=active,
                    speed_ratios=tuple(zip(active, speeds, strict=True)),
                )

    @staticmethod
    def _configuration_reasons(
        configuration: PumpConfiguration,
        constraints: OptimizationConstraints,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        active = set(configuration.active_pump_ids)
        missing = constraints.required_pump_ids - active
        forbidden = constraints.forbidden_pump_ids & active
        if missing:
            reasons.append(f"Pompes obligatoires inactives : {', '.join(sorted(missing))}.")
        if forbidden:
            reasons.append(f"Pompes interdites actives : {', '.join(sorted(forbidden))}.")
        if (
            constraints.maximum_active_pumps is not None
            and configuration.active_pump_count > constraints.maximum_active_pumps
        ):
            reasons.append(
                f"{configuration.active_pump_count} pompes actives dépassent la limite "
                f"de {constraints.maximum_active_pumps}."
            )
        return tuple(reasons)

    @staticmethod
    def _evaluation_reasons(
        configuration: PumpConfiguration,
        evaluation: CandidateEvaluation,
        constraints: OptimizationConstraints,
    ) -> tuple[str, ...]:
        reasons = list(evaluation.rejection_reasons)
        if not evaluation.converged:
            reasons.append("Le calcul hydraulique n'a pas convergé.")
        if (
            constraints.minimum_flow_m3_s is not None
            and evaluation.flow_m3_s < constraints.minimum_flow_m3_s
        ):
            reasons.append(
                f"Débit {evaluation.flow_m3_s:.6g} m³/s inférieur au minimum "
                f"{constraints.minimum_flow_m3_s:.6g} m³/s."
            )
        if (
            constraints.maximum_flow_m3_s is not None
            and evaluation.flow_m3_s > constraints.maximum_flow_m3_s
        ):
            reasons.append(
                f"Débit {evaluation.flow_m3_s:.6g} m³/s supérieur au maximum "
                f"{constraints.maximum_flow_m3_s:.6g} m³/s."
            )
        if constraints.minimum_pressure_pa is not None:
            if evaluation.minimum_pressure_pa is None:
                reasons.append("Pression minimale non calculée.")
            elif evaluation.minimum_pressure_pa < constraints.minimum_pressure_pa:
                reasons.append(
                    f"Pression minimale {evaluation.minimum_pressure_pa:.6g} Pa sous la limite "
                    f"{constraints.minimum_pressure_pa:.6g} Pa."
                )
        if constraints.maximum_pressure_pa is not None:
            if evaluation.maximum_pressure_pa is None:
                reasons.append("Pression maximale non calculée.")
            elif evaluation.maximum_pressure_pa > constraints.maximum_pressure_pa:
                reasons.append(
                    f"Pression maximale {evaluation.maximum_pressure_pa:.6g} Pa au-dessus de la "
                    f"limite {constraints.maximum_pressure_pa:.6g} Pa."
                )
        if evaluation.violation_codes and not constraints.allow_violations:
            reasons.append(
                "Violations bloquantes : " + ", ".join(sorted(evaluation.violation_codes)) + "."
            )
        if configuration.active_pump_count == 0 and evaluation.flow_m3_s > 0:
            reasons.append("Un débit positif est incohérent sans pompe active.")
        return tuple(reasons)

    @staticmethod
    def _objective_error(
        request: OptimizationRequest,
        evaluation: CandidateEvaluation,
    ) -> str | None:
        if request.weights is not None:
            if request.weights.energy > 0 and evaluation.energy_kwh is None:
                return "Énergie absente pour l'objectif pondéré."
            if request.weights.cost > 0 and evaluation.cost is None:
                return "Coût absent pour l'objectif pondéré."
            return None
        if request.objective is ObjectiveKind.MIN_ENERGY and evaluation.energy_kwh is None:
            return "Énergie absente pour l'objectif choisi."
        if request.objective is ObjectiveKind.MIN_COST and evaluation.cost is None:
            return "Coût absent pour l'objectif choisi."
        return None

    @staticmethod
    def _objective_value(
        request: OptimizationRequest,
        configuration: PumpConfiguration,
        evaluation: CandidateEvaluation,
    ) -> float:
        if request.weights is not None:
            weights = request.weights
            return (
                weights.energy * (evaluation.energy_kwh or 0.0)
                + weights.cost * (evaluation.cost or 0.0)
                + weights.active_pumps * configuration.active_pump_count
                + weights.starts * evaluation.starts_count
                + weights.availability * evaluation.availability_penalty
                + weights.violations * len(evaluation.violation_codes)
            )
        if request.objective is ObjectiveKind.MIN_ENERGY:
            return evaluation.energy_kwh or 0.0
        if request.objective is ObjectiveKind.MIN_COST:
            return evaluation.cost or 0.0
        if request.objective is ObjectiveKind.MIN_PUMP_COUNT:
            return float(configuration.active_pump_count)
        if request.objective is ObjectiveKind.MIN_STARTS:
            return float(evaluation.starts_count)
        if request.objective is ObjectiveKind.MAX_FLOW:
            return -evaluation.flow_m3_s
        raise InvalidInputError(
            "Objectif d'optimisation non pris en charge.",
            objective=request.objective.value,
        )

    @staticmethod
    def _partial_gap(best_value: float, lower_bound: float | None) -> float | None:
        if lower_bound is None:
            return None
        denominator = max(abs(best_value), 1.0)
        return max((best_value - lower_bound) / denominator, 0.0)
