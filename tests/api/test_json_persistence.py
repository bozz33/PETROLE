"""Tests PostgreSQL du contrat JSON strict de PETROLE."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session, sessionmaker

from hydro_api.database.base import utc_now
from hydro_api.models import AuditEvent
from hydro_shared.json_safety import normalize_json_numbers


def _audit_event(details: dict) -> AuditEvent:
    return AuditEvent(
        organization_id=None,
        action="test.json.strict",
        object_type="json_contract",
        object_id=uuid.uuid4(),
        details=details,
        created_at=utc_now(),
    )


def test_postgresql_refuse_un_nan_non_normalise(
    pg_session_factory: sessionmaker[Session],
) -> None:
    """Le sérialiseur SQLAlchemy bloque toute fuite non conforme à la RFC 8259.

    Avec psycopg3, le type JSONB traverse l'adaptateur ``Jsonb`` du pilote,
    qui appelle lui-même ``json.dumps`` (et lève ``ValueError`` pour un NaN).
    Suivant la version de SQLAlchemy et la configuration du dialecte, cette
    erreur peut remonter soit comme ``StatementError`` (SQLAlchemy encapsule),
    soit comme ``ValueError`` (psycopg3 la laisse passer hors d'un contexte
    DBAPI strict). Les deux prouvent que le NaN est refusé avant PostgreSQL,
    ce qui est le contrat vérifié ici.
    """

    with pg_session_factory() as session:
        session.add(_audit_event({"residual": float("nan")}))
        with pytest.raises((StatementError, ValueError)):
            session.flush()
        session.rollback()


def test_postgresql_persiste_une_valeur_non_finie_comme_null_apres_normalisation(
    pg_session_factory: sessionmaker[Session],
) -> None:
    """Le normaliseur conserve la trace et PostgreSQL reçoit un JSON valide."""

    normalized = normalize_json_numbers({"diagnostics": {"residual": float("nan")}})
    event = _audit_event(
        {
            "payload": normalized.value,
            "non_finite_values": [
                {"path": item.path, "kind": item.kind.value} for item in normalized.occurrences
            ],
        }
    )

    with pg_session_factory() as session:
        session.add(event)
        session.flush()
        event_id = event.id
        # Valide le SAVEPOINT de cette session. La transaction externe du test
        # reste ouverte et sera annulée par la fixture après le scénario.
        session.commit()

    with pg_session_factory() as session:
        persisted = session.get(AuditEvent, event_id)
        assert persisted is not None
        assert persisted.details["payload"]["diagnostics"]["residual"] is None
        assert persisted.details["non_finite_values"] == [
            {"path": "$.diagnostics.residual", "kind": "nan"}
        ]
