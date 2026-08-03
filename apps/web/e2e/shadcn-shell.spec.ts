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
    };

    if (path in fixtures) {
      await respond(route, fixtures[path]);
      return;
    }
    await respond(route, request.method() === "GET" ? pageOf([]) : {});
  });
}

test.beforeEach(async ({ page }) => {
  await installApiMock(page);
});

test("affiche le tableau de bord et conserve le thème sombre", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  await expect(page.getByText("Pipeline Abidjan–Bouaké")).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();

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
  await page.getByRole("button", { name: "Ouvrir la navigation" }).click();
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
