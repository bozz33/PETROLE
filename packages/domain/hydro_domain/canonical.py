"""Paquet d'entrée canonique d'un calcul.

Au lancement d'un calcul, les surcharges du scénario sont **matérialisées** dans un paquet
d'entrée canonique. Ce paquet reçoit une empreinte et reste accessible même si le catalogue
ou le scénario évoluent ensuite (D12 § 5 et § 12).

Le paquet est ce qui rend un résultat reproductible : rejouer le même paquet avec la même
version de moteur doit donner exactement le même résultat (NFR-SCI-002).

Sections du paquet (D12 § 12) : ``manifest``, ``units``, ``fluid``, ``network``,
``equipment``, ``boundary_conditions``, ``rules``, ``solver``, ``provenance``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from hydro_shared.hashing import sha256_of
from hydro_shared.units import SI_UNITS
from hydro_shared.versioning import (
    ENGINE_VERSION,
    INPUT_SCHEMA_VERSION,
    engine_fingerprint,
)

from hydro_domain.fluid import Fluid
from hydro_domain.pipeline import Pipeline
from hydro_domain.scenario import Scenario


@dataclass(frozen=True, slots=True)
class Provenance:
    """Origine du calcul : qui, quand, à partir de quoi."""

    requested_by: str | None = None
    requested_at: str | None = None
    project_id: str | None = None
    model_version_id: str | None = None
    organization_id: str | None = None
    client_reference: str | None = None
    source_files: tuple[str, ...] = ()

    @classmethod
    def now(cls, **kwargs: Any) -> Provenance:
        return cls(requested_at=datetime.now(UTC).isoformat(), **kwargs)

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "project_id": self.project_id,
            "model_version_id": self.model_version_id,
            "organization_id": self.organization_id,
            "client_reference": self.client_reference,
            "source_files": list(self.source_files),
        }


@dataclass(frozen=True, slots=True)
class CanonicalInput:
    """Entrées résolues et figées d'un calcul.

    L'empreinte :attr:`fingerprint` **exclut délibérément la provenance** : deux utilisateurs
    lançant le même calcul à deux instants différents doivent obtenir la même empreinte, afin
    que la déduplication et le cache de calculs fonctionnent (D13 § 10). La provenance reste
    conservée dans le paquet, mais hors du périmètre haché.
    """

    pipeline: Pipeline
    fluid: Fluid
    scenario: Scenario
    engine: str
    rule_set_ids: tuple[str, ...] = ()
    provenance: Provenance = field(default_factory=Provenance)
    schema_version: str = INPUT_SCHEMA_VERSION
    engine_version: str = ENGINE_VERSION

    # ------------------------------------------------------------------ sections

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "pipeline_id": self.pipeline.id,
            "fluid_id": self.fluid.id,
            "scenario_id": self.scenario.id,
        }

    @staticmethod
    def units() -> dict[str, str]:
        """Unités internes du paquet : SI, sans exception."""
        return {dimension.value: unit for dimension, unit in SI_UNITS.items()}

    def payload(self) -> dict[str, Any]:
        """Contenu haché du paquet : tout ce qui influence le résultat numérique."""
        return {
            "manifest": self.manifest(),
            "units": self.units(),
            "fluid": self.fluid.as_dict(),
            "network": self.pipeline.as_dict(),
            "boundary_conditions": [
                condition.as_dict() for condition in self.scenario.boundary_conditions
            ],
            "equipment_overrides": {
                "pumps": [o.as_dict() for o in self.scenario.pump_overrides],
                "stations": [o.as_dict() for o in self.scenario.station_overrides],
                "segments": [o.as_dict() for o in self.scenario.segment_overrides],
            },
            "scenario": self.scenario.as_dict(),
            "rules": {"rule_set_ids": list(self.rule_set_ids)},
            "solver": self.scenario.solver.as_dict(),
        }

    @property
    def fingerprint(self) -> str:
        """Empreinte SHA-256 des entrées, hors provenance."""
        return sha256_of(self.payload())

    def as_dict(self) -> dict[str, Any]:
        """Paquet complet, provenance et environnement inclus."""
        return {
            **self.payload(),
            "provenance": self.provenance.as_dict(),
            "environment": engine_fingerprint(),
            "input_hash": self.fingerprint,
        }

    def validate(self) -> list[str]:
        """Contrôles préalables au calcul : topologie et conditions aux limites.

        Retourne la liste des anomalies bloquantes. Une liste vide signifie que le paquet est
        calculable ; les contrôles physiques du résultat restent à la charge du moteur.
        """
        return [*self.pipeline.validate_topology(), *self.scenario.validate_boundary_conditions()]
