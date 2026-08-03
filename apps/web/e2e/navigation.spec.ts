import { expect, test } from "@playwright/test";

const ROUTES = [
  ["/", "Vue d'ensemble"],
  ["/projets", "Projets et versions"],
  ["/modelisation", "Modélisation"],
  ["/bibliotheques", "Bibliothèques techniques"],
  ["/calcul", "Calcul hydraulique"],
  ["/stockage", "Stockage et transferts"],
  ["/decision", "Comparaison et décision"],
  ["/donnees", "Données et imports"],
  ["/rapports", "Rapports"],
  ["/administration", "Administration"],
] as const;

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
    await page.waitForTimeout(350);

    expect(await page.locator('[role="alert"]').count()).toBe(0);
    expect(browserErrors).toEqual([]);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

test("la navigation interne change de page sans rechargement externe", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.locator('a[href="/modelisation"]').click();
  await expect(page).toHaveURL(/\/modelisation$/);
  await expect(page.getByRole("heading", { level: 1, name: "Modélisation" })).toBeVisible();
});
