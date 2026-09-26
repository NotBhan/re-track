#!/usr/bin/env node
/**
 * Test double for `backend/.venv/bin/python`, used by the TUI lifecycle suites.
 *
 * It is a real child process that reproduces the observable backend contract:
 * uvicorn-style argv, a `/health` endpoint, graceful SIGTERM, and the failure
 * modes below. Behaviour is recorded under RETRACK_STUB_MARKERS so tests can
 * assert the spawn contract, parent-watchdog wiring and shutdown semantics
 * without mocking child_process.
 *
 * Modes (RETRACK_STUB_MODE):
 *   ok         serve /health and exit on SIGTERM (records the signal)
 *   exit       fail immediately the way a broken import would
 *   hang       stay alive without listening (readiness-timeout case)
 *   stubborn   listen, then ignore SIGTERM to force the bounded SIGKILL fallback
 *   slowlisten bind only after RETRACK_STUB_LISTEN_DELAY_MS (port-race case)
 */

import { appendFileSync, mkdirSync, writeFileSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";

const markers = process.env.RETRACK_STUB_MARKERS ?? "";
const mode = process.env.RETRACK_STUB_MODE ?? "ok";
const portIndex = process.argv.indexOf("--port");
const port = portIndex >= 0 ? Number(process.argv[portIndex + 1]) : 0;

function record(name, value) {
  if (!markers) return;
  mkdirSync(markers, { recursive: true });
  appendFileSync(path.join(markers, name), `${value}\n`);
}

function recordJson(name, value) {
  if (!markers) return;
  mkdirSync(markers, { recursive: true });
  writeFileSync(path.join(markers, name), JSON.stringify(value, null, 2));
}

recordJson("argv.json", process.argv.slice(2));
recordJson("env.json", {
  RETRACK_PARENT_PID: process.env.RETRACK_PARENT_PID ?? null,
  PYTHONPATH: process.env.PYTHONPATH ?? null,
  LLM_MODEL: process.env.LLM_MODEL ?? null,
  VECTOR_DB_PROVIDER: process.env.VECTOR_DB_PROVIDER ?? null,
  GRAPH_DB_PROVIDER: process.env.GRAPH_DB_PROVIDER ?? null,
  EMBEDDING_DIMENSIONS: process.env.EMBEDDING_DIMENSIONS ?? null,
  cwd: process.cwd(),
});
recordJson("pids.json", { self: process.pid });

if (mode === "exit") {
  process.stderr.write("simulated startup failure: import error in app.server\n");
  process.exit(3);
}

if (mode === "hang") {
  setInterval(() => {}, 1_000);
} else {
  const server = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");
    const send = (payload) => res.end(JSON.stringify(payload));
    if (req.url.startsWith("/health/detailed")) return send({ status: "ok", storage_paths: {} });
    if (req.url.startsWith("/health")) {
      return send({
        status: "ok",
        version: "0.1.0",
        provider_identity: "lmstudio",
        provider_reachable: true,
        concurrency_available_slots: 1,
        concurrency_queue_depth: 0,
      });
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

  server.on("error", (error) => {
    process.stderr.write(`fake backend bind failed: ${error.code}\n`);
    process.exit(4);
  });

  const delayMs = Number(process.env.RETRACK_STUB_LISTEN_DELAY_MS ?? 0);
  const listen = () => {
    server.listen(port, "127.0.0.1", () => {
      record("starts.log", "started");
      // Represents the backend's own worker tree: cleanup must reach descendants.
      const grandchild = spawn(process.execPath, ["-e", "setInterval(() => {}, 1000)"], {
        stdio: "ignore",
      });
      recordJson("grandchild.json", { pid: grandchild.pid });
    });
  };
  if (delayMs > 0) setTimeout(listen, delayMs);
  else listen();
}

if (mode === "stubborn") {
  // Holds the process group open until the bounded SIGKILL fallback fires.
  process.on("SIGTERM", () => {});
} else {
  process.on("SIGTERM", () => {
    record("signals.log", "SIGTERM");
    // A short delay keeps the graceful path observable as a real shutdown.
    setTimeout(() => process.exit(0), 30);
  });
}
