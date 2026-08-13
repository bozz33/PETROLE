"""Contrat P6-B des modèles constitutifs de conduite gaz.

Cette couche ne contient aucune équation de perte de charge et ne calcule ni
pression, ni débit. Elle rend obligatoire la sélection explicite d'un modèle,
de sa version, de son domaine, de ses hypothèses et de son jeu de paramètres
avant qu'un futur solveur stationnaire puisse l'utiliser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from hydro_gas.network_balance import SteadyGasNetwork

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GasConstitutiveQualification(StrEnum):
    """État de qualification technique, sans signification de certification."""

    DECLARED = "declared"
    BENCHMARK_READY = "benchmark_ready"
    BENCHMARKED = "benchmarked"


@dataclass(frozen=True, slots=True)
class GasPipeConstitutiveModelDescriptor:
    """Description versionnée d'une formulation, sans reproduire son équation."""

    model_id: str
    version: str
    formulation_ref: str
    equation_ref: str
    source_ref: str
    parameter_schema_ref: str
    domain_refs: tuple[str, ...]
    assumptions: tuple[str, ...]
    qualification: GasConstitutiveQualification = GasConstitutiveQualification.DECLARED
    qualification_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        required = (
            self.model_id,
            self.version,
            self.formulation_ref,
            self.equation_ref,
            self.source_ref,
            self.parameter_schema_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Le modèle constitutif, sa version, sa formulation, son équation, "
                "sa source et son schéma de paramètres sont obligatoires."
            )

        domains = tuple(dict.fromkeys(value.strip() for value in self.domain_refs if value.strip()))
        assumptions = tuple(
            dict.fromkeys(value.strip() for value in self.assumptions if value.strip())
        )
        evidence = tuple(
            dict.fromkeys(
                value.strip() for value in self.qualification_evidence_refs if value.strip()
            )
        )
        if not domains:
            raise ValueError("Au moins une référence de domaine de validité est obligatoire.")
        if not assumptions:
            raise ValueError("Les hypothèses du modèle constitutif doivent être explicites.")
        if self.qualification is GasConstitutiveQualification.BENCHMARKED and not evidence:
            raise ValueError("Un modèle déclaré benchmarked doit référencer ses preuves.")

        object.__setattr__(self, "domain_refs", domains)
        object.__setattr__(self, "assumptions", assumptions)
        object.__setattr__(self, "qualification_evidence_refs", evidence)

    @property
    def key(self) -> tuple[str, str]:
        return self.model_id, self.version


@dataclass(frozen=True, slots=True)
class GasPipeConstitutiveBinding:
    """Lien entre une conduite et un jeu de paramètres d'un modèle précis."""

    pipe_id: str
    model_id: str
    model_version: str
    parameter_set_ref: str
    parameter_set_sha256: str
    geometry_ref: str
    gas_property_ref: str
    source_ref: str

    def __post_init__(self) -> None:
        required = (
            self.pipe_id,
            self.model_id,
            self.model_version,
            self.parameter_set_ref,
            self.geometry_ref,
            self.gas_property_ref,
            self.source_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "La conduite, le modèle, le jeu de paramètres, la géométrie, "
                "les propriétés gaz et la provenance sont obligatoires."
            )
        normalized_hash = self.parameter_set_sha256.strip().lower()
        if not _SHA256_RE.fullmatch(normalized_hash):
            raise ValueError(
                "L'empreinte du jeu de paramètres doit être un SHA-256 hexadécimal de 64 caractères."
            )
        object.__setattr__(self, "parameter_set_sha256", normalized_hash)

    @property
    def model_key(self) -> tuple[str, str]:
        return self.model_id, self.model_version


@dataclass(frozen=True, slots=True)
class GasConstitutiveManifest:
    """Sélection documentaire de modèles et paramètres pour un réseau donné."""

    descriptors: tuple[GasPipeConstitutiveModelDescriptor, ...]
    bindings: tuple[GasPipeConstitutiveBinding, ...]
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance du manifeste constitutif est obligatoire.")
        if not self.descriptors:
            raise ValueError("Le manifeste doit déclarer au moins un modèle constitutif.")

        descriptor_keys = tuple(descriptor.key for descriptor in self.descriptors)
        if len(descriptor_keys) != len(set(descriptor_keys)):
            raise ValueError("Les couples modèle/version du manifeste doivent être uniques.")

        pipe_ids = tuple(binding.pipe_id for binding in self.bindings)
        if len(pipe_ids) != len(set(pipe_ids)):
            raise ValueError("Une conduite ne peut avoir qu'un binding constitutif actif.")


@dataclass(frozen=True, slots=True)
class GasConstitutiveManifestAssessment:
    """Diagnostic factuel ; aucun seuil de conformité industrielle n'est déduit."""

    complete: bool
    benchmark_ready: bool
    violations: tuple[str, ...]
    unbound_pipe_ids: tuple[str, ...]
    unknown_pipe_ids: tuple[str, ...]
    unknown_model_keys: tuple[tuple[str, str], ...]
    not_benchmark_ready_model_keys: tuple[tuple[str, str], ...]


def assess_constitutive_manifest(
    network: SteadyGasNetwork,
    manifest: GasConstitutiveManifest,
) -> GasConstitutiveManifestAssessment:
    """Vérifie couverture et qualification sans exécuter de physique.

    ``benchmark_ready`` signifie uniquement que le manifeste est complet et que
    chaque modèle sélectionné est au moins explicitement préparé pour un
    benchmark. Il ne signifie ni validation industrielle, ni certification.
    """

    network_pipe_ids = {pipe.pipe_id for pipe in network.pipes}
    bindings_by_pipe = {binding.pipe_id: binding for binding in manifest.bindings}
    binding_pipe_ids = set(bindings_by_pipe)
    descriptors_by_key = {descriptor.key: descriptor for descriptor in manifest.descriptors}

    unbound = tuple(sorted(network_pipe_ids - binding_pipe_ids))
    unknown_pipes = tuple(sorted(binding_pipe_ids - network_pipe_ids))
    unknown_models = tuple(
        sorted(
            {
                binding.model_key
                for binding in manifest.bindings
                if binding.model_key not in descriptors_by_key
            }
        )
    )

    selected_known_keys = {
        binding.model_key
        for binding in manifest.bindings
        if binding.model_key in descriptors_by_key
    }
    not_ready = tuple(
        sorted(
            key
            for key in selected_known_keys
            if descriptors_by_key[key].qualification is GasConstitutiveQualification.DECLARED
        )
    )

    violations: list[str] = []
    violations.extend(f"unbound_pipe:{pipe_id}" for pipe_id in unbound)
    violations.extend(f"unknown_pipe:{pipe_id}" for pipe_id in unknown_pipes)
    violations.extend(
        f"unknown_model:{model_id}@{version}" for model_id, version in unknown_models
    )
    violations.extend(
        f"model_not_benchmark_ready:{model_id}@{version}"
        for model_id, version in not_ready
    )

    complete = not unbound and not unknown_pipes and not unknown_models
    return GasConstitutiveManifestAssessment(
        complete=complete,
        benchmark_ready=complete and not not_ready,
        violations=tuple(violations),
        unbound_pipe_ids=unbound,
        unknown_pipe_ids=unknown_pipes,
        unknown_model_keys=unknown_models,
        not_benchmark_ready_model_keys=not_ready,
    )


__all__ = [
    "GasConstitutiveManifest",
    "GasConstitutiveManifestAssessment",
    "GasConstitutiveQualification",
    "GasPipeConstitutiveBinding",
    "GasPipeConstitutiveModelDescriptor",
    "assess_constitutive_manifest",
]
