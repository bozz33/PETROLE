"""Contrat CoolProp partagé pour mélanges gazeux explicitement composés.

Cette brique ne choisit aucune composition ni aucun backend. Elle relie une
``GasComposition`` PETROLE à des identifiants de fluides CoolProp simples et
conserve la provenance du mélange et du mapping. Les adaptateurs scientifiques
peuvent ensuite construire leur propre ``AbstractState`` à partir de ce contrat.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.composition import GasComposition


@dataclass(frozen=True, slots=True)
class CoolPropGasMixtureComponentBinding:
    """Correspondance explicite entre un composant PETROLE et un fluide CoolProp."""

    composition_component: str
    coolprop_fluid: str

    def __post_init__(self) -> None:
        if not self.composition_component.strip() or not self.coolprop_fluid.strip():
            raise ValueError("Le composant PETROLE et son identifiant CoolProp sont obligatoires.")
        forbidden = ("::", "&", "[", "]")
        if any(
            token in self.coolprop_fluid for token in forbidden
        ) or self.coolprop_fluid.lower().endswith(".mix"):
            raise ValueError(
                "Un binding de composant doit viser un fluide CoolProp simple, sans syntaxe de mélange."
            )


@dataclass(frozen=True, slots=True)
class CoolPropGasMixtureDefinition:
    """Mélange CoolProp construit à partir d'une composition molaire traçable."""

    composition: GasComposition
    component_bindings: tuple[CoolPropGasMixtureComponentBinding, ...]
    backend: str
    source_ref: str
    mapping_source_ref: str

    def __post_init__(self) -> None:
        required = (self.backend, self.source_ref, self.mapping_source_ref)
        if any(not value.strip() for value in required):
            raise ValueError(
                "Le backend, la provenance du mélange et la provenance du mapping sont obligatoires."
            )
        if "::" in self.backend:
            raise ValueError("Le backend CoolProp doit être fourni sans séparateur '::'.")
        if not self.component_bindings:
            raise ValueError("Le mélange CoolProp exige un binding pour chaque composant.")

        composition_names = tuple(component.component for component in self.composition.components)
        binding_names = tuple(binding.composition_component for binding in self.component_bindings)
        if len(binding_names) != len(set(binding_names)):
            raise ValueError("Les composants PETROLE du mapping CoolProp doivent être uniques.")
        if set(binding_names) != set(composition_names):
            raise ValueError(
                "Le mapping CoolProp doit couvrir exactement les composants de la composition gaz."
            )

        coolprop_names = tuple(binding.coolprop_fluid for binding in self.component_bindings)
        if len(coolprop_names) != len(set(coolprop_names)):
            raise ValueError("Chaque composant PETROLE doit viser un fluide CoolProp distinct.")

    @property
    def composition_component_names(self) -> tuple[str, ...]:
        return tuple(component.component for component in self.composition.components)

    @property
    def coolprop_component_names(self) -> tuple[str, ...]:
        by_component = {
            binding.composition_component: binding.coolprop_fluid
            for binding in self.component_bindings
        }
        return tuple(by_component[name] for name in self.composition_component_names)

    @property
    def mole_fractions(self) -> tuple[float, ...]:
        return tuple(component.mole_fraction for component in self.composition.components)

    @property
    def component_key(self) -> str:
        """Clé de composants attendue par ``AbstractState`` (fractions séparées)."""

        return "&".join(self.coolprop_component_names)

    @property
    def fluid_name(self) -> str:
        """Identité déterministe backend/composants pour la restitution PETROLE."""

        return f"{self.backend}::{self.component_key}"


__all__ = [
    "CoolPropGasMixtureComponentBinding",
    "CoolPropGasMixtureDefinition",
]
