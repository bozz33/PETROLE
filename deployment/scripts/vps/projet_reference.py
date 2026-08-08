"""Construit le projet de référence attendu par la recette métier.

Le cahier des charges fixe la taille du cas de réception : au moins cent
tronçons, cinq stations, quinze pompes et dix réservoirs, avec une baseline
convergente puis les scénarios nominal et dégradés.

Ce script prépare ce cas dans une instance, uniquement par les interfaces
publiques de l'API. Il ne remplace pas la recette : il fournit à l'ingénieur un
dossier complet et reproductible à examiner, à exécuter et à accepter ou refuser.

Utilisation :
    python deployment/scripts/vps/projet_reference.py \\
        --base-url https://exemple/api/v1 --email … --password …
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from typing import Any

SEGMENT_COUNT = 100
STATION_COUNT = 5
PUMPS_PER_STATION = 3
TANK_COUNT = 10

# Le tracé est dimensionné pour que quinze pompes trouvent un point de
# fonctionnement acceptable : 200 km en DN600, relief modéré. La première
# station est volontairement proche du bac amont : avec 32 km sans reprise, la
# charge hydrostatique du bac ne suffisait pas à protéger l'aspiration contre la
# cavitation lors d'un transfert HydroLiquid réellement couplé. La longueur
# totale et le nombre de tronçons restent inchangés ; seule leur répartition est
# physique pour le cas de référence.
SEGMENT_LENGTH_M = 2_000.0
UPSTREAM_SEGMENT_COUNT = SEGMENT_COUNT // (STATION_COUNT + 1)
UPSTREAM_SEGMENT_LENGTH_M = 125.0
DOWNSTREAM_SEGMENT_LENGTH_M = (
    SEGMENT_COUNT * SEGMENT_LENGTH_M - UPSTREAM_SEGMENT_COUNT * UPSTREAM_SEGMENT_LENGTH_M
) / (SEGMENT_COUNT - UPSTREAM_SEGMENT_COUNT)
INNER_DIAMETER_M = 0.5810
OUTER_DIAMETER_M = 0.6096
WALL_THICKNESS_M = 0.0143
ROUGHNESS_M = 4.5e-5
MAWP_PA = 8.0e6


def segment_length_m(index: int) -> float:
    """Retourne la longueur du tronçon zéro-indexé du cas de référence."""

    if not 0 <= index < SEGMENT_COUNT:
        raise ValueError(f"Indice de tronçon hors limites : {index}")
    if index < UPSTREAM_SEGMENT_COUNT:
        return UPSTREAM_SEGMENT_LENGTH_M
    return DOWNSTREAM_SEGMENT_LENGTH_M


class ApiError(RuntimeError):
    """Erreur renvoyée par l'API, conservée telle quelle pour le diagnostic."""


