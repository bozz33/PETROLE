"""Désérialisation stricte des paquets d'entrée canoniques.

Le calcul persistant enregistre des dictionnaires JSON. Ce module reconstruit les objets du
domaine sans consulter un catalogue mutable : toutes les données qui influencent le résultat,
notamment les courbes de pompe, proviennent du paquet figé.

Les fonctions refusent les structures incomplètes et indiquent le chemin de la donnée fautive.
Aucune valeur scientifique obligatoire n'est inventée pendant le rejeu.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, TypeVar

from hydro_domain.canonical import CanonicalInput, Provenance
from hydro_domain.enums import (
    EquipmentStatus,
    FluidCategory,
    FrictionModel,
    ObjectiveKind,
    PropertyQuality,
    PropertySource,
    PumpArrangement,
    PumpRole,
    TankType,
)
from hydro_domain.fluid import Fluid, PropertyPoint, PropertyTable
from hydro_domain.geometry import ElevationProfile, Fitting, PipeSegment, ProfilePoint
from hydro_domain.interpolation import InterpolationKind
from hydro_domain.pipeline import InjectionPoint, Pipeline
from hydro_domain.pumps import PumpCurve, PumpInstance, PumpModel
from hydro_domain.scenario import (
    PumpOverride,
    Scenario,
    SegmentOverride,
    SolverOptions,
    StationOverride,
)
from hydro_domain.stations import PumpGroup, PumpStation
from hydro_domain.tanks import StrappingTable, Tank, TankLevels
from hydro_shared.errors import InvalidInputError

EnumT = TypeVar("EnumT", bound=StrEnum)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidInputError(
            f"La section « {path} » doit être un objet JSON.",
            path=path,
            received_type=type(value).__name__,
        )
    return value


def _items(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise InvalidInputError(
            f"La section « {path} » doit être une liste JSON.",
            path=path,
            received_type=type(value).__name__,
        )
    return value


def _required(source: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in source:
        full_path = f"{path}.{key}"
        raise InvalidInputError(
            f"La donnée obligatoire « {full_path} » est absente.",
            path=full_path,
        )
    return source[key]


def _required_str(source: Mapping[str, Any], key: str, path: str) -> str:
    value = _required(source, key, path)
    if not isinstance(value, str) or not value:
        full_path = f"{path}.{key}"
        raise InvalidInputError(
            f"La donnée « {full_path} » doit être une chaîne non vide.",
            path=full_path,
        )
    return value


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInputError(
            f"La donnée « {path} » doit être numérique.",
            path=path,
            received_type=type(value).__name__,
        )
    return float(value)


def _required_number(source: Mapping[str, Any], key: str, path: str) -> float:
    return _number(_required(source, key, path), f"{path}.{key}")


def _optional_number(source: Mapping[str, Any], key: str, path: str) -> float | None:
    value = source.get(key)
    if value is None:
        return None
    return _number(value, f"{path}.{key}")


def _optional_str(source: Mapping[str, Any], key: str, path: str) -> str | None:
    value = source.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        full_path = f"{path}.{key}"
        raise InvalidInputError(
            f"La donnée « {full_path} » doit être une chaîne ou null.",
            path=full_path,
            received_type=type(value).__name__,
        )
    return value


def _boolean(source: Mapping[str, Any], key: str, path: str, default: bool) -> bool:
    value = source.get(key, default)
    if not isinstance(value, bool):
        full_path = f"{path}.{key}"
        raise InvalidInputError(
            f"La donnée « {full_path} » doit être un booléen.",
            path=full_path,
        )
    return value


def _integer(source: Mapping[str, Any], key: str, path: str, default: int) -> int:
    value = source.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        full_path = f"{path}.{key}"
        raise InvalidInputError(
            f"La donnée « {full_path} » doit être un entier.",
            path=full_path,
        )
    return value


def _enum(enum_type: type[EnumT], value: Any, path: str) -> EnumT:
    if not isinstance(value, str):
        raise InvalidInputError(
            f"La donnée « {path} » doit être une chaîne.",
            path=path,
            received_type=type(value).__name__,
        )
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = [member.value for member in enum_type]
        raise InvalidInputError(
            f"La valeur « {value} » de « {path} » est inconnue.",
            path=path,
            value=value,
            allowed=allowed,
        ) from exc


def _number_sequence(value: Any, path: str) -> tuple[float, ...]:
    return tuple(
        _number(item, f"{path}[{index}]") for index, item in enumerate(_items(value, path))
    )


def _optional_number_sequence(value: Any, path: str) -> tuple[float, ...] | None:
    if value is None:
        return None
    return _number_sequence(value, path)


def _property_table(value: Any, path: str) -> PropertyTable | None:
    if value is None:
        return None
    data = _mapping(value, path)
    points = tuple(
        PropertyPoint(
            temperature_k=_required_number(point, "temperature_k", point_path),
            value=_required_number(point, "value", point_path),
            pressure_pa=_number(point.get("pressure_pa", 101_325.0), f"{point_path}.pressure_pa"),
            uncertainty=_optional_number(point, "uncertainty", point_path),
            method=_optional_str(point, "method", point_path),
            quality=_enum(
                PropertyQuality,
                point.get("quality", PropertyQuality.MEASURED.value),
                f"{point_path}.quality",
            ),
        )
        for index, item in enumerate(_items(_required(data, "points", path), f"{path}.points"))
        for point_path in (f"{path}.points[{index}]",)
        for point in (_mapping(item, point_path),)
    )
    return PropertyTable(
        points=points,
        source=_enum(
            PropertySource,
            data.get("source", PropertySource.INTERNAL_TABLE.value),
            f"{path}.source",
        ),
        reference=_optional_str(data, "reference", path),
    )


def fluid_from_dict(value: Any, path: str = "fluid") -> Fluid:
    """Reconstruit une fiche produit depuis sa représentation canonique."""

    data = _mapping(value, path)
    return Fluid(
        id=_required_str(data, "id", path),
        name=_required_str(data, "name", path),
        category=_enum(
            FluidCategory,
            data.get("category", FluidCategory.CUSTOM.value),
            f"{path}.category",
        ),
        reference_temperature_k=_number(
            data.get("reference_temperature_k", 288.15),
            f"{path}.reference_temperature_k",
        ),
        reference_pressure_pa=_number(
            data.get("reference_pressure_pa", 101_325.0),
            f"{path}.reference_pressure_pa",
        ),
        density_kg_m3=_optional_number(data, "density_kg_m3", path),
        kinematic_viscosity_m2_s=_optional_number(data, "kinematic_viscosity_m2_s", path),
        vapor_pressure_pa=_optional_number(data, "vapor_pressure_pa", path),
        density_table=_property_table(data.get("density_table"), f"{path}.density_table"),
        kinematic_viscosity_table=_property_table(
            data.get("kinematic_viscosity_table"),
            f"{path}.kinematic_viscosity_table",
        ),
        vapor_pressure_table=_property_table(
            data.get("vapor_pressure_table"),
            f"{path}.vapor_pressure_table",
        ),
        thermal_expansion_1_k=_optional_number(data, "thermal_expansion_1_k", path),
        coolprop_name=_optional_str(data, "coolprop_name", path),
        data_source=_optional_str(data, "data_source", path),
        batch_reference=_optional_str(data, "batch_reference", path),
    )


def pump_model_from_dict(value: Any, path: str = "equipment.pump_models[]") -> PumpModel:
    """Reconstruit un modèle de pompe et toutes ses courbes constructeur."""

    data = _mapping(value, path)
    curve_path = f"{path}.curve"
    curve_data = _mapping(_required(data, "curve", path), curve_path)
    curve = PumpCurve(
        _number_sequence(
            _required(curve_data, "flows_m3_s", curve_path),
            f"{curve_path}.flows_m3_s",
        ),
        _number_sequence(
            _required(curve_data, "heads_m", curve_path),
            f"{curve_path}.heads_m",
        ),
        efficiencies=_optional_number_sequence(
            curve_data.get("efficiencies"),
            f"{curve_path}.efficiencies",
        ),
        powers_w=_optional_number_sequence(
            curve_data.get("powers_w"),
            f"{curve_path}.powers_w",
        ),
        npshr_m=_optional_number_sequence(
            curve_data.get("npshr_m"),
            f"{curve_path}.npshr_m",
        ),
        reference_speed_rpm=_optional_number(
            curve_data,
            "reference_speed_rpm",
            curve_path,
        ),
        interpolation=_enum(
            InterpolationKind,
            curve_data.get("interpolation", InterpolationKind.PCHIP.value),
            f"{curve_path}.interpolation",
        ),
    )
    return PumpModel(
        id=_required_str(data, "id", path),
        name=_required_str(data, "name", path),
        curve=curve,
        manufacturer=_optional_str(data, "manufacturer", path),
        motor_rated_power_w=_optional_number(data, "motor_rated_power_w", path),
        npsh_margin_m=_number(data.get("npsh_margin_m", 0.5), f"{path}.npsh_margin_m"),
        min_speed_ratio=_number(
            data.get("min_speed_ratio", 0.7),
            f"{path}.min_speed_ratio",
        ),
        max_speed_ratio=_number(
            data.get("max_speed_ratio", 1.0),
            f"{path}.max_speed_ratio",
        ),
        minimum_continuous_flow_m3_s=_optional_number(
            data,
            "minimum_continuous_flow_m3_s",
            path,
        ),
        data_source=_optional_str(data, "data_source", path),
    )


def pump_models_from_dict(value: Any) -> dict[str, PumpModel]:
    """Construit le catalogue de pompes et refuse les identifiants ambigus."""

    equipment = _mapping(value, "equipment")
    models: dict[str, PumpModel] = {}
    raw_models = equipment.get("pump_models", ())
    for index, item in enumerate(_items(raw_models, "equipment.pump_models")):
        path = f"equipment.pump_models[{index}]"
        model = pump_model_from_dict(item, path)
        previous = models.get(model.id)
        if previous is not None and previous.as_dict() != model.as_dict():
            raise InvalidInputError(
                "Le catalogue contient plusieurs modèles de pompe différents sous le même identifiant.",
                path=path,
                pump_model_id=model.id,
            )
        models[model.id] = model
    return models


def _fitting(value: Any, path: str) -> Fitting:
    data = _mapping(value, path)
    return Fitting(
        id=_required_str(data, "id", path),
        kind=_required_str(data, "kind", path),
        k_coefficient=_required_number(data, "k_coefficient", path),
        quantity=_integer(data, "quantity", path, 1),
        chainage_m=_optional_number(data, "chainage_m", path),
        label=_optional_str(data, "label", path),
        status=_enum(
            EquipmentStatus,
            data.get("status", EquipmentStatus.AVAILABLE.value),
            f"{path}.status",
        ),
        opening_ratio=_number(data.get("opening_ratio", 1.0), f"{path}.opening_ratio"),
    )


def _segment(value: Any, path: str) -> PipeSegment:
    data = _mapping(value, path)
    fittings = tuple(
        _fitting(item, f"{path}.fittings[{index}]")
        for index, item in enumerate(_items(data.get("fittings", ()), f"{path}.fittings"))
    )
    return PipeSegment(
        id=_required_str(data, "id", path),
        sequence=_integer(data, "sequence", path, 0),
        length_m=_required_number(data, "length_m", path),
        inner_diameter_m=_required_number(data, "inner_diameter_m", path),
        roughness_m=_required_number(data, "roughness_m", path),
        start_chainage_m=_number(
            data.get("start_chainage_m", 0.0),
            f"{path}.start_chainage_m",
        ),
        outer_diameter_m=_optional_number(data, "outer_diameter_m", path),
        wall_thickness_m=_optional_number(data, "wall_thickness_m", path),
        material=_optional_str(data, "material", path),
        maop_pa=_optional_number(data, "maop_pa", path),
        minimum_pressure_pa=_optional_number(data, "minimum_pressure_pa", path),
        status=_enum(
            EquipmentStatus,
            data.get("status", EquipmentStatus.AVAILABLE.value),
            f"{path}.status",
        ),
        fittings=fittings,
        label=_optional_str(data, "label", path),
    )


def _tank(value: Any, path: str) -> Tank | None:
    if value is None:
        return None
    data = _mapping(value, path)
    strapping_path = f"{path}.strapping"
    strapping_data = _mapping(_required(data, "strapping", path), strapping_path)
    points = tuple(
        (
            _required_number(point, "height_m", point_path),
            _required_number(point, "volume_m3", point_path),
        )
        for index, item in enumerate(
            _items(_required(strapping_data, "points", strapping_path), f"{strapping_path}.points")
        )
        for point_path in (f"{strapping_path}.points[{index}]",)
        for point in (_mapping(item, point_path),)
    )
    levels_path = f"{path}.levels"
    levels_data = _mapping(_required(data, "levels", path), levels_path)
    compatible = tuple(
        str(item)
        for item in _items(data.get("compatible_fluid_ids", ()), f"{path}.compatible_fluid_ids")
    )
    return Tank(
        id=_required_str(data, "id", path),
        name=_required_str(data, "name", path),
        strapping=StrappingTable.from_pairs(points),
        levels=TankLevels(
            minimum_m=_required_number(levels_data, "minimum_m", levels_path),
            high_high_m=_required_number(levels_data, "high_high_m", levels_path),
            low_m=_optional_number(levels_data, "low_m", levels_path),
            normal_m=_optional_number(levels_data, "normal_m", levels_path),
            high_m=_optional_number(levels_data, "high_m", levels_path),
        ),
        tank_type=_enum(
            TankType,
            data.get("tank_type", TankType.VERTICAL_FIXED_ROOF.value),
            f"{path}.tank_type",
        ),
        elevation_m=_number(data.get("elevation_m", 0.0), f"{path}.elevation_m"),
        current_level_m=_number(
            data.get("current_level_m", 0.0),
            f"{path}.current_level_m",
        ),
        fluid_id=_optional_str(data, "fluid_id", path),
        compatible_fluid_ids=compatible,
        status=_enum(
            EquipmentStatus,
            data.get("status", EquipmentStatus.AVAILABLE.value),
            f"{path}.status",
        ),
        dead_volume_m3=_number(
            data.get("dead_volume_m3", 0.0),
            f"{path}.dead_volume_m3",
        ),
        label=_optional_str(data, "label", path),
    )


def _pump_instance(
    value: Any,
    path: str,
    pump_models: Mapping[str, PumpModel],
) -> PumpInstance:
    data = _mapping(value, path)
    model_id = _required_str(data, "model_id", path)
    model = pump_models.get(model_id)
    if model is None:
        raise InvalidInputError(
            f"La pompe « {path} » référence le modèle absent « {model_id} ».",
            path=f"{path}.model_id",
            pump_model_id=model_id,
        )
    return PumpInstance(
        id=_required_str(data, "id", path),
        model=model,
        role=_enum(PumpRole, data.get("role", PumpRole.MAIN.value), f"{path}.role"),
        status=_enum(
            EquipmentStatus,
            data.get("status", EquipmentStatus.AVAILABLE.value),
            f"{path}.status",
        ),
        running=_boolean(data, "running", path, True),
        speed_ratio=_number(data.get("speed_ratio", 1.0), f"{path}.speed_ratio"),
        label=_optional_str(data, "label", path),
    )


def _station(
    value: Any,
    path: str,
    pump_models: Mapping[str, PumpModel],
) -> PumpStation:
    data = _mapping(value, path)
    groups: list[PumpGroup] = []
    for group_index, raw_group in enumerate(_items(data.get("groups", ()), f"{path}.groups")):
        group_path = f"{path}.groups[{group_index}]"
        group_data = _mapping(raw_group, group_path)
        pumps = tuple(
            _pump_instance(item, f"{group_path}.pumps[{pump_index}]", pump_models)
            for pump_index, item in enumerate(
                _items(group_data.get("pumps", ()), f"{group_path}.pumps")
            )
        )
        groups.append(
            PumpGroup(
                id=_required_str(group_data, "id", group_path),
                pumps=pumps,
                label=_optional_str(group_data, "label", group_path),
            )
        )
    return PumpStation(
        id=_required_str(data, "id", path),
        name=_required_str(data, "name", path),
        chainage_m=_required_number(data, "chainage_m", path),
        elevation_m=_required_number(data, "elevation_m", path),
        groups=tuple(groups),
        arrangement=_enum(
            PumpArrangement,
            data.get("arrangement", PumpArrangement.SERIES.value),
            f"{path}.arrangement",
        ),
        status=_enum(
            EquipmentStatus,
            data.get("status", EquipmentStatus.AVAILABLE.value),
            f"{path}.status",
        ),
        suction_pressure_min_pa=_optional_number(
            data,
            "suction_pressure_min_pa",
            path,
        ),
        discharge_pressure_max_pa=_optional_number(
            data,
            "discharge_pressure_max_pa",
            path,
        ),
        suction_line_k=_number(data.get("suction_line_k", 0.0), f"{path}.suction_line_k"),
        bypass_k=_number(data.get("bypass_k", 0.0), f"{path}.bypass_k"),
        drive_efficiency=_number(
            data.get("drive_efficiency", 1.0),
            f"{path}.drive_efficiency",
        ),
        label=_optional_str(data, "label", path),
    )


def pipeline_from_dict(
    value: Any,
    pump_models: Mapping[str, PumpModel],
    path: str = "network",
) -> Pipeline:
    """Reconstruit le pipeline et résout chaque référence de modèle de pompe."""

    data = _mapping(value, path)
    segments = tuple(
        _segment(item, f"{path}.segments[{index}]")
        for index, item in enumerate(_items(_required(data, "segments", path), f"{path}.segments"))
    )
    profile_path = f"{path}.profile"
    profile_data = _mapping(_required(data, "profile", path), profile_path)
    profile = ElevationProfile(
        [
            ProfilePoint(
                chainage_m=_required_number(point, "chainage_m", point_path),
                elevation_m=_required_number(point, "elevation_m", point_path),
                latitude=_optional_number(point, "latitude", point_path),
                longitude=_optional_number(point, "longitude", point_path),
            )
            for index, item in enumerate(
                _items(_required(profile_data, "points", profile_path), f"{profile_path}.points")
            )
            for point_path in (f"{profile_path}.points[{index}]",)
            for point in (_mapping(item, point_path),)
        ]
    )
    stations = tuple(
        _station(item, f"{path}.stations[{index}]", pump_models)
        for index, item in enumerate(_items(data.get("stations", ()), f"{path}.stations"))
    )
    injections = tuple(
        InjectionPoint(
            id=_required_str(injection, "id", injection_path),
            chainage_m=_required_number(injection, "chainage_m", injection_path),
            flow_m3_s=_required_number(injection, "flow_m3_s", injection_path),
            label=_optional_str(injection, "label", injection_path),
            status=_enum(
                EquipmentStatus,
                injection.get("status", EquipmentStatus.AVAILABLE.value),
                f"{injection_path}.status",
            ),
        )
        for index, item in enumerate(_items(data.get("injections", ()), f"{path}.injections"))
        for injection_path in (f"{path}.injections[{index}]",)
        for injection in (_mapping(item, injection_path),)
    )
    return Pipeline(
        id=_required_str(data, "id", path),
        name=_required_str(data, "name", path),
        segments=segments,
        profile=profile,
        stations=stations,
        injections=injections,
        origin_tank=_tank(data.get("origin_tank"), f"{path}.origin_tank"),
        destination_tank=_tank(
            data.get("destination_tank"),
            f"{path}.destination_tank",
        ),
        label=_optional_str(data, "label", path),
    )


def solver_options_from_dict(value: Any, path: str = "scenario.solver") -> SolverOptions:
    """Reconstruit les paramètres numériques enregistrés avec le scénario."""

    data = _mapping(value, path)
    return SolverOptions(
        friction_model=_enum(
            FrictionModel,
            data.get("friction_model", FrictionModel.COLEBROOK_WHITE.value),
            f"{path}.friction_model",
        ),
        pressure_tolerance_pa=_number(
            data.get("pressure_tolerance_pa", 1.0),
            f"{path}.pressure_tolerance_pa",
        ),
        mass_balance_tolerance=_number(
            data.get("mass_balance_tolerance", 1.0e-6),
            f"{path}.mass_balance_tolerance",
        ),
        max_iterations=_integer(data, "max_iterations", path, 100),
        profile_step_m=_number(data.get("profile_step_m", 1000.0), f"{path}.profile_step_m"),
        store_iterations=_boolean(data, "store_iterations", path, False),
        use_quadratic_pump_fit=_boolean(
            data,
            "use_quadratic_pump_fit",
            path,
            False,
        ),
        max_flow_m3_s=_optional_number(data, "max_flow_m3_s", path),
        detect_gravity_zones=_boolean(data, "detect_gravity_zones", path, True),
        apply_gravity_model=_boolean(data, "apply_gravity_model", path, False),
        min_velocity_m_s=_optional_number(data, "min_velocity_m_s", path),
        max_velocity_m_s=_optional_number(data, "max_velocity_m_s", path),
    )


def scenario_from_dict(value: Any, path: str = "scenario") -> Scenario:
    """Reconstruit un scénario figé, surcharges et solveur compris."""

    data = _mapping(value, path)
    pump_overrides = tuple(
        PumpOverride(
            pump_id=_required_str(item_data, "pump_id", item_path),
            status=(
                None
                if item_data.get("status") is None
                else _enum(EquipmentStatus, item_data["status"], f"{item_path}.status")
            ),
            running=(
                None
                if item_data.get("running") is None
                else _boolean(item_data, "running", item_path, False)
            ),
            speed_ratio=_optional_number(item_data, "speed_ratio", item_path),
        )
        for index, item in enumerate(
            _items(data.get("pump_overrides", ()), f"{path}.pump_overrides")
        )
        for item_path in (f"{path}.pump_overrides[{index}]",)
        for item_data in (_mapping(item, item_path),)
    )
    station_overrides = tuple(
        StationOverride(
            station_id=_required_str(item_data, "station_id", item_path),
            status=(
                None
                if item_data.get("status") is None
                else _enum(EquipmentStatus, item_data["status"], f"{item_path}.status")
            ),
        )
        for index, item in enumerate(
            _items(data.get("station_overrides", ()), f"{path}.station_overrides")
        )
        for item_path in (f"{path}.station_overrides[{index}]",)
        for item_data in (_mapping(item, item_path),)
    )
    segment_overrides = tuple(
        SegmentOverride(
            segment_id=_required_str(item_data, "segment_id", item_path),
            status=(
                None
                if item_data.get("status") is None
                else _enum(EquipmentStatus, item_data["status"], f"{item_path}.status")
            ),
            additional_k=_optional_number(item_data, "additional_k", item_path),
        )
        for index, item in enumerate(
            _items(data.get("segment_overrides", ()), f"{path}.segment_overrides")
        )
        for item_path in (f"{path}.segment_overrides[{index}]",)
        for item_data in (_mapping(item, item_path),)
    )
    solver_value = data.get("solver", {})
    return Scenario(
        id=_required_str(data, "id", path),
        name=_required_str(data, "name", path),
        temperature_k=_optional_number(data, "temperature_k", path),
        imposed_flow_m3_s=_optional_number(data, "imposed_flow_m3_s", path),
        inlet_pressure_pa=_optional_number(data, "inlet_pressure_pa", path),
        outlet_pressure_pa=_optional_number(data, "outlet_pressure_pa", path),
        inlet_tank_level_m=_optional_number(data, "inlet_tank_level_m", path),
        outlet_tank_level_m=_optional_number(data, "outlet_tank_level_m", path),
        pump_overrides=pump_overrides,
        station_overrides=station_overrides,
        segment_overrides=segment_overrides,
        solver=solver_options_from_dict(solver_value, f"{path}.solver"),
        objective=(
            None
            if data.get("objective") is None
            else _enum(ObjectiveKind, data["objective"], f"{path}.objective")
        ),
        energy_price_per_joule=_optional_number(
            data,
            "energy_price_per_joule",
            path,
        ),
        parent_id=_optional_str(data, "parent_id", path),
        description=_optional_str(data, "description", path),
    )


def _provenance(value: Any) -> Provenance:
    if value is None:
        return Provenance()
    data = _mapping(value, "provenance")
    source_files = tuple(
        str(item) for item in _items(data.get("source_files", ()), "provenance.source_files")
    )
    return Provenance(
        requested_by=_optional_str(data, "requested_by", "provenance"),
        requested_at=_optional_str(data, "requested_at", "provenance"),
        project_id=_optional_str(data, "project_id", "provenance"),
        model_version_id=_optional_str(data, "model_version_id", "provenance"),
        organization_id=_optional_str(data, "organization_id", "provenance"),
        client_reference=_optional_str(data, "client_reference", "provenance"),
        source_files=source_files,
    )


def canonical_input_from_dict(value: Any) -> CanonicalInput:
    """Reconstruit un paquet canonique complet et vérifie ses références croisées."""

    data = _mapping(value, "canonical_input")
    manifest = _mapping(_required(data, "manifest", "canonical_input"), "manifest")
    equipment = data.get("equipment", {"pump_models": []})
    pump_models = pump_models_from_dict(equipment)
    pipeline = pipeline_from_dict(
        _required(data, "network", "canonical_input"),
        pump_models,
    )
    fluid = fluid_from_dict(_required(data, "fluid", "canonical_input"))
    scenario = scenario_from_dict(_required(data, "scenario", "canonical_input"))

    expected_ids = {
        "pipeline_id": pipeline.id,
        "fluid_id": fluid.id,
        "scenario_id": scenario.id,
    }
    for key, actual in expected_ids.items():
        declared = _required_str(manifest, key, "manifest")
        if declared != actual:
            raise InvalidInputError(
                f"L'identifiant « manifest.{key} » ne correspond pas à l'objet sérialisé.",
                path=f"manifest.{key}",
                declared=declared,
                actual=actual,
            )

    rules = _mapping(data.get("rules", {}), "rules")
    rule_set_ids = tuple(
        str(item) for item in _items(rules.get("rule_set_ids", ()), "rules.rule_set_ids")
    )
    return CanonicalInput(
        pipeline=pipeline,
        fluid=fluid,
        scenario=scenario,
        engine=_required_str(manifest, "engine", "manifest"),
        rule_set_ids=rule_set_ids,
        provenance=_provenance(data.get("provenance")),
        schema_version=_required_str(manifest, "schema_version", "manifest"),
        engine_version=_required_str(manifest, "engine_version", "manifest"),
    )


__all__ = [
    "canonical_input_from_dict",
    "fluid_from_dict",
    "pipeline_from_dict",
    "pump_model_from_dict",
    "pump_models_from_dict",
    "scenario_from_dict",
    "solver_options_from_dict",
]
