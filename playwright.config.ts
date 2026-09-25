import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  // The backend guards context synthesis behind a bounded concurrency queue
  // (max_concurrent=1), so specs run serially against it.
  workers: 1,
  use: {
    browserName: "chromium",
    launchOptions: {
      executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
      args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    },
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npx vite preview --port 4173 --host 127.0.0.1",
    port: 4173,
    reuseExistingServer: true,
    timeout: 10000,
  },
});