class Client:
    """Client HTTP minimal : le script ne dépend que de la bibliothèque standard."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        *,
        idempotency_key: str | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        if idempotency_key:
            request.add_header("Idempotency-Key", idempotency_key)
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ApiError(f"{method} {path} → {error.code} : {detail}") from error

    def login(self, email: str, password: str) -> None:
        tokens = self.request("POST", "/auth/login", {"email": email, "password": password})
        self.token = tokens["access_token"]


def elevation_at(index: int) -> float:
    """Profil légèrement ondulé et globalement descendant.

    Les ondulations restent assez marquées pour produire des points hauts et
    exercer la détection de zones gravitaires, sans imposer aux stations une
    charge que cinq groupes ne pourraient pas fournir.
    """

    progress = index / SEGMENT_COUNT
    return 90.0 + 12.0 * math.sin(progress * 3.0 * math.pi) - 45.0 * progress


def build(client: Client, approver: Client, organization_id: str) -> dict[str, Any]:
    """Monte le dossier de référence.

    Deux comptes sont nécessaires : un ingénieur crée et configure, un
    approbateur valide les références du catalogue. Cette séparation est celle
    du workflow métier ; la contourner avec un compte unique masquerait un
    contrôle que la recette doit précisément éprouver.
    """

    project = client.request(
        "POST",
        "/projects",
        {
            "organization_id": organization_id,
            "name": "Oléoduc de référence — recette MVP",
            "code": "REF-MVP-01",
            "description": ("Cas de réception : 100 tronçons, 5 stations, 15 pompes et 10 bacs."),
            "project_type": "liquid_pipeline",
        },
    )
    print(f"Projet {project['code']} créé.")

    fluid = client.request(
        "POST",
        "/catalog/fluids",
        {
            "organization_id": organization_id,
            "code": "REF-BRUT-01",
            "name": "Brut léger de référence",
            "source": "Jeu de référence de recette ; ne remplace pas une analyse laboratoire.",
            "payload": {
                "category": "crude",
                "reference_temperature_k": 288.15,
                "reference_pressure_pa": 101325.0,
                "density_kg_m3": 845.0,
                "kinematic_viscosity_m2_s": 5.5e-6,
                "vapor_pressure_pa": 4_500.0,
                "data_source": "Jeu de référence de recette",
            },
        },
    )
    approver.request("POST", f"/catalog/items/{fluid['id']}/approve")

    pump = client.request(
        "POST",
        "/catalog/pumps",
        {
            "organization_id": organization_id,
            "code": "REF-POMPE-01",
            "name": "Pompe centrifuge de référence",
            "source": "Courbe de référence de recette ; ne remplace pas une courbe certifiée.",
            "payload": {
                "curve": {
                    "flows_m3_s": [0.10, 0.20, 0.30, 0.40],
                    "heads_m": [235.0, 210.0, 172.0, 118.0],
                    "efficiencies": [0.68, 0.81, 0.84, 0.74],
                    "npshr_m": [3.0, 4.2, 6.1, 9.4],
                    "reference_speed_rpm": 2_980,
                    "interpolation": "pchip",
                },
                "manufacturer": "Constructeur de référence",
                "motor_rated_power_w": 1_200_000.0,
                "npsh_margin_m": 0.5,
                "min_speed_ratio": 0.7,
                "max_speed_ratio": 1.0,
                "data_source": "Jeu de référence de recette",
            },
        },
    )
    approver.request("POST", f"/catalog/items/{pump['id']}/approve")

    material = client.request(
        "POST",
        "/catalog/materials",
        {
            "organization_id": organization_id,
            "code": "REF-ACIER-X52",
            "name": "Acier API 5L X52",
            "payload": {
                "roughness_m": ROUGHNESS_M,
                "mawp_pa": MAWP_PA,
                "material_family": "Acier au carbone",
                "specification": "API 5L",
                "grade": "X52",
                "outer_diameter_m": OUTER_DIAMETER_M,
                "wall_thickness_m": WALL_THICKNESS_M,
            },
        },
    )
    approver.request("POST", f"/catalog/items/{material['id']}/approve")
    print("Produit, pompe et matériau approuvés.")

    tanks = []
    for index in range(1, TANK_COUNT + 1):
        tanks.append(
            client.request(
                "POST",
                "/tanks",
                {
                    "organization_id": organization_id,
                    "name": f"Bac de référence {index:02d}",
                    "code": f"TK-{index:02d}",
                    "tank_type": "vertical_fixed_roof",
                    "elevation_m": 120.0 if index == 1 else 60.0,
                    "current_level_m": 9.0 if index == 1 else 3.0,
                    "fluid_id": "REF-BRUT-01" if index == 1 else None,
                    "compatible_fluid_ids": ["REF-BRUT-01"],
                    "levels": {
                        "minimum_m": 0.8,
                        "low_m": 1.5,
                        "normal_m": 7.0,
                        "high_m": 13.0,
                        "high_high_m": 14.0,
                    },
                    "strapping": [
                        {"height_m": 0.0, "volume_m3": 0.0},
                        {"height_m": 7.5, "volume_m3": 6_000.0},
                        {"height_m": 15.0, "volume_m3": 12_000.0},
                    ],
                },
            )
        )
    print(f"{len(tanks)} bacs créés.")

    model = client.request(
        "POST",
        f"/projects/{project['id']}/models",
        {
            "name": "Baseline de référence",
            "payload": {
                "units": {"system": "SI"},
                "fluid_catalog_item_id": fluid["id"],
            },
        },
    )
    model_id = model["id"]

    # Le chaînage part du bac amont et se termine sur le bac aval : le transfert
    # couplé au réseau exige ces deux raccordements explicites.
    nodes: list[dict[str, Any]] = [
        client.request(
            "POST",
            f"/models/{model_id}/nodes",
            {
                "code": "ND-000",
                "name": "Raccordement bac amont",
                "kind": "tank",
                "elevation_m": elevation_at(0),
                "status": "available",
                "payload": {"tank_id": tanks[0]["id"]},
            },
        )
    ]

    station_positions = {
        index * (SEGMENT_COUNT // (STATION_COUNT + 1)) for index in range(1, STATION_COUNT + 1)
    }
    for index in range(1, SEGMENT_COUNT):
        if index in station_positions:
            kind, name = "station", f"Station de pompage {index:03d}"
            payload: dict[str, Any] = {
                "arrangement": "series",
                "suction_pressure_min_pa": 150_000.0,
                "discharge_pressure_max_pa": 7_500_000.0,
                "suction_line_k": 1.2,
                "suction_line_diameter_m": 0.6,
                "bypass_k": 0.0,
                "drive_efficiency": 0.95,
            }
        else:
            kind, name, payload = "junction", f"Jonction {index:03d}", {}
        nodes.append(
            client.request(
                "POST",
                f"/models/{model_id}/nodes",
                {
                    "code": f"ND-{index:03d}",
                    "name": name,
                    "kind": kind,
                    "elevation_m": elevation_at(index),
                    "status": "available",
                    "payload": payload,
                },
            )
        )

    nodes.append(
        client.request(
            "POST",
            f"/models/{model_id}/nodes",
            {
                "code": f"ND-{SEGMENT_COUNT:03d}",
                "name": "Raccordement bac aval",
                "kind": "tank",
                "elevation_m": elevation_at(SEGMENT_COUNT),
                "status": "available",
                "payload": {"tank_id": tanks[1]["id"]},
            },
        )
    )
    print(f"{len(nodes)} nœuds créés, dont {len(station_positions)} stations.")

    for index in range(SEGMENT_COUNT):
        start, end = nodes[index], nodes[index + 1]
        length_m = segment_length_m(index)
        client.request(
            "POST",
            f"/models/{model_id}/edges",
            {
                "from_node_id": start["id"],
                "to_node_id": end["id"],
                "material_catalog_item_id": material["id"],
                "code": f"TR-{index + 1:03d}",
                "name": f"Tronçon {index + 1:03d}",
                "sequence": index + 1,
                "length_m": length_m,
                "inner_diameter_m": INNER_DIAMETER_M,
                "roughness_m": ROUGHNESS_M,
                "mawp_pa": MAWP_PA,
                "status": "available",
                "profile": [
                    {"chainage_m": 0.0, "elevation_m": start["elevation_m"]},
                    {"chainage_m": length_m, "elevation_m": end["elevation_m"]},
                ],
                "fittings": [],
                "payload": {
                    "outer_diameter_m": OUTER_DIAMETER_M,
                    "wall_thickness_m": WALL_THICKNESS_M,
                },
            },
        )
    print(f"{SEGMENT_COUNT} tronçons créés.")

    pump_count = 0
    for node in nodes:
        if node["kind"] != "station":
            continue
        for rank in range(1, PUMPS_PER_STATION + 1):
            pump_count += 1
            client.request(
                "POST",
                f"/models/{model_id}/assets",
                {
                    "catalog_item_id": pump["id"],
                    "node_id": node["id"],
                    "code": f"P-{pump_count:03d}",
                    "name": f"Pompe {rank} de {node['code']}",
                    # Une pompe principale et deux secours par station : trois
                    # groupes en série ajouteraient plus de 50 bar par station et
                    # dépasseraient la pression maximale admissible de la conduite.
                    "role": "main" if rank == 1 else "standby",
                    "status": "available",
                    "payload": {},
                },
            )
    print(f"{pump_count} pompes placées.")

    # Sans jeu de règles approuvé, la conformité reste « non évaluée » et aucune
    # décision positive n'est possible : le dossier de référence doit donc en
    # porter un, rattaché au projet.
    standard = client.request(
        "POST",
        "/standards",
        {
            "organization_id": organization_id,
            "code": "REF-INTERNE-01",
            "title": "Limites internes d'exploitation du cas de référence",
            "issuing_body": "Exploitant",
            "edition": "2026",
            "licensed_copy_ref": (
                "Référentiel interne du jeu de recette ; ne reprend aucun texte normatif."
            ),
        },
    )
    approver.request("POST", f"/standards/{standard['id']}/approve")

    rule_set = client.request(
        "POST",
        "/rule-sets",
        {
            "organization_id": organization_id,
            "code": "REF-REGLES-01",
            "title": "Règles d'exploitation du cas de référence",
            "domain": "hydraulique",
            "description": (
                "Seuils internes de vitesse et de pression, servant à éprouver "
                "l'évaluation normative. Ils n'établissent aucune conformité."
            ),
            "standard_ids": [standard["id"]],
        },
    )
    rules = [
        # Les métriques visées sont celles réellement publiées à la racine du
        # résultat : viser un champ absent produirait une évaluation en erreur,
        # donc une conformité indéterminée bloquant toute décision.
        {
            "code": "REF-PRESS-MAX",
            "title": "Pression maximale en ligne",
            "severity": "blocking",
            "domain": "hydraulique",
            "metric_path": "max_pressure_pa",
            "operator": "le",
            "limit_value": MAWP_PA,
            "unit": "Pa",
            "message": "La pression dépasse la pression maximale admissible de la conduite.",
        },
        {
            "code": "REF-PRESS-MIN",
            "title": "Pression minimale en ligne",
            "severity": "blocking",
            "domain": "hydraulique",
            "metric_path": "min_pressure_pa",
            "operator": "ge",
            "limit_value": 120_000.0,
            "unit": "Pa",
            "message": "La pression descend sous la limite interne de 1,2 bar absolu.",
        },
    ]
    for rule in rules:
        created_rule = client.request(
            "POST", f"/rule-sets/{rule_set['id']}/rules", {**rule, "standard_id": standard["id"]}
        )
        approver.request("POST", f"/rules/{created_rule['id']}/approve")
    approver.request("POST", f"/rule-sets/{rule_set['id']}/approve")

    client.request(
        "PATCH",
        f"/projects/{project['id']}",
        {"rule_set_ids": [rule_set["id"]]},
    )
    print("Jeu de règles interne approuvé et rattaché au projet.")

    validation = client.request("POST", f"/models/{model_id}/validate")
    print(
        "Validation du réseau : "
        f"{len(validation['errors'])} erreur(s), {len(validation['warnings'])} avertissement(s)."
    )

    scenarios = []
    base_solver = {
        "friction_model": "colebrook_white",
        "pressure_tolerance_pa": 1.0,
        "flow_tolerance_m3_s": 1e-9,
        "mass_balance_tolerance": 1e-6,
        "max_iterations": 200,
        "profile_step_m": 1000.0,
        "store_iterations": False,
        "use_quadratic_pump_fit": False,
        "max_flow_m3_s": 1.2,
        "detect_gravity_zones": True,
        "apply_gravity_model": False,
        "min_velocity_m_s": None,
        "max_velocity_m_s": 3.0,
    }
    # Les secours restent à l'arrêt tant qu'un scénario ne les appelle pas.
    standby_ids = [
        f"P-{index:03d}"
        for index in range(1, pump_count + 1)
        if (index - 1) % PUMPS_PER_STATION != 0
    ]
    at_rest = [
        {"pump_id": identifier, "status": None, "running": False, "speed_ratio": None}
        for identifier in standby_ids
    ]
    first_pump = "P-001"
    definitions = [
        ("Régime nominal", "Une pompe principale par station, secours à l'arrêt.", at_rest),
        (
            "Pompe indisponible",
            "La pompe principale de la première station est hors service.",
            [
                *at_rest,
                {
                    "pump_id": first_pump,
                    "status": "unavailable",
                    "running": False,
                    "speed_ratio": None,
                },
            ],
        ),
        (
            "Marche en secours",
            "Le premier secours prend le relais de la pompe indisponible.",
            [
                *[override for override in at_rest if override["pump_id"] != "P-002"],
                {
                    "pump_id": first_pump,
                    "status": "unavailable",
                    "running": False,
                    "speed_ratio": None,
                },
                {"pump_id": "P-002", "status": None, "running": True, "speed_ratio": 1.0},
            ],
        ),
        (
            "Débit réduit",
            "Vitesse abaissée sur la première station.",
            [
                *at_rest,
                {"pump_id": first_pump, "status": None, "running": True, "speed_ratio": 0.8},
            ],
        ),
    ]
    for name, description, overrides in definitions:
        scenarios.append(
            client.request(
                "POST",
                f"/models/{model_id}/scenarios",
                {
                    "name": name,
                    "description": description,
                    "payload": {
                        "temperature_k": 288.15,
                        # Un débit d'exploitation et une pression d'aspiration
                        # connue : c'est le cas courant. Laisser le débit
                        # s'établir librement avec quinze pompes disponibles
                        # conduit à un point de fonctionnement irréaliste, que le
                        # moteur signale correctement mais qui ne constitue pas
                        # une baseline exploitable.
                        "imposed_flow_m3_s": 0.25,
                        "inlet_pressure_pa": 600_000.0,
                        "outlet_pressure_pa": None,
                        "inlet_tank_level_m": None,
                        "outlet_tank_level_m": None,
                        "pump_overrides": overrides,
                        "station_overrides": [],
                        "segment_overrides": [],
                        "solver": base_solver,
                        "objective": None,
                        "energy_price_per_joule": None,
                    },
                },
            )
        )
    print(f"{len(scenarios)} scénarios créés.")

    return {
        "project_id": project["id"],
        "model_version_id": model_id,
        "scenario_ids": [item["id"] for item in scenarios],
        "tank_ids": [item["id"] for item in tanks],
        "validation": validation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--approver-email", required=True)
    parser.add_argument("--approver-password", required=True)
    arguments = parser.parse_args()

    client = Client(arguments.base_url)
    client.login(arguments.email, arguments.password)
    approver = Client(arguments.base_url)
    approver.login(arguments.approver_email, arguments.approver_password)

    organizations = client.request("GET", "/organizations?limit=1&offset=0")
    if not organizations["items"]:
        print("Aucune organisation accessible.", file=sys.stderr)
        return 1
    organization_id = organizations["items"][0]["id"]

    try:
        summary = build(client, approver, organization_id)
    except ApiError as error:
        print(f"Échec : {error}", file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
