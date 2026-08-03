import { expect, test, type Page, type Route } from "@playwright/test";

const ROUTES = [
  ["/", "Tableau de bord"],
  ["/projets", "Projets et versions"],
  ["/modelisation", "Modélisation"],
  ["/reseau", "Visualisation du réseau"],
  ["/bibliotheques", "Bibliothèques techniques"],
  ["/calcul", "Calcul hydraulique"],
  ["/stockage", "Stockage et transferts"],
  ["/decision", "Comparaison et décision"],
  ["/donnees", "Données et imports"],
  ["/rapports", "Rapports"],
  ["/administration", "Administration"],
] as const;

function pageOf(items: unknown[] = []) {
  return { items, total: items.length, limit: 2000, offset: 0 };
}

async function respond(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installPlatformMock(page: Page): Promise<void> {
  await page.route("https://demotiles.maplibre.org/style.json", (route) =>
    respond(route, { version: 8, name: "PETROLE test style", sources: {}, layers: [] }),
  );

  await page.route(/\/api\/v1\//, async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");

    if (path === "/auth/status") {
      await respond(route, { authentication_required: false, initialized: true });
      return;
    }
    if (path === "/health") {
      await respond(route, {
        status: "ok",
        service: "hydro-api",
        version: "0.1.0-test",
        environment: "test",
      });
      return;
    }
    if (path === "/health/ready") {
      await respond(route, {
        status: "ready",
        database: "ready",
        object_storage: "ready",
      });
      return;
    }

    await respond(route, route.request().method() === "GET" ? pageOf() : {});
  });
}

test.beforeEach(async ({ page }) => {
  await installPlatformMock(page);
});

for (const [path, title] of ROUTES) {
  test(`${title} se charge sans erreur ni débordement`, async ({ page }) => {
    const browserErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") {
        browserErrors.push(message.text());
      }
    });
    page.on("pageerror", (error) => browserErrors.push(error.message));

    await page.goto(path, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
    await page.waitForTimeout(150);

    expect(await page.locator('[role="alert"]').count()).toBe(0);
    expect(browserErrors).toEqual([]);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

test("la navigation interne change de page sans rechargement externe", async ({ page }, testInfo) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();

  if (testInfo.project.name === "mobile") {
    await page.getByRole("button", { name: "Ouvrir la navigation" }).click();
  }

  await page.getByRole("link", { name: "Modélisation" }).click();
  await expect(page).toHaveURL(/\/modelisation$/);
  await expect(page.getByRole("heading", { level: 1, name: "Modélisation" })).toBeVisible();
});
