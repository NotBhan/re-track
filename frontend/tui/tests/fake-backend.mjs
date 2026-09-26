/**
 * Lifecycle test fixtures: a throwaway backend directory whose `.venv/bin/python`
 * is a real child process (fake-backend-python.mjs), plus small helpers for
 * ephemeral ports, child liveness and marker files.
 *
 * The TUI lifecycle resolves exactly these paths, so tests exercise the real
 * spawn → readiness → ownership → shutdown path instead of mocking it.
 */

import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

/** Materialize a fake backend tree: backend/app/server.py + backend/.venv/bin/python. */
export function createFakeBackend({ mode = "ok" } = {}) {
  const root = mkdtempSync(path.join(os.tmpdir(), "retrack-fake-backend-"));
  const backendDir = path.join(root, "backend");
  mkdirSync(path.join(backendDir, "app"), { recursive: true });
  writeFileSync(
    path.join(backendDir, "app", "server.py"),
    "# placeholder uvicorn target for lifecycle tests\n"
  );
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

/** Environment for a run whose backend directory is the given fake. */
export function fakeBackendEnv(fake, overrides = {}) {
  return {
    RETRACK_BACKEND_DIR: fake.backendDir,
    RETRACK_STUB_MODE: fake.mode,
    RETRACK_STUB_MARKERS: fake.markers,
    ...overrides,
  };
}

/** Minimal backend HTTP contract for the "already running" cases. */
export function startStubBackend() {
  const requests = [];
  const server = createServer((req, res) => {
    requests.push(req.url);
    res.setHeader("Content-Type", "application/json");
    const send = (payload) => res.end(JSON.stringify(payload));
    if (req.url.startsWith("/health/detailed")) return send({ status: "ok", storage_paths: {} });
    if (req.url.startsWith("/health")) {
      return send({ status: "ok", version: "0.1.0", provider_identity: "lmstudio", provider_reachable: true });
    }
    if (req.url.startsWith("/status")) return send({ status: "ok", llm_provider: "lmstudio" });
    if (req.url.startsWith("/provider/status")) {
      return send({ success: true, provider: "lmstudio", is_reachable: true, health_state: "healthy" });
    }
    if (req.url.startsWith("/repos/") && req.url.endsWith("/prompts")) {
      return send({ success: true, prompts: [], source: "heuristic" });
    }
    if (req.url.startsWith("/repos")) return send({ success: true, repositories: [], total_count: 0 });
    if (req.url.startsWith("/packages")) return send({ success: true, packages: [], total_count: 0 });
    if (req.url.startsWith("/memory/stats")) {
      return send({ success: true, dataset_count: 0, total_size_display: "0 B" });
    }
    if (req.url.startsWith("/logs/recent")) return send({ status: "ok", count: 0, logs: [] });
    return send({ ok: true });
  });
  return new Promise((resolve, reject) => {
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({
        server,
        requests,
        baseUrl: `http://127.0.0.1:${port}`,
        close: () => new Promise((done) => server.close(done)),
      });
    });
  });
}

/** Reserve an ephemeral port, then release it for the fake backend to bind. */
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

export function pidAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

export async function waitFor(predicate, { timeoutMs = 5_000, intervalMs = 50 } = {}) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const value = await predicate();
    if (value) return value;
    if (Date.now() >= deadline) return null;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export function readText(file) {
  try {
    return readFileSync(file, "utf8");
  } catch {
    return null;
  }
}

export function readJson(file) {
  const text = readText(file);
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export function markerCount(fake, name) {
  const text = readText(path.join(fake.markers, name));
  return text ? text.split("\n").filter(Boolean).length : 0;
}

export function waitForPidGone(pid, timeoutMs = 4_000) {
  return waitFor(() => !pidAlive(pid), { timeoutMs, intervalMs: 50 });
}
