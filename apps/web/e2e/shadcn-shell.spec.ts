import { expect, test, type Page, type Route } from "@playwright/test";

const now = "2026-08-03T09:00:00Z";
const organization = {
  id: "org-1",
  name: "PETROLE Démonstration",
  slug: "petrole-demo",
  default_locale: "fr-CI",
  default_unit_system: "SI",
  archived_at: null,
  created_at: now,
  updated_at: now,
};
const project = {
  id: "project-1",
  organization_id: organization.id,
  site_id: null,
  name: "Pipeline Abidjan–Bouaké",
  code: "PL-ABK-001",
  description: "Cas de démonstration du réseau liquide.",
  project_type: "liquid_pipeline",
  country_code: "ci",
  unit_system: "SI",
  rule_set_ids: [],
  responsible_user_ids: [],
  status: "active",
  created_at: now,
  updated_at: now,
};
const model = {
  id: "model-1",
  project_id: project.id,
  parent_id: null,
  version_number: 1,
  name: "Réseau de référence",
  status: "approved",
  content_hash: "demo-model-hash",
  payload: {},
  approved_at: now,
  created_at: now,
  updated_at: now,
};
const nodes = [
  networkNode("node-source", "SRC-01", "Dépôt Abidjan", "source", 18, 5.32, -4.02),
  networkNode("node-station", "ST-01", "Station intermédiaire", "station", 145, 6.3, -4.7),
  networkNode("node-terminal", "TRM-01", "Terminal Bouaké", "terminal", 310, 7.69, -5.03),
];
const edges = [
  networkEdge("edge-1", "node-source", "node-station", "L-001", "Tronçon Sud", 1, 132_000),
  networkEdge("edge-2", "node-station", "node-terminal", "L-002", "Tronçon Nord", 2, 218_000),
];

function networkNode(
  id: string,
  code: string,
  name: string,
  kind: string,
  elevation_m: number,
  latitude: number,
  longitude: number,
) {
  return {
    id,
    model_version_id: model.id,
    code,
    name,
    kind,
    elevation_m,
    latitude,
    longitude,
    status: "available",
    payload: {},
    created_at: now,
    updated_at: now,
  };
}

function networkEdge(
  id: string,
  from_node_id: string,
  to_node_id: string,
  code: string,
  name: string,
  sequence: number,
  length_m: number,
) {
  return {
    id,
    model_version_id: model.id,
    from_node_id,
    to_node_id,
    material_catalog_item_id: null,
    code,
    name,
    sequence,
    length_m,
    inner_diameter_m: 0.4064,
    roughness_m: 0.000045,
    mawp_pa: 8_000_000,
    status: "available",
    profile_payload: [],
    fittings_payload: [],
    payload: {},
    created_at: now,
    updated_at: now,
  };
}

function pageOf<T>(items: T[]) {
  return { items, total: items.length, limit: 2000, offset: 0 };
}

async function respond(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApiMock(page: Page): Promise<void> {
  await page.route("https://demotiles.maplibre.org/style.json", (route) =>
    respond(route, { version: 8, name: "PETROLE test style", sources: {}, layers: [] }),
  );

  await page.route(/\/api\/v1\//, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api/v1", "");
    const fixtures: Record<string, unknown> = {
      "/auth/status": { authentication_required: false, initialized: true },
      "/health": {
        status: "ok",
        service: "hydro-api",
        version: "0.1.0-test",
        environment: "test",
        build: {
          application_version: "0.1.0-test",
          git_sha: "0000000000000000",
          ref: "test",
          build_date: "2026-08-07T00:00:00Z",
          scientific_engine_version: "hydroliquid-0.1.0",
          database_migration_version: "8b1f2d6c4e90",
        },
        deployment: { mode: "single_org", organization_label: "Exploitant" },
      },
      "/health/validation": {
        suite: "scientific-validation",
        passed: 41,
        total: 41,
        proof_hash: "0".repeat(64),
        engine_version: "hydroliquid-0.1.0",
        executed_at: "2026-08-07T00:00:00Z",
        environment: "test",
        source: "docs/validation",
      },
      "/health/ready": {
        status: "ready",
        database: "ready",
        object_storage: "ready",
      },
      "/organizations": pageOf([organization]),
      "/projects": pageOf([project]),
      [`/projects/${project.id}/models`]: pageOf([model]),
      [`/models/${model.id}/nodes`]: pageOf(nodes),
      [`/models/${model.id}/edges`]: pageOf(edges),
      [`/models/${model.id}/assets`]: pageOf([]),
      [`/models/${model.id}/validate`]: {
        model_version_id: model.id,
        valid: true,
        errors: [],
        warnings: [],
      },
    };

    if (path in fixtures) {
      await respond(route, fixtures[path]);
      return;
    }
    await respond(route, request.method() === "GET" ? pageOf([]) : {});
  });
}

