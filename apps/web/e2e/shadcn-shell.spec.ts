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
const site = {
  id: "site-1",
  organization_id: organization.id,
  name: "Station pilote",
  code: "ST-PILOTE",
  country_code: "CI",
  latitude: null,
  longitude: null,
  status: "active",
  created_at: now,
  updated_at: now,
};
const measurementTag = {
  id: "tag-pt-101",
  organization_id: organization.id,
  site_id: site.id,
  asset_instance_id: null,
  external_name: "PT-101",
  name: "Pression de refoulement",
  measurement_type: "pressure",
  dimension: "pressure",
  source_unit: "bar",
  si_unit: "Pa",
  source: "fichier-pilote",
  status: "active",
  metadata: { absolute_pressure: true },
  created_at: now,
  updated_at: now,
};
const seriesAnalysis = {
  tag: measurementTag,
  processing_version: "pilot-v1-a3",
  requested_start_timestamp: null,
  requested_end_timestamp: null,
  start_timestamp: "2026-08-03T09:00:00Z",
  end_timestamp: "2026-08-03T09:03:00Z",
  included_qualities: ["good", "uncertain"],
  quality_counts: { good: 2, uncertain: 1, bad: 1 },
  visible_quality_counts: { good: 2, uncertain: 1 },
  candidate_sample_count: 4,
  excluded_sample_count: 1,
  statistics: {
    sample_count: 3,
    minimum_value_si: 1_000_000,
    maximum_value_si: 1_020_000,
    mean_value_si: 1_010_000,
    stddev_value_si: 8_164.966,
  },
  duplicate_timestamp_count: 1,
  out_of_order_count: 0,
  gap_count: 1,
  observed_interval_seconds: 60,
  reference_interval_seconds: 60,
  gap_factor: 1.5,
  outlier_method: "none",
  outlier_threshold: null,
  outlier_count: 0,
  issues: [
    {
      code: "DQ-008",
      severity: "warning",
      count: 1,
      message: "Les mesures bad sont exclues par le filtre par défaut, sans suppression.",
    },
    {
      code: "TS-GAP",
      severity: "warning",
      count: 1,
      message: "Un trou est signalé sans supprimer les points.",
    },
  ],
  items: [
    {
      id: "normalized-1",
      raw_sample_id: "raw-1",
      time_series_import_id: "import-1",
      dataset_id: "dataset-1",
      dataset_row_id: "row-1",
      source_timestamp: "2026-08-03T09:00:00Z",
      ingest_timestamp: now,
      source_value: "10.0",
      source_unit: "bar",
      timestamp: "2026-08-03T09:00:00Z",
      value_si: 1_000_000,
      si_unit: "Pa",
      quality: "good",
      sequence_number: 1,
      processing_version: "pilot-v1-a3",
      duplicate: false,
      gap_after: false,
      gap_after_seconds: null,
      outlier: false,
      outlier_score: null,
    },
    {
      id: "normalized-2",
      raw_sample_id: "raw-2",
      time_series_import_id: "import-1",
      dataset_id: "dataset-1",
      dataset_row_id: "row-2",
      source_timestamp: "2026-08-03T09:01:00Z",
      ingest_timestamp: now,
      source_value: "10.1",
      source_unit: "bar",
      timestamp: "2026-08-03T09:01:00Z",
      value_si: 1_010_000,
      si_unit: "Pa",
      quality: "uncertain",
      sequence_number: 2,
      processing_version: "pilot-v1-a3",
      duplicate: true,
      gap_after: true,
      gap_after_seconds: 120,
      outlier: false,
      outlier_score: null,
    },
    {
      id: "normalized-3",
      raw_sample_id: "raw-3",
      time_series_import_id: "import-1",
      dataset_id: "dataset-1",
      dataset_row_id: "row-3",
      source_timestamp: "2026-08-03T09:03:00Z",
      ingest_timestamp: now,
      source_value: "10.2",
      source_unit: "bar",
      timestamp: "2026-08-03T09:03:00Z",
      value_si: 1_020_000,
      si_unit: "Pa",
      quality: "good",
      sequence_number: 3,
      processing_version: "pilot-v1-a3",
      duplicate: false,
      gap_after: false,
      gap_after_seconds: null,
      outlier: false,
      outlier_score: null,
    },
  ],
  total: 3,
  limit: 500,
  offset: 0,
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
const scenario = {
  id: "scenario-1",
  model_version_id: model.id,
  parent_id: null,
  name: "Régime nominal stable",
  description: null,
  payload: {},
  created_at: now,
  updated_at: now,
};
const calculation = {
  id: "calculation-1",
  job_id: null,
  scenario_id: scenario.id,
  engine: "long_distance_liquid",
  engine_version: "long_distance_liquid-0.1.0",
  status: "SIM_CONVERGED",
  phase: "completed",
  progress_percent: 100,
  input_hash: "sha256:calculation-input",
  approval_status: "approved",
  approval_comment: "Référence stationnaire.",
  approved_at: now,
  created_at: now,
  started_at: now,
  finished_at: now,
};
const measurementMapping = {
  id: "mapping-1",
  organization_id: organization.id,
  project_id: project.id,
  model_version_id: model.id,
  tag_id: measurementTag.id,
  version_number: 1,
  target_type: "node",
  target_id: "node-terminal",
  metric: "pressure_pa",
  dimension: "pressure",
  si_unit: "Pa",
  status: "approved",
  source_ref: "Schéma d'instrumentation de démonstration.",
  created_by: null,
  approved_by: null,
  approved_at: now,
  created_at: now,
  updated_at: now,
};
const measurementComparison = {
  id: "measurement-comparison-1",
  organization_id: organization.id,
  project_id: project.id,
  model_version_id: model.id,
  mapping_id: measurementMapping.id,
  calculation_id: calculation.id,
  tag_id: measurementTag.id,
  processing_version: "pilot-v1-a3",
  start_timestamp: "2026-08-03T09:00:00Z",
  end_timestamp: "2026-08-03T09:03:00Z",
  included_qualities: ["good", "uncertain", "substituted", "estimated"],
  input_hash: "sha256:comparison-input",
  calculation_input_hash: calculation.input_hash,
  engine: calculation.engine,
  engine_version: calculation.engine_version,
  simulated_value_si: 1_005_000,
  si_unit: "Pa",
  status: "completed",
  kpis: {
    n_compared: 3,
    bias_si: 5_000,
    mae_si: 8_333.333,
    rmse_si: 9_128.709,
    min_residual_si: -5_000,
    max_residual_si: 15_000,
  },
  exclusions: {
    n_candidates: 4,
    n_excluded_quality: 1,
    n_excluded_outlier: 0,
    quality_counts: { good: 2, uncertain: 1, bad: 1 },
    exclusion_counts: { "quality:bad": 1 },
    duplicate_timestamp_count: 1,
  },
  mapping: measurementMapping,
  created_by: null,
  created_at: now,
};
const measurementResiduals = seriesAnalysis.items.map((point) => ({
  id: "residual-" + point.id,
  comparison_id: measurementComparison.id,
  normalized_sample_id: point.id,
  raw_sample_id: point.raw_sample_id,
  dataset_id: point.dataset_id,
  dataset_row_id: point.dataset_row_id,
  timestamp: point.timestamp,
  measured_value_si: point.value_si,
  simulated_value_si: measurementComparison.simulated_value_si,
  residual_si: point.value_si - measurementComparison.simulated_value_si,
  quality: point.quality,
  included_in_kpi: point.quality !== "bad",
  exclusion_reason: point.quality === "bad" ? "quality:bad" : null,
  source_timestamp: point.source_timestamp,
  ingest_timestamp: point.ingest_timestamp,
  source_value: point.source_value,
  source_unit: point.source_unit,
  processing_version: point.processing_version,
}));
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
      "/sites": pageOf([site]),
      "/projects": pageOf([project]),
      "/measurement-tags": pageOf([measurementTag]),
      [`/measurement-tags/${measurementTag.id}/processing-versions`]: [
        {
          processing_version: "pilot-v1-a3",
          sample_count: 4,
          start_timestamp: seriesAnalysis.start_timestamp,
          end_timestamp: seriesAnalysis.end_timestamp,
        },
      ],
      [`/measurement-tags/${measurementTag.id}/series-analysis`]: seriesAnalysis,
      [`/projects/${project.id}/models`]: pageOf([model]),
      [`/models/${model.id}/scenarios`]: pageOf([scenario]),
      [`/scenarios/${scenario.id}/calculations`]: pageOf([calculation]),
      "/measurement-model-mappings": pageOf([measurementMapping]),
      "/measurement-comparisons": measurementComparison,
      [`/measurement-comparisons/${measurementComparison.id}/residuals`]: pageOf(measurementResiduals),
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

test("explore une série SI avec diagnostics et lignage sans étirer la page", async ({ page }) => {
  await page.goto("/donnees");
  await expect(page.getByRole("heading", { level: 1, name: "Données et imports" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "4. Séries temporelles et qualité" })).toBeVisible();
  await expect(page.getByRole("img", { name: /Série temporelle en unité SI/ })).toBeVisible();
  await expect(page.getByText("TS-GAP")).toBeVisible();
  await expect(page.getByText("Doublons")).toBeVisible();

  const table = page.locator(".table-wrap").filter({ has: page.getByText("Ligne source") }).last();
  await expect(table).toHaveCSS("overflow-y", "auto");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});

test("compare une fenêtre stable au calcul et affiche les résidus sans calibration", async ({ page }) => {
  await page.goto("/donnees");
  await expect(
    page.getByRole("heading", { level: 2, name: "5. Comparaison mesures ↔ modèle" }),
  ).toBeVisible();
  await expect(page.getByText("Ce n'est pas une calibration.")).toBeVisible();

  await page.getByLabel("Début de comparaison UTC").fill("2026-08-03T09:00");
  await page.getByLabel("Fin de comparaison UTC").fill("2026-08-03T09:03");
  await page.getByRole("button", { name: "Calculer les résidus" }).click();

  await expect(page.getByText("Comparaison stationnaire terminée")).toBeVisible();
  await expect(page.getByText("RMSE")).toBeVisible();
  await expect(page.getByRole("img", { name: "Mesures SI et référence de simulation stationnaire" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Résidus signés, mesure moins simulation" })).toBeVisible();
  const residualTable = page.locator(".table-wrap").filter({ has: page.getByText("Résidu signé") }).last();
  await expect(residualTable).toHaveCSS("overflow-y", "auto");
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
