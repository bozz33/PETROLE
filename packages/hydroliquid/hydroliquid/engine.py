"""Interface commune des moteurs hydrauliques.

Décision structurante ([ADR-003](../../../docs/adr/adr-003-moteurs-derriere-interfaces.md),
D-v2 § 5.7) : *tous les moteurs implémentent la même interface*. Cela permet de comparer deux
moteurs sur un même cas, d'en remplacer un sans toucher au produit, et d'éviter toute
dépendance irréversible à une bibliothèque tierce.

.. code-block:: python

    class HydraulicEngine:
        def validate(self, canonical_input) -> ValidationReport: ...
        def simulate(self, canonical_input) -> SimulationResult: ...
        def explain(self, result) -> Explanation: ...

Implémentations du MVP :

- :class:`~hydroliquid.long_distance.LongDistanceLiquidEngine` — moteur principal oléoduc ;
- :class:`~hydroliquid.pandapipes_adapter.PandapipesEngine` — adaptateur de comparaison, activé
  seulement si la bibliothèque est installée et si le cas est compatible.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from hydro_domain.canonical import CanonicalInput
from hydro_domain.results import SimulationResult
from hydro_shared.diagnostics import ValidationReport


@dataclass(frozen=True, slots=True)
class ExplanationEntry:
    """Élément d'explication : une affirmation, sa justification et sa source."""

    title: str
    detail: str
    reference: str | None = None
    values: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "detail": self.detail,
            "reference": self.reference,
            "values": self.values,
        }


@dataclass(frozen=True, slots=True)
class Explanation:
    """Explication structurée d'un résultat, destinée à l'interface et à la note de calcul.

    Exigence D-v2 § 12.2 : *localisation et explication de chaque violation*. L'explication
    n'est pas un commentaire libre : elle relie chaque conclusion aux hypothèses, aux méthodes
    et aux valeurs qui l'ont produite, afin qu'un ingénieur puisse la contester point par
    point.
    """

    summary: str
    feasible: bool
    approvable: bool
    assumptions: tuple[ExplanationEntry, ...] = ()
    methods: tuple[ExplanationEntry, ...] = ()
    findings: tuple[ExplanationEntry, ...] = ()
    limitations: tuple[ExplanationEntry, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "feasible": self.feasible,
            "approvable": self.approvable,
            "assumptions": [e.as_dict() for e in self.assumptions],
            "methods": [e.as_dict() for e in self.methods],
            "findings": [e.as_dict() for e in self.findings],
            "limitations": [e.as_dict() for e in self.limitations],
        }


class HydraulicEngine(ABC):
    """Contrat que tout moteur hydraulique doit respecter."""

    #: Identifiant stable du moteur, enregistré dans le résultat et dans l'empreinte.
    name: str = "abstract"
    #: Version du moteur, indépendante de la version de l'application (D18 § 11).
    version: str = "0.0.0"

    @abstractmethod
    def validate(self, canonical_input: CanonicalInput) -> ValidationReport:
        """Contrôle les entrées **avant** tout calcul.

        Un rapport invalide interdit le lancement : aucun calcul n'est engagé sur des données
        dont on sait déjà qu'elles produiront un résultat sans signification.
        """

    @abstractmethod
    def simulate(self, canonical_input: CanonicalInput) -> SimulationResult:
        """Exécute la simulation et retourne un résultat immuable.

        Le moteur ne lève pas d'exception pour une non-convergence ou une absence de solution
        physique : il retourne un résultat portant le statut correspondant et les diagnostics
        associés (D13 § 9). Les exceptions sont réservées aux entrées invalides.
        """

    @abstractmethod
    def explain(self, result: SimulationResult) -> Explanation:
        """Produit l'explication structurée d'un résultat déjà calculé."""

    def supports(self, canonical_input: CanonicalInput) -> bool:
        """Indique si le moteur couvre ce cas.

        Utilisé par l'orchestrateur pour proposer une comparaison croisée uniquement sur les
        cas réellement compatibles (D-v2 § 7.3).
        """
        return True

    def __repr__(self) -> str:  # pragma: no cover - confort de débogage
        return f"{type(self).__name__}(name={self.name!r}, version={self.version!r})"


#: Registre des moteurs disponibles, alimenté par :func:`register_engine`.
_ENGINE_REGISTRY: dict[str, type[HydraulicEngine]] = {}


def register_engine(engine_class: type[HydraulicEngine]) -> type[HydraulicEngine]:
    """Enregistre un moteur dans le registre, utilisable comme décorateur."""
    _ENGINE_REGISTRY[engine_class.name] = engine_class
    return engine_class


def get_engine(name: str) -> HydraulicEngine:
    """Instancie un moteur par son nom.

    Lève :class:`KeyError` avec la liste des moteurs disponibles si le nom est inconnu :
    une faute de frappe dans une requête d'API ne doit pas produire un repli silencieux sur
    un autre moteur.
    """
    if name not in _ENGINE_REGISTRY:
        available = ", ".join(sorted(_ENGINE_REGISTRY)) or "aucun"
        raise KeyError(f"Moteur inconnu : {name!r}. Moteurs disponibles : {available}.")
    return _ENGINE_REGISTRY[name]()


def available_engines() -> tuple[str, ...]:
    """Noms des moteurs enregistrés."""
    return tuple(sorted(_ENGINE_REGISTRY))