test.beforeEach(async ({ page }, testInfo) => {
  if (testInfo.project.name === "mobile") {
    await page.setViewportSize({ width: 390, height: 844 });
  }
  await installApiMock(page);
});

test("affiche le tableau de bord et conserve le thème sombre", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  await expect(page.getByText("Pipeline Abidjan–Bouaké")).toBeVisible();
  // Le graphique d'activité de démonstration a été retiré : le tableau de bord
  // publie désormais l'attestation scientifique réellement servie par l'API.
  await expect(page.getByText("41 / 41")).toBeVisible();
  await expect(page.locator("canvas")).toHaveCount(0);

  await page.getByRole("button", { name: "Activer le mode sombre" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("navigue avec la palette de commandes", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "bureau", "La palette globale est vérifiée sur bureau.");

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  await page.getByRole("search").getByLabel("Rechercher").click();

  const dialog = page.getByRole("dialog", { name: "Recherche globale" });
  await expect(dialog).toBeVisible();
  await dialog.getByPlaceholder("Rechercher une page ou une fonction…").fill("rapports");
  await dialog.getByRole("button", { name: /Rapports/ }).click();

  await expect(page).toHaveURL(/\/rapports$/);
  await expect(page.getByRole("heading", { level: 1, name: "Rapports" })).toBeVisible();
});

test("affiche le réseau avec React Flow et MapLibre", async ({ page }) => {
  await page.goto("/reseau");
  await expect(page.getByRole("heading", { level: 1, name: "Visualisation du réseau" })).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(3);
  await expect(page.locator(".react-flow__edge")).toHaveCount(2);
  await expect(page.getByText("350 km")).toBeVisible();

  await page.getByRole("button", { name: "Carte" }).click();
  await expect(page.getByRole("heading", { level: 2, name: "Carte du réseau" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Carte géographique du pipeline" })).toBeVisible();
  const geolocatedCount = page
    .locator(".resource-summary > div")
    .filter({ hasText: "Nœuds géolocalisés" });
  await expect(geolocatedCount.getByText("3", { exact: true })).toBeVisible();
});

test("ouvre la navigation mobile", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "Scénario réservé à la vue mobile.");
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();

  const menuButton = page.locator(".mobile-menu-button");
  await expect(menuButton).toHaveCount(1);
  await expect(menuButton).toHaveAttribute("aria-label", "Ouvrir la navigation");
  await menuButton.evaluate((element: HTMLButtonElement) => element.click());
  await expect(page.locator("aside.sidebar")).toHaveClass(/is-mobile-open/);

  await page.getByRole("link", { name: "Rapports" }).click();
  await expect(page).toHaveURL(/\/rapports$/);
});

test("réduit et restaure la barre latérale", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "bureau", "Scénario réservé à la vue bureau.");
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  await page.getByRole("button", { name: "Réduire la barre latérale" }).click();
  await expect(page.locator(".app-shell")).toHaveClass(/sidebar-collapsed/);
  await page.getByRole("button", { name: "Déployer la barre latérale" }).click();
  await expect(page.locator(".app-shell")).not.toHaveClass(/sidebar-collapsed/);
});

