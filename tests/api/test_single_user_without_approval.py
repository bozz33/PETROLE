"""Contrat du déploiement PETROLE mono-utilisateur sans workflow d'approbation."""

from __future__ import annotations

from hydro_api.single_user_mode import configure_single_user_workflow


def _bootstrap(client) -> tuple[dict, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "ingenieur@petrole.example.com",
            "full_name": "Ingénieur PETROLE",
            "password": "mot-de-passe-recette-1234",
            "organization_name": "Valeur ignorée en single_org",
            "organization_slug": "valeur-ignoree",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    organizations = client.get("/api/v1/organizations?limit=10&offset=0", headers=headers)
    assert organizations.status_code == 200, organizations.text
    return organizations.json()["items"][0], headers


def test_single_org_ne_demande_aucune_approbation(api_client_factory) -> None:
    try:
        with api_client_factory(
            deployment_mode="single_org",
            authentication_required=True,
            jwt_secret="test-single-user-secret-0123456789abcdef",
            default_organization_name="PETROLE",
            default_organization_slug="petrole",
        ) as client:
            organization, headers = _bootstrap(client)

            openapi = client.get("/api/v1/openapi.json").json()
            assert not [path for path in openapi["paths"] if path.endswith("/approve")]

            approver = client.post(
                f"/api/v1/organizations/{organization['id']}/members",
                headers=headers,
                json={
                    "email": "approver@petrole.example.com",
                    "full_name": "Ancien approbateur",
                    "password": "mot-de-passe-approver-1234",
                    "role": "approver",
                },
            )
            assert approver.status_code == 422, approver.text

            fluid = client.post(
                "/api/v1/catalog/fluids",
                headers=headers,
                json={
                    "organization_id": organization["id"],
                    "code": "BRUT-SU",
                    "name": "Brut mono-utilisateur",
                    "payload": {
                        "category": "crude",
                        "reference_temperature_k": 288.15,
                        "reference_pressure_pa": 101325.0,
                        "density_kg_m3": 850.0,
                        "kinematic_viscosity_m2_s": 5.0e-6,
                        "vapor_pressure_pa": 4500.0,
                    },
                },
            )
            assert fluid.status_code == 201, fluid.text
            # Valeur SQL historique conservée pour compatibilité ; aucune action
            # humaine n'a été effectuée pour obtenir ce statut.
            assert fluid.json()["status"] == "approved"
            assert (
                client.post(
                    f"/api/v1/catalog/items/{fluid.json()['id']}/approve",
                    headers=headers,
                ).status_code
                == 404
            )

            standard = client.post(
                "/api/v1/standards",
                headers=headers,
                json={
                    "organization_id": organization["id"],
                    "code": "REF-SU-001",
                    "title": "Référence interne mono-utilisateur",
                    "issuing_body": "PETROLE",
                    "edition": "2026",
                },
            )
            assert standard.status_code == 201, standard.text
            assert standard.json()["status"] == "active"

            rule_set = client.post(
                "/api/v1/rule-sets",
                headers=headers,
                json={
                    "organization_id": organization["id"],
                    "code": "REGLES-SU",
                    "title": "Règles mono-utilisateur",
                    "domain": "pipeline_liquide",
                    "standard_ids": [standard.json()["id"]],
                },
            )
            assert rule_set.status_code == 201, rule_set.text
            assert rule_set.json()["status"] == "approved"

            for index, metric in enumerate(("max_pressure_pa", "min_pressure_pa"), start=1):
                rule = client.post(
                    f"/api/v1/rule-sets/{rule_set.json()['id']}/rules",
                    headers=headers,
                    json={
                        "standard_id": standard.json()["id"],
                        "code": f"REGLE-{index}",
                        "title": f"Règle {index}",
                        "severity": "warning",
                        "domain": "hydraulique",
                        "metric_path": metric,
                        "operator": "le" if index == 1 else "ge",
                        "limit_value": 8_000_000.0 if index == 1 else 0.0,
                        "message": "Contrôle automatique.",
                    },
                )
                assert rule.status_code == 201, rule.text
                assert rule.json()["status"] == "approved"

            rules = client.get(
                f"/api/v1/rule-sets/{rule_set.json()['id']}/rules",
                headers=headers,
            )
            assert rules.status_code == 200, rules.text
            assert len(rules.json()) == 2

            project = client.post(
                "/api/v1/projects",
                headers=headers,
                json={
                    "organization_id": organization["id"],
                    "name": "Projet ingénieur unique",
                    "code": "SU-01",
                    "project_type": "liquid_pipeline",
                    "rule_set_ids": [rule_set.json()["id"]],
                },
            )
            assert project.status_code == 201, project.text
            assert project.json()["rule_set_ids"] == [rule_set.json()["id"]]
    finally:
        # Évite qu'un test suivant en mode multi_org hérite des adaptations
        # process-globales utilisées par cette application isolée.
        configure_single_user_workflow(False)
