"""Contrôles physiques et numériques obligatoires C-001 à C-012.

Référence : *Documentation complète du MVP v2.0*, § 5.8. Chaque contrôle produit soit une
violation localisée, soit un avertissement, soit rien — mais il est **toujours exécuté**, et
son identifiant apparaît dans le résultat afin que la note de calcul puisse indiquer ce qui a
été vérifié et ce qui ne l'a pas été (D-v2 § 6.3 : ne jamais afficher une conformité complète
lorsqu'un sous-ensemble seulement a été vérifié).

Chaque violation porte sa valeur, sa limite, son écart, sa localisation et une recommandation
exploitable (D-v2 § 4.9).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hydro_domain.geometry import PipeSegment
from hydro_domain.results import ProfilePointResult, PumpResult, StationResult
from hydro_domain.scenario import SolverOptions
from hydro_domain.tanks import Tank
from hydro_shared.codes import ViolationCode, WarningCode
from hydro_shared.diagnostics import Diagnostic, Location, Severity, Violation


@dataclass(slots=True)
class CheckOutcome:
    """Résultat de l'exécution d'une batterie de contrôles."""

    violations: list[Violation] = field(default_factory=list)
    warnings: list[Diagnostic] = field(default_factory=list)
    #: Contrôles effectivement exécutés, par identifiant.
    executed: set[str] = field(default_factory=set)
    #: Contrôles non applicables faute de donnée, avec leur motif.
    skipped: dict[str, str] = field(default_factory=dict)

    def extend(self, other: CheckOutcome) -> None:
        self.violations.extend(other.violations)
        self.warnings.extend(other.warnings)
        self.executed |= other.executed
        self.skipped.update(other.skipped)

    def as_dict(self) -> dict[str, object]:
        return {
            "executed": sorted(self.executed),
            "skipped": dict(sorted(self.skipped.items())),
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
        }


# --------------------------------------------------------------------------- C-001


def check_mass_balance(
    inlet_flow_m3_s: float,
    outlet_flow_m3_s: float,
    net_injection_m3_s: float,
    tolerance: float,
) -> CheckOutcome:
    """C-001 — Conservation de masse le long du pipeline.

    En régime permanent et à masse volumique constante, le débit volumique sortant doit être
    égal au débit entrant augmenté des injections nettes. L'écart est rapporté au débit de
    référence pour être comparé à une tolérance relative (D10 § 3 : ≤ 10⁻⁶).
    """
    outcome = CheckOutcome(executed={"C-001"})
    expected = inlet_flow_m3_s + net_injection_m3_s
    residual = outlet_flow_m3_s - expected
    reference = max(abs(inlet_flow_m3_s), abs(outlet_flow_m3_s), 1e-12)
    relative = abs(residual) / reference

    if relative > tolerance:
        outcome.violations.append(
            Violation(
                code=ViolationCode.MASS_BALANCE,
                severity=Severity.CRITICAL,
                message=(
                    f"Bilan de masse non conservé : écart relatif {relative:.3e} supérieur à la "
                    f"tolérance {tolerance:.3e}."
                ),
                value=relative,
                limit=tolerance,
                unit="sans dimension",
                recommendation=(
                    "Vérifiez les injections et soutirages déclarés, ainsi que la cohérence des "
                    "conditions aux limites. Aucun résultat ne peut être approuvé tant que le "
                    "bilan de masse dépasse la tolérance."
                ),
                check_id="C-001",
            )
        )
    return outcome


# --------------------------------------------------------------------------- C-002


def check_vapor_pressure(
    profile: list[ProfilePointResult],
    vapor_pressure_pa: float,
    *,
    gravity_model_applied: bool,
    vapor_pressure_known: bool,
) -> CheckOutcome:
    """C-002 — Pression inférieure à la pression de vapeur.

    Sans donnée de pression de vapeur, le contrôle est déclaré **non exécuté** plutôt que
    déclaré conforme : une absence de donnée n'est pas une preuve d'absence de risque.

    Lorsque le modèle de zone gravitaire est explicitement activé, la dépression n'est plus
    une violation mais une caractéristique du modèle retenu ; elle est alors signalée comme
    avertissement, assortie du rappel que ce modèle exige une validation avant usage
    industriel (D07 § 8).
    """
    outcome = CheckOutcome()
    if not vapor_pressure_known:
        outcome.skipped["C-002"] = (
            "Pression de vapeur non renseignée pour le produit : le contrôle de dépression ne "
            "peut pas conclure."
        )
        return outcome

    outcome.executed.add("C-002")
    offending = [p for p in profile if p.pressure_pa <= vapor_pressure_pa]
    if not offending:
        return outcome

    worst = min(offending, key=lambda p: p.pressure_pa)
    location = Location(object_type="pipeline", chainage_m=worst.chainage_m)
    extent_km = (offending[-1].chainage_m - offending[0].chainage_m) / 1000.0

    if gravity_model_applied:
        outcome.warnings.append(
            Diagnostic(
                code=WarningCode.GRAVITY_FLOW_SUSPECTED,
                message=(
                    f"Le modèle de zone gravitaire est actif : la pression atteint la pression de "
                    f"vapeur sur environ {extent_km:.1f} km, à partir du PK "
                    f"{offending[0].chainage_m / 1000:.1f} km. Ce modèle suppose une conduite non "
                    f"entièrement pressurisée et doit être validé avant usage industriel."
                ),
                severity=Severity.WARNING,
                location=location,
                details={"points": len(offending), "extent_km": extent_km},
            )
        )
        return outcome

    outcome.violations.append(
        Violation(
            code=ViolationCode.PRESSURE_BELOW_VAPOR,
            severity=Severity.CRITICAL,
            message=(
                f"La pression descend à {worst.pressure_pa / 1e5:.3f} bar au PK "
                f"{worst.chainage_m / 1000:.2f} km, au niveau ou en dessous de la pression de "
                f"vapeur ({vapor_pressure_pa / 1e5:.3f} bar) : le modèle de conduite pleine n'est "
                f"plus valable."
            ),
            location=location,
            value=worst.pressure_pa,
            limit=vapor_pressure_pa,
            unit="Pa",
            recommendation=(
                "Augmentez la pression amont, ajoutez une station intermédiaire, réduisez le "
                "débit, ou sélectionnez explicitement le modèle de zone gravitaire après en "
                "avoir vérifié les hypothèses."
            ),
            check_id="C-002",
        )
    )
    return outcome


# --------------------------------------------------------------------------- C-003


def check_npsh(pumps: list[PumpResult], margins: dict[str, float]) -> CheckOutcome:
    """C-003 — NPSH disponible insuffisant.

    La marge de projet ``margins[pump_id]`` s'ajoute au NPSH requis : la condition de
    non-cavitation s'écrit ``NPSHa ≥ NPSHr + marge``. Sans courbe NPSHr, le contrôle est
    déclaré non exécuté.
    """
    outcome = CheckOutcome()
    evaluated = False

    for pump in pumps:
        if not pump.running:
            continue
        if pump.npsh_required_m is None or pump.npsh_available_m is None:
            continue
        evaluated = True
        margin = margins.get(pump.pump_id, 0.0)
        available_margin = pump.npsh_available_m - pump.npsh_required_m - margin
        if available_margin < 0.0:
            outcome.violations.append(
                Violation(
                    code=ViolationCode.CAVITATION,
                    severity=Severity.CRITICAL,
                    message=(
                        f"Risque de cavitation sur « {pump.label} » : NPSH disponible "
                        f"{pump.npsh_available_m:.2f} m contre {pump.npsh_required_m:.2f} m requis "
                        f"plus une marge de projet de {margin:.2f} m."
                    ),
                    location=Location(
                        object_type="pump",
                        object_id=pump.pump_id,
                        object_label=pump.label,
                    ),
                    value=pump.npsh_available_m,
                    limit=pump.npsh_required_m + margin,
                    unit="m",
                    recommendation=(
                        "Augmentez la pression d'aspiration (niveau du bac amont, pression de "
                        "gavage), réduisez les pertes du collecteur d'aspiration ou abaissez le "
                        "débit de la pompe."
                    ),
                    check_id="C-003",
                )
            )

    if evaluated:
        outcome.executed.add("C-003")
    else:
        outcome.skipped["C-003"] = (
            "Aucune courbe NPSHr disponible sur les pompes en service : le risque de cavitation "
            "n'a pas pu être évalué."
        )
    return outcome


# --------------------------------------------------------------------------- C-004


def check_maximum_pressure(
    profile: list[ProfilePointResult],
    segments: list[PipeSegment],
    *,
    near_limit_ratio: float = 0.95,
) -> CheckOutcome:
    """C-004 — Pression supérieure à la pression maximale admissible.

    Le contrôle est fait **tronçon par tronçon** : la MAOP peut varier le long du tracé selon
    l'épaisseur et le matériau. Un dépassement est critique ; une approche à moins de 5 % de
    la limite produit un avertissement ``WARN_NEAR_LIMIT``.
    """
    outcome = CheckOutcome()
    segments_with_limit = [s for s in segments if s.maop_pa is not None]
    if not segments_with_limit:
        outcome.skipped["C-004"] = (
            "Aucun tronçon ne déclare de pression maximale admissible : le contrôle de "
            "surpression n'a pas pu être effectué."
        )
        return outcome

    outcome.executed.add("C-004")
    for segment in segments_with_limit:
        limit = segment.maop_pa
        assert limit is not None  # garanti par le filtre ci-dessus
        points = [
            p for p in profile if segment.start_chainage_m <= p.chainage_m <= segment.end_chainage_m
        ]
        if not points:
            continue
        worst = max(points, key=lambda p: p.pressure_pa)
        location = Location(
            object_type="segment",
            object_id=segment.id,
            object_label=segment.label or segment.id,
            chainage_m=worst.chainage_m,
        )
        if worst.pressure_pa > limit:
            outcome.violations.append(
                Violation(
                    code=ViolationCode.PRESSURE_HIGH,
                    severity=Severity.CRITICAL,
                    message=(
                        f"Pression maximale admissible dépassée sur le tronçon "
                        f"{segment.label or segment.id} : {worst.pressure_pa / 1e5:.2f} bar au PK "
                        f"{worst.chainage_m / 1000:.2f} km pour une limite de {limit / 1e5:.2f} bar."
                    ),
                    location=location,
                    value=worst.pressure_pa,
                    limit=limit,
                    unit="Pa",
                    recommendation=(
                        "Réduisez la hauteur fournie en amont (nombre de pompes, vitesse), "
                        "abaissez le débit, ou vérifiez la pression maximale admissible retenue "
                        "pour ce tronçon."
                    ),
                    check_id="C-004",
                )
            )
        elif worst.pressure_pa > near_limit_ratio * limit:
            outcome.warnings.append(
                Diagnostic(
                    code=WarningCode.NEAR_LIMIT,
                    message=(
                        f"Pression proche de la limite sur le tronçon "
                        f"{segment.label or segment.id} : {worst.pressure_pa / 1e5:.2f} bar, soit "
                        f"{100 * worst.pressure_pa / limit:.1f} % de la pression maximale "
                        f"admissible."
                    ),
                    location=location,
                    details={"pressure_pa": worst.pressure_pa, "limit_pa": limit},
                )
            )

    minimum_limits = [s for s in segments if s.minimum_pressure_pa is not None]
    for segment in minimum_limits:
        limit = segment.minimum_pressure_pa
        assert limit is not None
        points = [
            p for p in profile if segment.start_chainage_m <= p.chainage_m <= segment.end_chainage_m
        ]
        if not points:
            continue
        worst = min(points, key=lambda p: p.pressure_pa)
        if worst.pressure_pa < limit:
            outcome.violations.append(
                Violation(
                    code=ViolationCode.PRESSURE_LOW,
                    severity=Severity.CRITICAL,
                    message=(
                        f"Pression minimale de service non respectée sur le tronçon "
                        f"{segment.label or segment.id} : {worst.pressure_pa / 1e5:.2f} bar au PK "
                        f"{worst.chainage_m / 1000:.2f} km pour un minimum de {limit / 1e5:.2f} bar."
                    ),
                    location=Location(
                        object_type="segment",
                        object_id=segment.id,
                        chainage_m=worst.chainage_m,
                    ),
                    value=worst.pressure_pa,
                    limit=limit,
                    unit="Pa",
                    recommendation=(
                        "Augmentez la pression amont ou réduisez le débit pour maintenir la "
                        "pression de service minimale."
                    ),
                    check_id="C-004",
                )
            )
    return outcome


# --------------------------------------------------------------------------- C-005


def check_velocity(profile: list[ProfilePointResult], options: SolverOptions) -> CheckOutcome:
    """C-005 — Vitesse hors de la plage configurée.

    La sévérité est **paramétrable par le projet** : les bornes de vitesse relèvent d'une
    règle d'exploitation (érosion, dépôt, coup de bélier) et non d'une loi physique. Le MVP
    les traite en avertissement, puisque le calcul reste valable en dehors de la plage.
    """
    outcome = CheckOutcome()
    if options.min_velocity_m_s is None and options.max_velocity_m_s is None:
        outcome.skipped["C-005"] = "Aucune plage de vitesse configurée pour ce scénario."
        return outcome
    if not profile:
        outcome.skipped["C-005"] = "Profil de résultat vide."
        return outcome

    outcome.executed.add("C-005")
    fastest = max(profile, key=lambda p: abs(p.velocity_m_s))
    slowest = min(profile, key=lambda p: abs(p.velocity_m_s))

    if (
        options.max_velocity_m_s is not None
        and abs(fastest.velocity_m_s) > options.max_velocity_m_s
    ):
        outcome.warnings.append(
            Diagnostic(
                code=WarningCode.HIGH_VELOCITY,
                message=(
                    f"Vitesse de {abs(fastest.velocity_m_s):.2f} m/s au PK "
                    f"{fastest.chainage_m / 1000:.2f} km, au-delà de la limite configurée de "
                    f"{options.max_velocity_m_s:.2f} m/s."
                ),
                location=Location(object_type="pipeline", chainage_m=fastest.chainage_m),
                details={"velocity_m_s": abs(fastest.velocity_m_s)},
            )
        )
    if (
        options.min_velocity_m_s is not None
        and abs(slowest.velocity_m_s) < options.min_velocity_m_s
    ):
        outcome.warnings.append(
            Diagnostic(
                code=WarningCode.LOW_VELOCITY,
                message=(
                    f"Vitesse de {abs(slowest.velocity_m_s):.2f} m/s au PK "
                    f"{slowest.chainage_m / 1000:.2f} km, en deçà de la limite configurée de "
                    f"{options.min_velocity_m_s:.2f} m/s ; risque de dépôt."
                ),
                location=Location(object_type="pipeline", chainage_m=slowest.chainage_m),
                details={"velocity_m_s": abs(slowest.velocity_m_s)},
            )
        )
    return outcome


# --------------------------------------------------------------------------- C-006


def check_pump_curve_domain(
    pumps: list[PumpResult], minimum_flows: dict[str, float]
) -> CheckOutcome:
    """C-006 — Fonctionnement hors du domaine de courbe.

    Deux situations distinctes sont traitées :

    - **hors domaine tabulé** : la hauteur provient d'une extrapolation ; le résultat est
      disponible mais l'incertitude n'est pas maîtrisée → avertissement ;
    - **sous le débit minimal continu constructeur** : le fonctionnement est déconseillé et
      peut endommager la machine → violation.
    """
    outcome = CheckOutcome()
    running = [p for p in pumps if p.running]
    if not running:
        outcome.skipped["C-006"] = "Aucune pompe en service."
        return outcome

    outcome.executed.add("C-006")
    for pump in running:
        location = Location(object_type="pump", object_id=pump.pump_id, object_label=pump.label)
        if not pump.within_curve_domain:
            outcome.warnings.append(
                Diagnostic(
                    code=WarningCode.PUMP_EXTRAPOLATION_NEAR_LIMIT,
                    message=(
                        f"« {pump.label} » fonctionne à {pump.flow_m3_s * 3600:.0f} m³/h, hors du "
                        f"domaine de sa courbe constructeur : la hauteur est extrapolée."
                    ),
                    location=location,
                    details={"flow_m3_s": pump.flow_m3_s},
                )
            )
        minimum = minimum_flows.get(pump.pump_id)
        if minimum is not None and pump.flow_m3_s < minimum:
            outcome.violations.append(
                Violation(
                    code=ViolationCode.PUMP_BELOW_MIN_FLOW,
                    severity=Severity.CRITICAL,
                    message=(
                        f"« {pump.label} » fonctionne à {pump.flow_m3_s * 3600:.0f} m³/h, en deçà "
                        f"du débit minimal continu de {minimum * 3600:.0f} m³/h."
                    ),
                    location=location,
                    value=pump.flow_m3_s,
                    limit=minimum,
                    unit="m³/s",
                    recommendation=(
                        "Augmentez le débit, arrêtez une pompe en parallèle, ou mettez en service "
                        "une ligne de recirculation."
                    ),
                    check_id="C-006",
                )
            )
        if pump.off_bep_ratio is not None and pump.off_bep_ratio > 0.3:
            outcome.warnings.append(
                Diagnostic(
                    code=WarningCode.PUMP_OFF_BEP,
                    message=(
                        f"« {pump.label} » fonctionne à {100 * pump.off_bep_ratio:.0f} % d'écart "
                        f"de son point de meilleur rendement : usure et consommation accrues."
                    ),
                    location=location,
                    details={"off_bep_ratio": pump.off_bep_ratio},
                )
            )
    return outcome


# --------------------------------------------------------------------------- C-007


def check_motor_power(pumps: list[PumpResult], rated_powers: dict[str, float]) -> CheckOutcome:
    """C-007 — Puissance absorbée supérieure à la puissance nominale du moteur."""
    outcome = CheckOutcome()
    evaluated = False

    for pump in pumps:
        if not pump.running or pump.absorbed_power_w is None:
            continue
        rated = rated_powers.get(pump.pump_id)
        if rated is None:
            continue
        evaluated = True
        if pump.absorbed_power_w > rated:
            outcome.violations.append(
                Violation(
                    code=ViolationCode.POWER,
                    severity=Severity.CRITICAL,
                    message=(
                        f"Puissance moteur dépassée sur « {pump.label} » : "
                        f"{pump.absorbed_power_w / 1e3:.0f} kW absorbés pour un moteur de "
                        f"{rated / 1e3:.0f} kW."
                    ),
                    location=Location(
                        object_type="pump", object_id=pump.pump_id, object_label=pump.label
                    ),
                    value=pump.absorbed_power_w,
                    limit=rated,
                    unit="W",
                    recommendation=(
                        "Réduisez le débit ou la vitesse de la pompe, ou vérifiez la puissance "
                        "nominale du moteur déclarée au catalogue."
                    ),
                    check_id="C-007",
                )
            )

    if evaluated:
        outcome.executed.add("C-007")
    else:
        outcome.skipped["C-007"] = (
            "Puissance absorbée ou puissance nominale moteur indisponible : le contrôle de "
            "puissance n'a pas pu être effectué."
        )
    return outcome


# --------------------------------------------------------------------------- C-008 / C-009


def check_tank_levels(tank: Tank, level_m: float, *, role: str) -> CheckOutcome:
    """C-008 et C-009 — Niveaux de réservoir hors des seuils d'exploitation."""
    outcome = CheckOutcome(executed={"C-008", "C-009"})
    location = Location(object_type="tank", object_id=tank.id, object_label=tank.display_name)

    if level_m < tank.levels.minimum_m - 1e-9:
        outcome.violations.append(
            Violation(
                code=ViolationCode.TANK_BELOW_MIN,
                severity=Severity.CRITICAL,
                message=(
                    f"Le bac {role} « {tank.display_name} » descend à {level_m:.3f} m, sous son "
                    f"niveau minimal d'exploitation de {tank.levels.minimum_m:.3f} m."
                ),
                location=location,
                value=level_m,
                limit=tank.levels.minimum_m,
                unit="m",
                recommendation=(
                    "Réduisez le volume à transférer ou arrêtez le mouvement au niveau bas."
                ),
                check_id="C-008",
            )
        )
    if level_m > tank.levels.high_high_m + 1e-9:
        outcome.violations.append(
            Violation(
                code=ViolationCode.TANK_ABOVE_HIGH_HIGH,
                severity=Severity.CRITICAL,
                message=(
                    f"Le bac {role} « {tank.display_name} » atteint {level_m:.3f} m, au-dessus de "
                    f"son niveau très haut de {tank.levels.high_high_m:.3f} m : risque de "
                    f"débordement."
                ),
                location=location,
                value=level_m,
                limit=tank.levels.high_high_m,
                unit="m",
                recommendation=(
                    "Réduisez le volume à transférer, choisissez un autre bac destinataire ou "
                    "arrêtez le mouvement au niveau haut."
                ),
                check_id="C-009",
            )
        )
    elif level_m > tank.levels.effective_high_m + 1e-9:
        outcome.warnings.append(
            Diagnostic(
                code=WarningCode.NEAR_LIMIT,
                message=(
                    f"Le bac {role} « {tank.display_name} » dépasse son niveau haut "
                    f"({tank.levels.effective_high_m:.3f} m) en atteignant {level_m:.3f} m."
                ),
                location=location,
                details={"level_m": level_m},
            )
        )
    return outcome