test("confine les longues ressources de scénarios dans leurs défilements", async ({ page }) => {
  const longEdges = Array.from({ length: 100 }, (_, index) =>
    networkEdge(
      "edge-scenario-" + index,
      index === 0 ? "node-source" : "node-station",
      index === 99 ? "node-terminal" : "node-station",
      "L-" + String(index + 1).padStart(3, "0"),
      "Tronçon " + String(index + 1),
      index + 1,
      10_000,
    ),
  );
  const pumps = Array.from({ length: 15 }, (_, index) => ({
    id: "pump-" + index,
    model_version_id: model.id,
    code: "P-" + String(index + 1).padStart(2, "0"),
    name: "Pompe " + String(index + 1),
    role: "main",
  }));

  await page.route(/\/api\/v1\/models\/model-1\/edges/, (route) => respond(route, pageOf(longEdges)));
  await page.route(/\/api\/v1\/models\/model-1\/assets/, (route) => respond(route, pageOf(pumps)));

  await page.goto("/scenarios");
  await expect(page.getByText("Renseignez deux conditions indépendantes")).toBeVisible();
  await expect(page.locator('[role="alert"]')).toHaveCount(0);

  for (const label of ["Pompes — défilement interne", "Tronçons — défilement interne"]) {
    const resource = page.getByLabel(label);
    await expect(resource).toHaveCSS("overflow-y", "auto");
    const size = await resource.evaluate((element) => ({
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }));
    expect(size.scrollHeight).toBeGreaterThan(size.clientHeight);
  }

  const bodyHeight = await page.evaluate(() => document.body.scrollHeight);
  // Sur mobile le formulaire se présente en une colonne et mesure environ
  // 4,9 kpx. Ce seuil laisse ce contenu légitime, tout en empêchant les
  // 100 lignes de tronçons de redevenir un défilement de page géant.
  expect(bodyHeight).toBeLessThan(6_000);
});

