import { defineConfig, devices } from "@playwright/test";

const outputDir = process.env.PLAYWRIGHT_OUTPUT_DIR ?? "test-results";
const htmlReportDir = process.env.PLAYWRIGHT_HTML_REPORT_DIR ?? "playwright-report";

export default defineConfig({
  testDir: "./e2e",
  outputDir,
  timeout: 15_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  workers: process.env.CI ? 1 : undefined,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [["line"], ["html", { outputFolder: htmlReportDir, open: "never" }]]
    : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:4173",
    channel: process.env.PLAYWRIGHT_USE_BUNDLED_CHROMIUM === "true" ? undefined : "chrome",
    headless: true,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "bureau",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"] },
    },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: "npm run dev -- --host 127.0.0.1 --port 4173",
        url: "http://127.0.0.1:4173",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
