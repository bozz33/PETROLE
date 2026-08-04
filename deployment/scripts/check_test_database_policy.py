#!/usr/bin/env python3
"""Vérifie la politique PostgreSQL des tests (ADR-TEST-DB-001).

Le contrôle repose sur l'AST Python afin d'éviter les faux positifs des simples
recherches de texte. Les fichiers de test ne peuvent pas :

* importer ou configurer une base embarquée ;
* créer leur propre moteur SQLAlchemy ;
* créer ou supprimer le schéma avec ``metadata.create_all/drop_all`` ;
* exécuter du SQL textuel ;
* embarquer une URL de développement, recette ou production.

Les opérations PostgreSQL indispensables à l'infrastructure sont centralisées
hors de ``tests/`` dans ``hydro_shared.testing.postgres`` et sont protégées par
une vérification stricte du suffixe ``_test``.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_ROOT = REPO_ROOT / "tests"
CONFIG_FILES = (REPO_ROOT / "pyproject.toml",)

FORBIDDEN_MODULES = {
    "sqlite3",
    "sqlalchemy.pool.StaticPool",
}
FORBIDDEN_CALLS = {
    "create_engine": "Les moteurs sont fournis par les fixtures partagées.",
    "sqlalchemy.create_engine": "Les moteurs sont fournis par les fixtures partagées.",
    "sqlalchemy.engine.create_engine": "Les moteurs sont fournis par les fixtures partagées.",
    "text": "Le SQL textuel est interdit dans les fichiers de test.",
    "sqlalchemy.text": "Le SQL textuel est interdit dans les fichiers de test.",
}
FORBIDDEN_METADATA_METHODS = {"create_all", "drop_all"}
FORBIDDEN_TEXT_FRAGMENTS = {
    "sqlite": "Moteur embarqué interdit.",
    "pysqlite": "Pilote embarqué interdit.",
    ":memory:": "Base en mémoire interdite.",
    "check_same_thread": "Option spécifique à une base embarquée interdite.",
    "hydro_dev": "Identifiants de la base de développement interdits dans les tests.",
    "@postgres:5432/hydro": "Base de développement interdite dans les tests.",
}


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path.relative_to(REPO_ROOT)}:{self.line}: {self.message}"


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _string_values(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node


def _check_python(path: Path) -> list[Violation]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        return [Violation(path, 1, f"Fichier impossible à analyser : {error}")]

    violations: list[Violation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sqlite3":
                    violations.append(
                        Violation(path, node.lineno, "L'import sqlite3 est interdit.")
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                qualified = f"{module}.{alias.name}" if module else alias.name
                if qualified in FORBIDDEN_MODULES or alias.name == "StaticPool":
                    violations.append(
                        Violation(path, node.lineno, f"Import interdit : {qualified}.")
                    )
        elif isinstance(node, ast.Call):
            call_name = _qualified_name(node.func) or ""
            if call_name in FORBIDDEN_CALLS:
                violations.append(
                    Violation(path, node.lineno, FORBIDDEN_CALLS[call_name])
                )
            if isinstance(node.func, ast.Attribute):
                if (
                    node.func.attr in FORBIDDEN_METADATA_METHODS
                    and _qualified_name(node.func.value) in {"Base.metadata", "metadata"}
                ):
                    violations.append(
                        Violation(
                            path,
                            node.lineno,
                            "Le schéma de test doit être créé exclusivement par Alembic.",
                        )
                    )
                if node.func.attr == "execute" and node.args:
                    argument = node.args[0]
                    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                        violations.append(
                            Violation(
                                path,
                                node.lineno,
                                "Une chaîne SQL brute est interdite dans les tests.",
                            )
                        )
                    if isinstance(argument, ast.Call) and _qualified_name(argument.func) in {
                        "text",
                        "sqlalchemy.text",
                    }:
                        violations.append(
                            Violation(
                                path,
                                node.lineno,
                                "SQLAlchemy text() est interdit dans les tests.",
                            )
                        )

    for node in _string_values(tree):
        lowered = node.value.lower()
        for fragment, reason in FORBIDDEN_TEXT_FRAGMENTS.items():
            if fragment.lower() in lowered:
                violations.append(Violation(path, node.lineno, reason))

    return violations


def _check_configuration(path: Path) -> list[Violation]:
    if not path.exists():
        return []
    violations: list[Violation] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        lowered = line.lower()
        if "sqlite" in lowered or "pysqlite" in lowered:
            violations.append(
                Violation(path, line_number, "Dépendance ou configuration SQLite interdite.")
            )
    return violations


def main() -> int:
    violations: list[Violation] = []
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        violations.extend(_check_python(path))
    for path in CONFIG_FILES:
        violations.extend(_check_configuration(path))

    if violations:
        print(f"POLITIQUE POSTGRESQL VIOLÉE — {len(violations)} anomalie(s) :")
        for violation in sorted(violations, key=lambda item: (str(item.path), item.line)):
            print(f"  {violation.render()}")
        return 1

    print("Politique PostgreSQL des tests respectée : aucun moteur embarqué ni SQL brut.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
