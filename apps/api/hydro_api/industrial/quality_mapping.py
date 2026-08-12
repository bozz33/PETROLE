"""Mapping explicite des qualités fournisseur vers le contrat PETROLE.

Aucun code inconnu n'est converti par défaut en ``good`` ou ``uncertain``. Le
mapping est versionné, traçable et conserve le code source pour permettre un
audit/reprocessing ultérieur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CanonicalQuality = Literal["good", "uncertain", "bad", "substituted", "estimated"]
_ALLOWED_QUALITIES: frozenset[str] = frozenset(
    {"good", "uncertain", "bad", "substituted", "estimated"}
)


@dataclass(frozen=True, slots=True)
class QualityMappingRule:
    """Correspondance revue d'un code qualité externe."""

    source_code: str
    target_quality: CanonicalQuality
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_code.strip():
            raise ValueError("Le code qualité source est obligatoire.")
        if self.target_quality not in _ALLOWED_QUALITIES:
            raise ValueError("La qualité cible n'appartient pas au contrat PETROLE.")
        if not self.source_ref.strip():
            raise ValueError("La provenance de la règle de qualité est obligatoire.")


@dataclass(frozen=True, slots=True)
class QualityMappingRegistry:
    """Table fournisseur/version sans règle de repli silencieuse."""

    provider: str
    version: str
    source_ref: str
    rules: tuple[QualityMappingRule, ...]

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.version.strip() or not self.source_ref.strip():
            raise ValueError("Fournisseur, version et provenance du mapping sont obligatoires.")
        if not self.rules:
            raise ValueError("Le registre de qualité doit contenir au moins une règle.")
        source_codes = [rule.source_code for rule in self.rules]
        if len(source_codes) != len(set(source_codes)):
            raise ValueError("Chaque code qualité source ne peut être mappé qu'une fois.")

    def map_quality(self, source_code: str) -> QualityMappingResult:
        """Résout un code exact ou refuse le point si le mapping n'est pas défini."""

        for rule in self.rules:
            if rule.source_code == source_code:
                return QualityMappingResult(
                    provider=self.provider,
                    registry_version=self.version,
                    source_code=source_code,
                    target_quality=rule.target_quality,
                    registry_source_ref=self.source_ref,
                    rule_source_ref=rule.source_ref,
                )
        raise KeyError(
            f"Code qualité externe non mappé pour {self.provider} version {self.version}: {source_code!r}."
        )


@dataclass(frozen=True, slots=True)
class QualityMappingResult:
    """Résultat réversible conservant qualité externe et règle utilisée."""

    provider: str
    registry_version: str
    source_code: str
    target_quality: CanonicalQuality
    registry_source_ref: str
    rule_source_ref: str


__all__ = [
    "CanonicalQuality",
    "QualityMappingRegistry",
    "QualityMappingResult",
    "QualityMappingRule",
]
