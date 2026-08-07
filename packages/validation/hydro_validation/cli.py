"""Commande de génération du dossier de validation scientifique."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from hydro_validation.cases import validation_cases
from hydro_validation.runner import render_markdown, run_validation_suite


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydro-validate",
        description="Exécute les cas scientifiques figés du MVP.",
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        metavar="MOTIF",
        help="Identifiant ou motif à exécuter, par exemple VAL-PMP-*.",
    )
    parser.add_argument("--report", type=Path, help="Chemin du rapport Markdown.")
    parser.add_argument("--json", type=Path, dest="json_path", help="Chemin de la preuve JSON.")
    parser.add_argument(
        "--attestation",
        type=Path,
        dest="attestation_path",
        help="Chemin de l'attestation publiée par l'API.",
    )
    parser.add_argument(
        "--attestation-source",
        default="packages/validation (exécution hydro-validate)",
        help="Référence documentaire citée par l'attestation.",
    )
    parser.add_argument("--list", action="store_true", help="Liste les cas sans les exécuter.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Exécute la commande et retourne un code exploitable par l'intégration continue."""

    args = _parser().parse_args(argv)
    if args.list:
        for case in validation_cases():
            print(f"{case.id}\t{case.title}")
        return 0

    try:
        result = run_validation_suite(args.cases)
    except ValueError as exc:
        print(f"Erreur : {exc}")
        return 2

    markdown = render_markdown(result)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown, encoding="utf-8")
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(
            json.dumps(result.as_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.attestation_path:
        args.attestation_path.parent.mkdir(parents=True, exist_ok=True)
        args.attestation_path.write_text(
            json.dumps(
                result.attestation(args.attestation_source),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    verdict = "VALIDÉ" if result.passed else "ÉCHEC"
    print(f"Validation {verdict} : {result.passed_count}/{len(result.cases)} cas réussis.")
    print(f"Empreinte reproductible : {result.proof_hash}")
    print(f"Empreinte d'exécution : {result.sha256}")
    if args.report:
        print(f"Rapport Markdown : {args.report}")
    if args.json_path:
        print(f"Preuve JSON : {args.json_path}")
    if args.attestation_path:
        print(f"Attestation publiée : {args.attestation_path}")
    return 0 if result.passed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
