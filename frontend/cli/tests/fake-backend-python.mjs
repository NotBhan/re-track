#!/usr/bin/env node
/**
 * Stand-in for the backend interpreter in CLI lifecycle tests.
 *
 * Copied into a fake `backend/.venv/bin/python` by fake-backend.mjs. It ignores
 * the uvicorn argv except `--port`, records its own pid, and behaves according
 * to RETRACK_STUB_MODE:
 *   ok    — serve the minimum HTTP contract and stay alive
 *   exit  — print a failure and exit non-zero before readiness
 *   hang  — stay alive without ever answering /health
 */

import { appendFileSync, mkdirSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import path from "node:path";

const mode = process.env.RETRACK_STUB_MODE ?? "ok";
const markers = process.env.RETRACK_STUB_MARKERS;
const argv = process.argv.slice(2);
const portArg = argv.indexOf("--port");
const port = portArg === -1 ? 0 : Number(argv[portArg + 1]);

if (markers) {
  mkdirSync(markers, { recursive: true });
  appendFileSync(path.join(markers, "starts.log"), "start\n");
  writeFileSync(path.join(markers, "pids.json"), JSON.stringify({ self: process.pid, port }));
}

if (mode === "exit") {
  process.stderr.write("simulated startup failure\n");
  process.exit(3);
}

if (mode === "hang") {
  // Alive but never ready: shutdown must reap it.
  setInterval(() => {}, 60_000);
} else {
  const server = createServer((request, response) => {
    response.setHeader("Content-Type", "application/json");
    if (request.url.startsWith("/health")) return response.end(JSON.stringify({ status: "ok", provider_identity: "stub" }));
    if (request.url.startsWith("/status")) return response.end(JSON.stringify({ status: "ok" }));
    if (request.url.startsWith("/provider/status")) {
      return response.end(JSON.stringify({ success: true, provider: "stub", base_url: `http://127.0.0.1:${port}/v1`, is_reachable: true, health_state: "healthy" }));
    }
    return response.end(JSON.stringify({ ok: true }));
  });
  server.listen(port, "127.0.0.1");
}
