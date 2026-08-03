"""Configuration commune de la suite de tests.

Le répertoire ``tests`` est ajouté au chemin d'import afin que le module de fabriques
:mod:`tests.factories` soit accessible depuis n'importe quel fichier de test, quel que soit
son sous-répertoire.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))