# --------------------------------------------------------------------------- C-010 / C-012


def check_convergence(
    converged: bool, residual: float, tolerance: float, iterations: int
) -> CheckOutcome:
    """C-010 et C-012 — Convergence et résidu.

    Ces deux contrôles sont indissociables d'un résultat approuvable : le produit ne doit
    jamais présenter comme valide un calcul dont la tolérance n'est pas atteinte
    (NFR-SCI-005).
    """
    outcome = CheckOutcome(executed={"C-010", "C-012"})
    if not converged:
        outcome.violations.append(
            Violation(
                code=ViolationCode.RESIDUAL_ABOVE_TOLERANCE,
                severity=Severity.CRITICAL,
                message=(
                    f"Le solveur n'a pas convergé : résidu {residual:.6g} après {iterations} "
                    f"itérations pour une tolérance de {tolerance:.3g}."
                ),
                value=residual,
                limit=tolerance,
                recommendation=(
                    "Élargissez le domaine de recherche, augmentez le nombre d'itérations, ou "
                    "vérifiez que les conditions aux limites admettent une solution physique."
                ),
                check_id="C-010",
            )
        )
    elif abs(residual) > tolerance:
        outcome.violations.append(
            Violation(
                code=ViolationCode.RESIDUAL_ABOVE_TOLERANCE,
                severity=Severity.CRITICAL,
                message=(
                    f"Résidu final {residual:.6g} supérieur à la tolérance {tolerance:.3g} malgré "
                    f"un arrêt déclaré convergé."
                ),
                value=abs(residual),
                limit=tolerance,
                check_id="C-012",
            )
        )
    return outcome


