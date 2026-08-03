"""Constructeurs de cas d'essai réutilisables par les tests.

Ces fabriques produisent des objets du domaine cohérents et minimalement paramétrés, afin que
chaque test n'exprime que ce qui le distingue. Elles ne contiennent aucune logique de calcul :
un test qui échouerait à cause d'une fabrique révélerait un problème de modèle, pas de moteur.
"""

from __future__ import annotations

from collections.abc import Sequence

from hydro_domain import (
    CanonicalInput,
    ElevationProfile,
    Fitting,
    Fluid,
    FluidCategory,
    Pipeline,
    PipeSegment,
    PumpCurve,
    PumpInstance,
    PumpModel,
    PumpStation,
    Scenario,
    SolverOptions,
    StrappingTable,
    Tank,
    TankLevels,
    build_parallel_station,
    build_series_station,
)

#: Pression atmosphérique normale, utilisée comme référence des pressions absolues.
ATMOSPHERE_PA = 101_325.0


def brut_leger(**kwargs) -> Fluid:
    """Pétrole brut léger : ρ = 875 kg/m³, ν = 9 cSt, p_v = 10 kPa.

    Ces valeurs sont celles du cas académique de 460 km conservé comme benchmark (D10 § 5).
    """
    defaults = {
        "id": "brut-leger",
        "name": "Pétrole brut léger",
        "category": FluidCategory.CRUDE,
        "density_kg_m3": 875.0,
        "kinematic_viscosity_m2_s": 9.0e-6,
        "vapor_pressure_pa": 1.0e4,
        "data_source": "Jeu d'essai interne",
    }
    return Fluid(**{**defaults, **kwargs})


def gasoil(**kwargs) -> Fluid:
    """Gasoil commercial : ρ = 840 kg/m³, ν = 4 cSt, p_v = 500 Pa."""
    defaults = {
        "id": "gasoil",
        "name": "Gasoil",
        "category": FluidCategory.DIESEL,
        "density_kg_m3": 840.0,
        "kinematic_viscosity_m2_s": 4.0e-6,
        "vapor_pressure_pa": 500.0,
        "data_source": "Jeu d'essai interne",
    }
    return Fluid(**{**defaults, **kwargs})


def segment(
    identifiant: str = "T1",
    sequence: int = 1,
    longueur_m: float = 50_000.0,
    diametre_m: float = 0.5,
    depart_m: float = 0.0,
    **kwargs,
) -> PipeSegment:
    defaults = {
        "id": identifiant,
        "sequence": sequence,
        "length_m": longueur_m,
        "inner_diameter_m": diametre_m,
        "roughness_m": 4.5e-5,
        "start_chainage_m": depart_m,
        "maop_pa": 8.0e6,
    }
    return PipeSegment(**{**defaults, **kwargs})


def chaine_de_troncons(
    longueurs_m: Sequence[float], diametre_m: float = 0.5, **kwargs
) -> tuple[PipeSegment, ...]:
    """Chaîne continue de tronçons de longueurs données."""
    segments: list[PipeSegment] = []
    depart = 0.0
    for index, longueur in enumerate(longueurs_m, start=1):
        segments.append(
            segment(
                identifiant=f"T{index}",
                sequence=index,
                longueur_m=longueur,
                diametre_m=diametre_m,
                depart_m=depart,
                **kwargs,
            )
        )
        depart += longueur
    return tuple(segments)


def profil_plat(longueur_m: float = 50_000.0, altitude_m: float = 100.0) -> ElevationProfile:
    return ElevationProfile.from_pairs([(0.0, altitude_m), (longueur_m, altitude_m)])


def profil_incline(
    longueur_m: float = 50_000.0, altitude_depart_m: float = 100.0, denivele_m: float = 50.0
) -> ElevationProfile:
    return ElevationProfile.from_pairs(
        [(0.0, altitude_depart_m), (longueur_m, altitude_depart_m + denivele_m)]
    )


def courbe_pompe(
    debits_m3_h: Sequence[float] = (1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0),
    hauteurs_m: Sequence[float] = (298.0, 292.0, 284.0, 270.0, 252.0, 230.0, 205.0),
    rendements: Sequence[float] | None = (0.60, 0.70, 0.78, 0.83, 0.81, 0.75, 0.68),
    npshr_m: Sequence[float] | None = (3.5, 4.2, 5.1, 6.3, 7.8, 9.6, 11.8),
    **kwargs,
) -> PumpCurve:
    """Courbe constructeur type d'une pompe d'oléoduc."""
    return PumpCurve(
        [q / 3600.0 for q in debits_m3_h],
        hauteurs_m,
        efficiencies=rendements,
        npshr_m=npshr_m,
        reference_speed_rpm=3000.0,
        **kwargs,
    )


