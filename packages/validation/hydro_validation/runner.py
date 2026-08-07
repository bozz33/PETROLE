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

    def scientific_payload(self) -> dict[str, Any]:
        """Retourne le contenu scientifique reproductible du dossier de preuve.

        Sont exclus l'horodatage, les durées et les caractéristiques de la machine
        (interpréteur, système, dépendances). Deux exécutions du même code sur le
        même dossier de cas produisent donc la même empreinte, ce qui permet de
        vérifier automatiquement l'attestation publiée par l'API.
        """

        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "passed": self.passed,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "versions": {
                key: self.environment.get(key)
                for key in (
                    "platform_version",
                    "engine_version",
                    "input_schema_version",
                    "result_schema_version",
                )
            },
            "cases": [case.scientific_payload() for case in self.cases],
        }

    def evidence_payload(self) -> dict[str, Any]:
        """Retourne le dossier complet, exécution et environnement compris."""

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

    @staticmethod
    def _digest(payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def proof_hash(self) -> str:
        """Empreinte reproductible des résultats scientifiques."""

        return self._digest(self.scientific_payload())

    @property
    def sha256(self) -> str:
        """Empreinte de cette exécution précise, horodatage et machine compris."""

        return self._digest(self.evidence_payload())

    def as_dict(self) -> dict[str, Any]:
        payload = self.evidence_payload()
        payload["proof_hash"] = self.proof_hash
        payload["sha256"] = self.sha256
        return payload

    def attestation(self, source: str) -> dict[str, Any]:
        """Construit l'attestation publiable par l'API à partir de cette exécution."""

        return {
            "suite": "scientific-validation",
            "passed": self.passed_count,
            "total": len(self.cases),
            "proof_hash": self.proof_hash,
            "engine_version": str(self.environment.get("engine_version", "inconnu")),
            "executed_at": self.finished_at,
            "environment": (
                f"python-{self.environment.get('python', 'inconnu')} "
                f"({self.environment.get('os', 'inconnu')})"
            ),
            "source": source,
        }


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
        f"- Empreinte reproductible des résultats : {result.proof_hash}",
        f"- Empreinte SHA-256 de l'exécution : {result.sha256}",
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
