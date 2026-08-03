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
  {
    id: "node-source",
    model_version_id: model.id,
    code: "SRC-01",
    name: "Dépôt Abidjan",
    kind: "source",
    elevation_m: 18,
    latitude: 5.32,
    longitude: -4.02,
    status: "available",
    payload: {},
    created_at: now,
    updated_at: now,
  },
  {
    id: "node-station",
    model_version_id: model.id,
    code: "ST-01",
    name: "Station intermédiaire",
    kind: "station",
    elevation_m: 145,
    latitude: 6.3,
    longitude: -4.7,
    status: "available",
    payload: {},
    created_at: now,
    updated_at: now,
  },
  {
    id: "node-terminal",
    model_version_id: model.id,
    code: "TRM-01",
    name: "Terminal Bouaké",
    kind: "terminal",
    elevation_m: 310,
    latitude: 7.69,
    longitude: -5.03,
    status: "available",
    payload: {},
    created_at: now,
    updated_at: now,
  },
];

const edges = [
  {
    id: "edge-1",
    model_version_id: model.id,
    from_node_id: "node-source",
    to_node_id: "node-station",
    material_catalog_item_id: null,
    code: "L-001",
    name: "Tronçon Sud",
    sequence: 1,
    length_m: 132_000,
    inner_diameter_m: 0.4064,
    roughness_m: 0.000045,
    mawp_pa: 8_000_000,
    status: "available",
    profile_payload: [],
    fittings_payload: [],
    payload: {},
    created_at: now,
    updated_at: now,
  },
  {
    id: "edge-2",
    model_version_id: model.id,
    from_node_id: "node-station",
    to_node_id: "node-terminal",
    material_catalog_item_id: null,
    code: "L-002",
    name: "Tronçon Nord",
    sequence: 2,
    length_m: 218_000,
    inner_diameter_m: 0.4064,
    roughness_m: 0.000045,
    mawp_pa: 8_000_000,
    status: "available",
    profile_payload: [],
    fittings_payload: [],
    payload: {},
    created_at: now,
    updated_at: now,
  },
];

function pageOf<T>(items: T[]) {
  return { items, total: items.length, limit: 2000, offset: 0 };
}

async function json(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApiMock(page: Page): Promise<void> {
  await page.route("https://demotiles.maplibre.org/style.json", async (route) => {
    await json(route, { version: 8, name: "PETROLE test style", sources: {}, layers: [] });
  });

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api/v1", "");

    if (path === "/auth/status") {
      await json(route, { authentication_required: false, initialized: true });
      return;
    }
    if (path === "/health") {
      await json(route, {
        status: "ok",
        service: "hydro-api",
        version: "0.1.0-test",
        environment: "test",
      });
      return;
    }
    if (path === "/health/ready") {
      await json(route, {
        status: "ready",
        database: "ready",
        object_storage: "ready",
      });
      return;
    }
    if (path === "/organizations") {
      await json(route, pageOf([organization]));
      return;
    }
    if (path === "/projects") {
      await json(route, pageOf([project]));
      return;
    }
    if (path === `/projects/${project.id}/models`) {
      await json(route, pageOf([model]));
      return;
    }
    if (path === `/models/${model.id}/nodes`) {
      await json(route, pageOf(nodes));
      return;
    }
    if (path === `/models/${model.id}/edges`) {
      await json(route, pageOf(edges));
      return;
    }
    if (request.method() === "GET") {
      await json(route, pageOf([]));
      return;
    }
    await json(route, {}, 200);
  });
}

test.beforeEach(async ({ page }) => {
  await installApiMock(page);
});

test("affiche le tableau de bord et conserve le thème sombre", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  await expect(page.getByText("Pipeline Abidjan–Bouaké")).toBeVisible();
  await expect(page.locator("canvas")).toBeVisible();

  await page.getByRole("button", { name: "Activer le mode sombre" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);

  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("ouvre la palette de commandes et navigue avec TanStack Router", async ({ page }) => {
  await page.goto("/");

  await page.keyboard.press("Control+K");
  const dialog = page.getByRole("dialog", { name: "Recherche globale" });
  await expect(dialog).toBeVisible();

  await dialog.getByPlaceholder("Rechercher une page ou une fonction…").fill("rapports");
  await dialog.getByRole("button", { name: /Rapports/ }).click();

  await expect(page).toHaveURL(/\/rapports$/);
  await expect(page.getByRole("heading", { level: 1, name: "Rapports" })).toBeVisible();
});

test("affiche le réseau avec React Flow et MapLibre", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Visualiser le réseau" }).click();

  await expect(page).toHaveURL(/\/reseau$/);
  await expect(page.getByRole("heading", { level: 2, name: "Schéma technologique du réseau" })).toBeVisible();
  await expect(page.locator(".react-flow__node")).toHaveCount(3);
  await expect(page.locator(".react-flow__edge")).toHaveCount(2);
  await expect(page.getByText("350 km")).toBeVisible();

  await page.getByRole("button", { name: "Carte" }).click();
  await expect(page.getByRole("heading", { level: 2, name: "Carte du réseau" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Carte géographique du pipeline" })).toBeVisible();
  await expect(page.getByText("3", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Schéma" }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(3);
});

test("ouvre et ferme le menu mobile", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "Scénario réservé à la vue mobile.");

  await page.goto("/");
  await page.getByRole("button", { name: "Ouvrir la navigation" }).click();
  await expect(page.locator("aside.sidebar")).toHaveClass(/is-mobile-open/);

  await page.getByRole("link", { name: "Rapports" }).click();
  await expect(page).toHaveURL(/\/rapports$/);
  await expect(page.locator("aside.sidebar")).not.toHaveClass(/is-mobile-open/);
});

test("réduit et restaure la barre latérale sur bureau", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "bureau", "Scénario réservé à la vue bureau.");

  await page.goto("/");
  await page.getByRole("button", { name: "Réduire la barre latérale" }).click();
  await expect(page.locator(".app-shell")).toHaveClass(/sidebar-collapsed/);

  await page.getByRole("button", { name: "Déployer la barre latérale" }).click();
  await expect(page.locator(".app-shell")).not.toHaveClass(/sidebar-collapsed/);
});
