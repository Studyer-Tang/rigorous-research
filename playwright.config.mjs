import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";

const python =
  process.platform === "win32"
    ? `"${resolve(".venv/Scripts/python.exe")}"`
    : "python";

export default defineConfig({
  testDir: "tests/browser",
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `${python} -m http.server 4173 --bind 127.0.0.1 --directory build/papertrail-e2e`,
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