# --------------------------------------------------------------------------- C-011


def check_property_extrapolation(notes: tuple[str, ...], extrapolated: bool) -> CheckOutcome:
    """C-011 — Extrapolation de propriété physique."""
    outcome = CheckOutcome(executed={"C-011"})
    if extrapolated:
        outcome.warnings.append(
            Diagnostic(
                code=WarningCode.EXTRAPOLATION,
                message=(
                    "Au moins une propriété du produit a été extrapolée hors de son domaine "
                    "tabulé : " + " ".join(notes)
                ),
                details={"notes": list(notes)},
            )
        )
    return outcome


# --------------------------------------------------------------------------- station


def check_station_pressures(
    stations: list[StationResult], limits: dict[str, dict[str, float | None]]
) -> CheckOutcome:
    """Contrôles de pression propres aux stations : aspiration minimale et refoulement maximal.

    Ces limites relèvent de l'équipement de la station (brides, corps de pompe, soupapes) et
    complètent le contrôle C-004 qui porte sur la conduite.
    """
    outcome = CheckOutcome()
    if not stations:
        return outcome

    evaluated = False
    for station in stations:
        if not station.in_service:
            continue
        station_limits = limits.get(station.station_id, {})
        suction_min = station_limits.get("suction_min")
        discharge_max = station_limits.get("discharge_max")
        location = Location(
            object_type="station",
            object_id=station.station_id,
            object_label=station.name,
            chainage_m=station.chainage_m,
        )
        if suction_min is not None:
            evaluated = True
            if station.suction_pressure_pa < suction_min:
                outcome.violations.append(
                    Violation(
                        code=ViolationCode.SUCTION_PRESSURE_LOW,
                        severity=Severity.CRITICAL,
                        message=(
                            f"Pression d'aspiration insuffisante à la station « {station.name} » : "
                            f"{station.suction_pressure_pa / 1e5:.2f} bar pour un minimum de "
                            f"{suction_min / 1e5:.2f} bar."
                        ),
                        location=location,
                        value=station.suction_pressure_pa,
                        limit=suction_min,
                        unit="Pa",
                        recommendation=(
                            "Augmentez la pression amont, réduisez le débit ou mettez en service "
                            "une pompe de gavage."
                        ),
                        check_id="C-004",
                    )
                )
        if discharge_max is not None:
            evaluated = True
            if station.discharge_pressure_pa > discharge_max:
                outcome.violations.append(
                    Violation(
                        code=ViolationCode.DISCHARGE_PRESSURE_HIGH,
                        severity=Severity.CRITICAL,
                        message=(
                            f"Pression de refoulement excessive à la station « {station.name} » : "
                            f"{station.discharge_pressure_pa / 1e5:.2f} bar pour un maximum de "
                            f"{discharge_max / 1e5:.2f} bar."
                        ),
                        location=location,
                        value=station.discharge_pressure_pa,
                        limit=discharge_max,
                        unit="Pa",
                        recommendation=(
                            "Arrêtez une pompe, réduisez la vitesse, ou vérifiez la limite de "
                            "refoulement retenue pour cette station."
                        ),
                        check_id="C-004",
                    )
                )
    if evaluated:
        outcome.executed.add("C-004")
    return outcome
