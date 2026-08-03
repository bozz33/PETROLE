"""Exécution du dossier de validation et production de sa preuve."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from hydro_shared import engine_fingerprint
from hydro_validation.cases import validation_cases
from hydro_validation.models import ValidationCase, ValidationCaseResult

VALIDATION_SCHEMA_VERSION = "hydro-validation/1"


@dataclass(frozen=True, slots=True)
class ValidationSuiteResult:
    """Résultat complet et sérialisable d'une campagne de validation."""

    started_at: str
    finished_at: str
    duration_s: float
    cases: tuple[ValidationCaseResult, ...]
    environment: dict[str, Any]

    @property
    def passed(self) -> bool:
        return bool(self.cases) and all(case.passed for case in self.cases)

    @property
    def passed_count(self) -> int:
        return sum(case.passed for case in self.cases)

    @property
    def failed_count(self) -> int:
        return len(self.cases) - self.passed_count

    def evidence_payload(self) -> dict[str, Any]:
        """Retourne le contenu stable utilisé pour calculer l'empreinte."""

        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": self.duration_s,
            "passed": self.passed,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "environment": self.environment,
            "cases": [case.as_dict() for case in self.cases],
        }

    @property
    def sha256(self) -> str:
        encoded = json.dumps(
            self.evidence_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        payload = self.evidence_payload()
        payload["sha256"] = self.sha256
        return payload


def select_cases(patterns: Iterable[str] | None = None) -> tuple[ValidationCase, ...]:
    """Sélectionne les cas par identifiant ou motif de type shell."""

    available = validation_cases()
    normalized = tuple(pattern.upper() for pattern in (patterns or ()))
    if not normalized:
        return available
    return tuple(
        case
        for case in available
        if any(fnmatch.fnmatchcase(case.id, pattern) for pattern in normalized)
    )


def run_validation_suite(
    patterns: Iterable[str] | None = None,
) -> ValidationSuiteResult:
    """Exécute les cas sélectionnés sans interrompre la campagne sur une exception."""

    selected = select_cases(patterns)
    if not selected:
        raise ValueError("Aucun cas ne correspond à la sélection demandée.")

    started = datetime.now(UTC)
    suite_start = time.perf_counter()
    results: list[ValidationCaseResult] = []

    for case in selected:
        case_start = time.perf_counter()
        try:
            observations = case.executor()
            error = None
        except Exception as exc:  # pragma: no cover - garde du dossier de preuve
            observations = ()
            error = f"{type(exc).__name__}: {exc}"
        results.append(
            ValidationCaseResult(
                case_id=case.id,
                title=case.title,
                category=case.category,
                reference=case.reference,
                observations=observations,
                duration_s=time.perf_counter() - case_start,
                error=error,
            )
        )

    finished = datetime.now(UTC)
    return ValidationSuiteResult(
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_s=time.perf_counter() - suite_start,
        cases=tuple(results),
        environment=engine_fingerprint(),
    )


def render_markdown(result: ValidationSuiteResult) -> str:
    """Produit un rapport Markdown autonome en français."""

    verdict = "VALIDÉ" if result.passed else "ÉCHEC"
    lines = [
        "# Rapport de validation scientifique",
        "",
        f"- Verdict : **{verdict}**",
        f"- Cas réussis : **{result.passed_count}/{len(result.cases)}**",
        f"- Début UTC : {result.started_at}",
        f"- Fin UTC : {result.finished_at}",
        f"- Durée : {result.duration_s:.6f} s",
        f"- Empreinte SHA-256 : {result.sha256}",
        "",
        "## Environnement",
        "",
        f"- Plateforme : {result.environment.get('platform_version', 'inconnue')}",
        f"- Moteur : {result.environment.get('engine_version', 'inconnu')}",
        f"- Python : {result.environment.get('python', 'inconnu')}",
        f"- Système : {result.environment.get('os', 'inconnu')}",
        "",
        "## Résultats",
        "",
        "| Cas | Catégorie | Verdict | Durée (s) | Référence |",
        "|---|---|---:|---:|---|",
    ]
    for case in result.cases:
        case_verdict = "Réussi" if case.passed else "Échec"
        lines.append(
            f"| {case.case_id} | {case.category} | {case_verdict} | "
            f"{case.duration_s:.6f} | {case.reference} |"
        )

    for case in result.cases:
        lines.extend(["", f"### {case.case_id} — {case.title}", ""])
        if case.error:
            lines.append(f"Erreur d'exécution : {case.error}")
            continue
        lines.extend(
            [
                "| Grandeur | Calculé | Attendu | Tolérance | Erreur absolue | Verdict |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for observation in case.observations:
            unit = f" {observation.unit}" if observation.unit else ""
            observation_verdict = "Réussi" if observation.passed else "Échec"
            lines.append(
                f"| {observation.name} | {observation.actual:.12g}{unit} | "
                f"{observation.expected:.12g}{unit} | "
                f"{observation.acceptance_limit:.6g}{unit} | "
                f"{observation.absolute_error:.6g}{unit} | {observation_verdict} |"
            )
            if observation.detail:
                lines.append(f"\nNote — {observation.name} : {observation.detail}\n")

    lines.extend(
        [
            "",
            "## Portée",
            "",
            "Ce rapport prouve uniquement les cas exécutés et les critères affichés. "
            "Il ne constitue ni une certification réglementaire ni une validation de site.",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "VALIDATION_SCHEMA_VERSION",
    "ValidationSuiteResult",
    "render_markdown",
    "run_validation_suite",
    "select_cases",
]
