#!/usr/bin/env python3
"""Controle automatique de la politique de base de donnees (ADR-TEST-DB-001).

Analyse tous les fichiers Python du depot et echoue si l'un des motifs
interdits est present :

* ``sqlite``, ``pysqlite``, ``sqlite3`` — moteur SQLite
* ``:memory:`` — base en memoire SQLite
* ``StaticPool``, ``check_same_thread`` — configuration specifique a SQLite
* ``Base.metadata.create_all`` — contourne Alembic
* ``sqlalchemy.text(``, ``session.execute("`` — SQL brut dans les tests

Ce script doit etre execute avant pytest dans la qualification.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Motifs interdits et leur justification.
FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("sqlite", "SQLite interdit par ADR-TEST-DB-001"),
    ("pysqlite", "SQLite interdit par ADR-TEST-DB-001"),
    ("sqlite3", "SQLite interdit par ADR-TEST-DB-001"),
    (":memory:", "Base SQLite en memoire interdite"),
    ("StaticPool", "Configuration SQLite interdite"),
    ("check_same_thread", "Configuration SQLite interdite"),
    ("Base.metadata.create_all", "Contourne Alembic, interdit"),
    ("sqlalchemy.text(", "SQL brut interdit dans les tests"),
    ('session.execute("', "SQL brut interdit dans les tests"),
    ('connection.execute("', "SQL brut interdit dans les tests"),
]

# Chemins a exclure de l'analyse.
EXCLUDED_DIRS: set[str] = {
    "__pycache__",
    ".venv",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
}

# Fichiers autorises a mentionner sqlite dans leurs commentaires/documentation.
ALLOWED_COMMENT_FILES: set[str] = {
    "packages/shared/hydro_shared/json_safety.py",
    "deployment/scripts/check_test_database_policy.py",
    "apps/api/hydro_api/models/core.py",  # parametre sqlite_where, pas SQLite
}


def _check_file(filepath: Path) -> list[str]:
    """Verifie un fichier et retourne les violations trouvees."""

    violations: list[str] = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    rel = str(filepath.relative_to(REPO_ROOT))

    for pattern, reason in FORBIDDEN_PATTERNS:
        if pattern not in content:
            continue
        # Autoriser les mentions dans les commentaires/documentation
        if rel in ALLOWED_COMMENT_FILES:
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            if pattern in line:
                violations.append(f"{rel}:{lineno}: {pattern} — {reason}")
                break  # Une violation par pattern suffit

    return violations


def main() -> int:
    violations: list[str] = []

    for py_file in REPO_ROOT.rglob("*.py"):
        parts = set(py_file.parts)
        if parts & EXCLUDED_DIRS:
            continue
        if "test" not in str(py_file) and "test" not in py_file.parts:
            # On ne verifie que les fichiers de test et le code applicatif
            pass
        file_violations = _check_file(py_file)
        violations.extend(file_violations)

    # Ajouter aussi la verification des fichiers non-Python (config, etc.)
    for extra in ["pyproject.toml", "alembic.ini"]:
        extra_path = REPO_ROOT / extra
        if extra_path.exists():
            violations.extend(_check_file(extra_path))

    if violations:
        print(f"POLITIQUE VIOLÉE — {len(violations)} occurrence(s) interdite(s) :")
        for v in sorted(violations):
            print(f"  {v}")
        return 1

    print("Politique « zéro SQLite » respectée.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