test("restitue les enveloppes ingénieur et exporte les graphiques sans inventer de limite", async ({ page }) => {
  const scenario = {
    id: "scenario-engineering-1",
    model_version_id: model.id,
    name: "Régime stationnaire multi-stations",
    description: null,
    payload: {},
    status: "approved",
    created_at: now,
    updated_at: now,
  };
  const calculation = {
    id: "calculation-engineering-1",
    scenario_id: scenario.id,
    engine: "long_distance_liquid",
    engine_version: "long-distance-liquid-1.0.0",
    status: "SIM_CONVERGED",
    phase: "completed",
    progress_percent: 100,
    input_hash: "engineering-result-hash",
    approval_status: "pending",
    approval_comment: null,
    approved_at: null,
    created_at: now,
    started_at: now,
    finished_at: now,
  };
  const engineeringResult = {
    calculation_id: calculation.id,
    status: calculation.status,
    diagnostics: {},
    result: {
      status: calculation.status,
      flow_m3_s: 0.2,
      min_pressure_pa: 1_200_000,
      max_pressure_pa: 3_500_000,
      total_head_loss_m: 45,
      total_power_w: 150_000,
      residual: 0.000001,
      feasible: true,
      physical_approvable: true,
      compliance_status: "not_evaluated",
      decision_eligible: false,
      approvable: false,
      compliance: {
        status: "not_evaluated",
        counts: { total: 0, compliant: 0, non_compliant: 0, not_applicable: 0, errors: 0 },
        blocking_failure_count: 0,
        reservation_count: 0,
        blocking_rule_ids: [],
      },
      rule_evaluations: [],
      violations: [],
      warnings: [],
      profile: [
        {
          chainage_m: 0,
          elevation_m: 18,
          pressure_pa: 3_500_000,
          hydraulic_grade_m: 430,
          flow_m3_s: 0.2,
          velocity_m_s: 1.55,
          below_vapor_pressure: false,
          gravity_zone: false,
        },
        {
          chainage_m: 132_000,
          elevation_m: 145,
          pressure_pa: 1_200_000,
          hydraulic_grade_m: 285,
          flow_m3_s: 0.2,
          velocity_m_s: 1.55,
          below_vapor_pressure: true,
          gravity_zone: true,
        },
        {
          chainage_m: 350_000,
          elevation_m: 310,
          pressure_pa: 3_000_000,
          hydraulic_grade_m: 660,
          flow_m3_s: 0.2,
          velocity_m_s: 1.55,
          below_vapor_pressure: false,
          gravity_zone: false,
        },
      ],
      segments: [
        {
          segment_id: "L-001",
          label: "Tronçon Sud",
          flow_m3_s: 0.2,
          velocity_m_s: 1.55,
          reynolds: 125_000,
          friction_factor: 0.018,
          friction_model: "colebrook_white",
          friction_head_loss_m: 20,
          minor_head_loss_m: 2,
          total_head_loss_m: 22,
          elevation_change_m: 127,
          inlet_pressure_pa: 3_500_000,
          outlet_pressure_pa: 1_200_000,
          min_pressure_pa: 1_200_000,
          max_pressure_pa: 3_500_000,
          maop_margin_pa: 4_500_000,
          maop_pa: 8_000_000,
          start_chainage_m: 0,
          end_chainage_m: 132_000,
          flow_regime: "turbulent",
        },
        {
          segment_id: "L-002",
          label: "Tronçon Nord",
          flow_m3_s: 0.2,
          velocity_m_s: 1.55,
          reynolds: 125_000,
          friction_factor: 0.018,
          friction_model: "colebrook_white",
          friction_head_loss_m: 23,
          minor_head_loss_m: 0,
          total_head_loss_m: 23,
          elevation_change_m: 165,
          inlet_pressure_pa: 3_000_000,
          outlet_pressure_pa: 2_400_000,
          min_pressure_pa: 2_400_000,
          max_pressure_pa: 3_000_000,
          maop_margin_pa: null,
          maop_pa: null,
          start_chainage_m: 132_000,
          end_chainage_m: 350_000,
          flow_regime: "turbulent",
        },
      ],
      stations: [
        {
          station_id: "ST-01",
          name: "Station intermédiaire",
          chainage_m: 132_000,
          elevation_m: 145,
          in_service: true,
          bypassed: false,
          flow_m3_s: 0.2,
          suction_pressure_pa: 1_200_000,
          discharge_pressure_pa: 3_000_000,
          differential_pressure_pa: 1_800_000,
          head_m: 210,
          hydraulic_power_w: 150_000,
          absorbed_power_w: 180_000,
          efficiency: 0.78,
          active_pump_count: 1,
          pumps: [],
        },
      ],
      gravity_zones: [
        { start_chainage_m: 130_000, end_chainage_m: 132_000, length_m: 2_000, fill_ratio: null },
      ],
      assumptions: {
        fluid_state: {
          vapor_pressure_pa: 1_500_000,
          vapor_pressure_source: "laboratoire",
          extrapolated: false,
        },
      },
    },
  };

  await page.route(/\/api\/v1\/models\/model-1\/scenarios/, (route) =>
    respond(route, pageOf([scenario])),
  );
  await page.route(/\/api\/v1\/scenarios\/scenario-engineering-1\/calculations/, (route) =>
    respond(route, calculation),
  );
  await page.route(/\/api\/v1\/calculations\/calculation-engineering-1\/results/, (route) =>
    respond(route, engineeringResult),
  );

  await page.goto("/calcul");
  await page.getByRole("button", { name: "Exécuter HydroLiquid Core" }).click();

  await expect(page.getByRole("heading", { level: 2, name: "Diagnostics ingénieur" })).toBeVisible();
  await expect(page.getByText("Marge MAOP/MAWP minimale")).toBeVisible();
  await expect(page.getByText("Propriété produit · laboratoire")).toBeVisible();
  await expect(
    page.getByRole("img", {
      name: "Profil hydraulique, terrain, stations et zones signalées",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", {
      name: "Pression absolue, limites configurées, stations et zones suivant le chaînage",
    }),
  ).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exporter le profil hydraulique PNG" }).click();
  expect((await download).suggestedFilename()).toMatch(/calcul-calculat-profil-hydraulique\.png/);

  const dimensions = await page.locator(".chart-export").evaluateAll((charts) =>
    charts.map((chart) => ({ clientWidth: chart.clientWidth, scrollWidth: chart.scrollWidth })),
  );
  expect(dimensions.every(({ clientWidth, scrollWidth }) => scrollWidth <= clientWidth)).toBe(true);
});
