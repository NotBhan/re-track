/**
 * Fixtures for CLI lifecycle tests: a fake backend directory whose interpreter
 * is a Node script, plus marker helpers for asserting what actually ran.
 */

import { chmodSync, copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

export function createFakeBackend({ mode = "ok" } = {}) {
  const root = mkdtempSync(path.join(os.tmpdir(), "retrack-cli-fake-"));
  const backendDir = path.join(root, "backend");
  mkdirSync(path.join(backendDir, "app"), { recursive: true });
  writeFileSync(path.join(backendDir, "app", "server.py"), "# placeholder uvicorn target for CLI lifecycle tests\n");
  const binDir = path.join(backendDir, ".venv", "bin");
  mkdirSync(binDir, { recursive: true });
  const python = path.join(binDir, "python");
  copyFileSync(path.join(here, "fake-backend-python.mjs"), python);
  chmodSync(python, 0o755);
  return {
    root,
    backendDir,
    python,
    mode,
    logPath: path.join(root, "retrack-backend.log"),
    markers: path.join(root, "markers"),
  };
}

/** Environment pointing the CLI at the fake backend and isolating its log file. */
export function fakeBackendEnv(fake, overrides = {}) {
  return {
    RETRACK_BACKEND_DIR: fake.backendDir,
    RETRACK_STUB_MODE: fake.mode,
    RETRACK_STUB_MARKERS: fake.markers,
    TMPDIR: fake.root,
    ...overrides,
  };
}

export function markerCount(fake, name) {
  const file = path.join(fake.markers, name);
  if (!existsSync(file)) return 0;
  return readFileSync(file, "utf8").split("\n").filter(Boolean).length;
}

export function readMarkerJson(fake, name) {
  return JSON.parse(readFileSync(path.join(fake.markers, name), "utf8"));
}

export function pidAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

export async function waitForPidGone(pid, { timeoutMs = 6_000, intervalMs = 50 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!pidAlive(pid)) return true;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return !pidAlive(pid);
}

export function freePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}
