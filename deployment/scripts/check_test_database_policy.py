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
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_ROOT = REPO_ROOT / "tests"
CONFIG_FILES = (REPO_ROOT / "pyproject.toml",)

# Les programmes autonomes de tests/qualification/ sont des exécutables de
# recette (charge, import massif, concurrence worker) pilotés directement par
# qualify.sh et les scripts de recette. Ils ne font pas partie de la collection
# pytest, reçoivent HYDRO_DATABASE_URL d'une base jetable contrôlée externe et
# n'ouvrent aucune base embarquée. À ce titre ils relèvent de l'exception
# prévue par l'ADR-TEST-DB-001 (tests spécialisés d'infrastructure), et non des
# tests métier soumis au présent contrôle.
QUALIFICATION_ROOT = TESTS_ROOT / "qualification"

FORBIDDEN_IMPORTS = {
    "sqlite3": "L'import d'un moteur embarqué est interdit.",
    "sqlalchemy.create_engine": "Les moteurs sont fournis par les fixtures partagées.",
    "sqlalchemy.engine.create_engine": "Les moteurs sont fournis par les fixtures partagées.",
    "sqlalchemy.pool.StaticPool": "Le pool spécifique aux bases embarquées est interdit.",
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


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    """Construit la table des alias afin de détecter aussi les imports renommés."""

    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                local_name = imported.asname or imported.name.split(".", maxsplit=1)[0]
                aliases[local_name] = imported.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for imported in node.names:
                if imported.name == "*":
                    continue
                local_name = imported.asname or imported.name
                aliases[local_name] = f"{module}.{imported.name}" if module else imported.name
    return aliases


def _qualified_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value, aliases)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _string_values(tree: ast.AST) -> Iterator[ast.Constant]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node


def _check_imports(path: Path, tree: ast.AST) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(tree):
        imported_names: list[str] = []
        if isinstance(node, ast.Import):
            imported_names = [item.name for item in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_names = [
                f"{module}.{item.name}" if module else item.name
                for item in node.names
                if item.name != "*"
            ]

        for imported_name in imported_names:
            reason = FORBIDDEN_IMPORTS.get(imported_name)
            if reason:
                violations.append(Violation(path, node.lineno, reason))
    return violations


def _check_python(path: Path) -> list[Violation]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        return [Violation(path, 1, f"Fichier impossible à analyser : {error}")]

    aliases = _import_aliases(tree)
    violations = _check_imports(path, tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        call_name = _qualified_name(node.func, aliases) or ""
        if call_name == "create_engine" or call_name.endswith(".create_engine"):
            violations.append(
                Violation(path, node.lineno, "Les moteurs sont fournis par les fixtures partagées.")
            )
        if call_name == "text" or call_name.endswith(".text"):
            violations.append(
                Violation(
                    path, node.lineno, "Le SQL textuel est interdit dans les fichiers de test."
                )
            )

        if not isinstance(node.func, ast.Attribute):
            continue

        owner_name = _qualified_name(node.func.value, aliases) or ""
        if node.func.attr in FORBIDDEN_METADATA_METHODS and (
            owner_name == "metadata" or owner_name.endswith(".metadata")
        ):
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    "Le schéma de test doit être créé exclusivement par Alembic.",
                )
            )

        if node.func.attr in {"execute", "exec_driver_sql"} and node.args:
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                violations.append(
                    Violation(
                        path,
                        node.lineno,
                        "Une chaîne SQL brute est interdite dans les tests.",
                    )
                )
            if isinstance(argument, ast.Call):
                argument_name = _qualified_name(argument.func, aliases) or ""
                if argument_name == "text" or argument_name.endswith(".text"):
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
                Violation(path, line_number, "Dépendance ou configuration embarquée interdite.")
            )
    return violations


def main() -> int:
    violations: list[Violation] = []
    for path in sorted(TESTS_ROOT.rglob("*.py")):
        if QUALIFICATION_ROOT in path.parents:
            continue
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