def modele_pompe(identifiant: str = "NM-8", **kwargs) -> PumpModel:
    defaults = {
        "id": identifiant,
        "name": identifiant,
        "curve": courbe_pompe(),
        "manufacturer": "Constructeur générique",
        "motor_rated_power_w": 5.0e6,
        "npsh_margin_m": 1.0,
        "min_speed_ratio": 0.7,
        "max_speed_ratio": 1.0,
    }
    return PumpModel(**{**defaults, **kwargs})


def pompe(identifiant: str = "P1", modele: PumpModel | None = None, **kwargs) -> PumpInstance:
    return PumpInstance(id=identifiant, model=modele or modele_pompe(), **kwargs)


def station_serie(
    identifiant: str = "S1",
    chainage_m: float = 0.0,
    altitude_m: float = 100.0,
    nombre_de_pompes: int = 2,
    **kwargs,
) -> PumpStation:
    pompes = tuple(pompe(f"{identifiant}-P{i}") for i in range(1, nombre_de_pompes + 1))
    return build_series_station(
        identifiant, f"Station {identifiant}", chainage_m, altitude_m, pompes, **kwargs
    )


def station_parallele(
    identifiant: str = "S1",
    chainage_m: float = 0.0,
    altitude_m: float = 100.0,
    nombre_de_pompes: int = 2,
    **kwargs,
) -> PumpStation:
    pompes = tuple(pompe(f"{identifiant}-P{i}") for i in range(1, nombre_de_pompes + 1))
    return build_parallel_station(
        identifiant, f"Station {identifiant}", chainage_m, altitude_m, pompes, **kwargs
    )


def bac(
    identifiant: str = "B1",
    diametre_m: float = 40.0,
    hauteur_m: float = 16.0,
    niveau_m: float = 8.0,
    altitude_m: float = 0.0,
    **kwargs,
) -> Tank:
    defaults = {
        "id": identifiant,
        "name": f"Bac {identifiant}",
        "strapping": StrappingTable.from_vertical_cylinder(diametre_m, hauteur_m),
        "levels": TankLevels(
            minimum_m=0.8,
            low_m=1.5,
            normal_m=hauteur_m / 2.0,
            high_m=hauteur_m - 2.0,
            high_high_m=hauteur_m - 1.0,
        ),
        "current_level_m": niveau_m,
        "elevation_m": altitude_m,
    }
    return Tank(**{**defaults, **kwargs})


def pipeline(
    segments: tuple[PipeSegment, ...] | None = None,
    profil: ElevationProfile | None = None,
    stations: tuple[PumpStation, ...] = (),
    **kwargs,
) -> Pipeline:
    segments = segments or (segment(),)
    longueur = segments[-1].end_chainage_m
    defaults = {
        "id": "PL-1",
        "name": "Pipeline d'essai",
        "segments": segments,
        "profile": profil or profil_plat(longueur),
        "stations": stations,
    }
    return Pipeline(**{**defaults, **kwargs})


def scenario(
    identifiant: str = "SC-1",
    nom: str = "Scénario d'essai",
    options: SolverOptions | None = None,
    **kwargs,
) -> Scenario:
    return Scenario(
        id=identifiant,
        name=nom,
        solver=options or SolverOptions(profile_step_m=1000.0),
        **kwargs,
    )


def entree_canonique(
    conduite: Pipeline | None = None,
    fluide: Fluid | None = None,
    cas: Scenario | None = None,
    moteur: str = "long_distance_liquid",
) -> CanonicalInput:
    return CanonicalInput(
        pipeline=conduite or pipeline(),
        fluid=fluide or brut_leger(),
        scenario=cas or scenario(imposed_flow_m3_s=0.2, inlet_pressure_pa=5.0e6),
        engine=moteur,
    )


def accessoire(identifiant: str = "V1", k: float = 0.5, **kwargs) -> Fitting:
    defaults = {"id": identifiant, "kind": "vanne", "k_coefficient": k}
    return Fitting(**{**defaults, **kwargs})
