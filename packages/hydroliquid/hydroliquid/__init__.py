"""HydroLiquid Core — noyau scientifique liquide de la plateforme.

Décision DEC-ENGINE-001 : *le moteur liquide principal est HydroLiquid Core, développé comme
une couche spécialisée assemblant NumPy, SciPy, ``fluids``, CoolProp, Pint et un adaptateur
pandapipes. Pandapipes n'est pas l'unique cœur scientifique.*

Le paquet est utilisable **sans le web ni la base de données** (NFR-MNT-005) :

.. code-block:: python

    from hydroliquid import LongDistanceLiquidEngine
    from hydro_domain import CanonicalInput

    moteur = LongDistanceLiquidEngine()
    resultat = moteur.simulate(entree_canonique)
    print(moteur.explain(resultat).summary)

Organisation
------------

======================  ====================================================================
Module                  Contenu
======================  ====================================================================
``hydraulics``          Reynolds, corrélations de frottement, pertes linéaires et singulières
``properties``          Fournisseurs de propriétés et adaptateur CoolProp
``solvers``             Encadrement, Brent, Newton amorti, méthode hybride journalisée
``checks``              Contrôles obligatoires C-001 à C-012
``engine``              Interface commune ``HydraulicEngine`` et registre de moteurs
``long_distance``       Moteur principal oléoduc longue distance
``pandapipes_adapter``  Moteur secondaire de comparaison, activé si la bibliothèque est là
======================  ====================================================================
"""

from hydroliquid.checks import CheckOutcome
from hydroliquid.engine import (
    Explanation,
    ExplanationEntry,
    HydraulicEngine,
    available_engines,
    get_engine,
    register_engine,
)
from hydroliquid.hydraulics import (
    LAMINAR_LIMIT_RE,
    TURBULENT_LIMIT_RE,
    G,
    flow_area_m2,
    flow_regime,
    friction_altshul,
    friction_colebrook_white,
    friction_factor,
    friction_haaland,
    friction_head_loss_m,
    friction_laminar,
    friction_swamee_jain,
    head_to_pressure_pa,
    hydraulic_gradient,
    is_transition_regime,
    minor_head_loss_m,
    pressure_to_head_m,
    reynolds,
    total_head_m,
    velocity_head_m,
    velocity_m_s,
)
from hydroliquid.long_distance import LongDistanceLiquidEngine
from hydroliquid.properties import CoolPropAdapter, FluidPropertyProvider, FluidState
from hydroliquid.solvers import (
    RootResult,
    bracket_root,
    brent,
    damped_newton,
    solve_hybrid,
    solve_monotonic,
)

# L'adaptateur pandapipes est facultatif : son import échoue proprement si la bibliothèque
# n'est pas installée, sans empêcher l'usage du moteur principal (DEC-ENGINE-002).
try:  # pragma: no cover - dépend de l'environnement
    from hydroliquid.pandapipes_adapter import PandapipesEngine as PandapipesEngine

    _PANDAPIPES = ["PandapipesEngine"]
except ImportError:  # pragma: no cover
    _PANDAPIPES = []

__all__ = [
    "G",
    "LAMINAR_LIMIT_RE",
    "TURBULENT_LIMIT_RE",
    "CheckOutcome",
    "CoolPropAdapter",
    "Explanation",
    "ExplanationEntry",
    "FluidPropertyProvider",
    "FluidState",
    "HydraulicEngine",
    "LongDistanceLiquidEngine",
    "RootResult",
    "available_engines",
    "bracket_root",
    "brent",
    "damped_newton",
    "flow_area_m2",
    "flow_regime",
    "friction_altshul",
    "friction_colebrook_white",
    "friction_factor",
    "friction_haaland",
    "friction_head_loss_m",
    "friction_laminar",
    "friction_swamee_jain",
    "get_engine",
    "head_to_pressure_pa",
    "hydraulic_gradient",
    "is_transition_regime",
    "minor_head_loss_m",
    "pressure_to_head_m",
    "register_engine",
    "reynolds",
    "solve_hybrid",
    "solve_monotonic",
    "total_head_m",
    "velocity_head_m",
    "velocity_m_s",
    *_PANDAPIPES,
]
