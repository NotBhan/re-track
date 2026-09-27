import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { startStubBackend } from "./stub-backend.mjs";
import { createFakeBackend, fakeBackendEnv, freePort, markerCount, readMarkerJson, waitForPidGone } from "./fake-backend.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const CLI = path.resolve(here, "..", "retrack.mjs");

function runCli(args, { env = {}, timeoutMs = 40_000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [CLI, ...args], {
      env: { ...process.env, ...env },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString("utf8");
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString("utf8");
    });
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`cli did not exit: ${args.join(" ")}\n${stdout}${stderr}`));
    }, timeoutMs);
    child.on("error", reject);
    child.on("exit", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
  });
}

describe("cli lifecycle: real processes", () => {
  it("starts a backend when none is reachable and terminates only that tree", { timeout: 40_000 }, async () => {
    const port = await freePort();
    const fake = createFakeBackend();
    const result = await runCli(["health"], {
      env: fakeBackendEnv(fake, { RETRACK_BACKEND_URL: `http://127.0.0.1:${port}` }),
    });

    assert.equal(result.code, 0, result.stderr);
    assert.match(result.stdout, /Backend\s+ok/);
    assert.match(result.stderr, /starting backend/, "the start is reported on stderr, never stdout");
    assert.equal(markerCount(fake, "starts.log"), 1, "the CLI started the backend it needed");

    const { self } = readMarkerJson(fake, "pids.json");
    assert.equal(await waitForPidGone(self), true, "the backend this invocation started is not left behind");
  });

  it("attaches to a running backend, spawns nothing and leaves it alive", { timeout: 40_000 }, async () => {
    const stub = await startStubBackend();
    const fake = createFakeBackend();
    try {
      const result = await runCli(["health"], {
        env: fakeBackendEnv(fake, { RETRACK_BACKEND_URL: stub.baseUrl }),
      });
      assert.equal(result.code, 0, result.stderr);
      assert.match(result.stdout, /Backend\s+ok/);
      assert.equal(markerCount(fake, "starts.log"), 0, "a reachable backend is never replaced");
      assert.equal(result.stderr.includes("starting backend"), false);

      const health = await (await fetch(`${stub.baseUrl}/health`)).json();
      assert.equal(health.status, "ok", "the pre-existing backend is still running");
    } finally {
      await stub.close();
    }
  });

  it("reports a startup failure with the log tail, exits 1 and leaves no orphan", { timeout: 40_000 }, async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "exit" });
    const result = await runCli(["health"], {
      env: fakeBackendEnv(fake, { RETRACK_BACKEND_URL: `http://127.0.0.1:${port}` }),
    });

    assert.equal(result.code, 1);
    assert.equal(result.stdout, "", "nothing is printed to stdout on a failed startup");
    assert.match(result.stderr, /exited before readiness/);
    assert.match(result.stderr, /simulated startup failure/, "the backend's own failure is reported");

    const { self } = readMarkerJson(fake, "pids.json");
    assert.equal(await waitForPidGone(self), true, "the failed child was reaped");
  });

  it("never spawns under --no-start", { timeout: 40_000 }, async () => {
    const port = await freePort();
    const fake = createFakeBackend();
    const result = await runCli(["health", "--no-start"], {
      env: fakeBackendEnv(fake, { RETRACK_BACKEND_URL: `http://127.0.0.1:${port}` }),
    });

    assert.equal(result.code, 1);
    assert.match(result.stderr, /backend unavailable .*--no-start/);
    assert.equal(markerCount(fake, "starts.log"), 0);
  });
});
