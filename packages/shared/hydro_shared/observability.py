"""Journalisation structurée et corrélation.

Deux journaux distincts (NFR-OBS-001, NFR-OBS-003) :

- le **journal applicatif** (`app`) : requêtes, jobs, erreurs, événements de sécurité ;
- le **journal scientifique** (`science`) : méthode, itérations, résidus, corrélations,
  extrapolations et données utilisées.

Les journaux ne doivent contenir ni secret ni donnée sensible inutile (NFR-SEC-006) : les
clés listées dans :data:`REDACTED_KEYS` sont masquées avant écriture.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import structlog

#: Identifiant de corrélation propagé de la requête HTTP au processus différé puis au moteur (D13 § 3).
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
#: Identifiant du calcul en cours, présent dans tout le journal scientifique.
calculation_id_var: ContextVar[str | None] = ContextVar("calculation_id", default=None)
#: Organisation propriétaire, pour tracer l'isolation multi-organisation.
organization_id_var: ContextVar[str | None] = ContextVar("organization_id", default=None)

#: Clés dont la valeur ne doit jamais apparaître dans un journal.
REDACTED_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "api_key",
        "private_key",
        "client_secret",
    }
)

_REDACTED = "***"


def _inject_context(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key, var in (
        ("correlation_id", correlation_id_var),
        ("calculation_id", calculation_id_var),
        ("organization_id", organization_id_var),
    ):
        value = var.get()
        if value is not None and key not in event_dict:
            event_dict[key] = value
    return event_dict


def _redact(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict):
        if key.lower() in REDACTED_KEYS:
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging(*, json_output: bool = True, level: int = logging.INFO) -> None:
    """Configure structlog pour l'ensemble du processus.

    ``json_output=False`` produit une sortie lisible en développement local.
    """
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _inject_context,
        _redact,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app") -> Any:
    """Journal applicatif."""
    return structlog.get_logger(name)


def get_science_logger() -> Any:
    """Journal scientifique, distinct du journal applicatif."""
    return structlog.get_logger("science")


@contextmanager
def bound_context(
    *,
    correlation_id: str | None = None,
    calculation_id: str | None = None,
    organization_id: str | None = None,
) -> Iterator[None]:
    """Lie temporairement un contexte de corrélation au journal courant."""
    tokens = []
    if correlation_id is not None:
        tokens.append((correlation_id_var, correlation_id_var.set(correlation_id)))
    if calculation_id is not None:
        tokens.append((calculation_id_var, calculation_id_var.set(calculation_id)))
    if organization_id is not None:
        tokens.append((organization_id_var, organization_id_var.set(organization_id)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
