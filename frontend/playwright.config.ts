import { defineConfig } from "@playwright/test";

// End-to-end smoke tests against the local stack: backend on :8000 (with its database),
// frontend on :3100. Uses the installed Google Chrome, so no browser download is needed.
//   pnpm e2e
export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3100",
    channel: "chrome",
    headless: true,
    locale: "uz-UZ",
    viewport: { width: 1280, height: 900 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "pnpm dev --port 3100",
    url: "http://localhost:3100",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
