/**
 * Lifecycle module suite: discovery, spawn, readiness, ownership and shutdown.
 *
 * These tests spawn real child processes — a fake backend whose `python` is a
 * Node HTTP server — so the spawn contract, readiness polling, process-group
 * cleanup and the attach-only rule are verified against real process state.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";

import {
  BackendStartupError,
  backendLogPath,
  ensureBackend,
  isLoopbackBaseUrl,
  resolveBackendDir,
  resolveBaseUrl,
  resolvePython,
} from "../backend-lifecycle.mjs";
import {
  createFakeBackend,
  fakeBackendEnv,
  freePort,
  markerCount,
  pidAlive,
  readJson,
  readText,
  startStubBackend,
  waitFor,
  waitForPidGone,
} from "./fake-backend.mjs";

const baseUrlFor = (port) => `http://127.0.0.1:${port}`;

describe("lifecycle: configuration", () => {
  it("normalizes the configured base URL", () => {
    assert.equal(resolveBaseUrl(undefined), "http://127.0.0.1:8765");
    assert.equal(resolveBaseUrl(""), "http://127.0.0.1:8765");
    assert.equal(resolveBaseUrl("http://127.0.0.1:9000/"), "http://127.0.0.1:9000");
  });

  it("treats only loopback hosts as locally startable", () => {
    assert.equal(isLoopbackBaseUrl("http://127.0.0.1:8765"), true);
    assert.equal(isLoopbackBaseUrl("http://localhost:8765"), true);
    assert.equal(isLoopbackBaseUrl("http://[::1]:8765"), true);
    assert.equal(isLoopbackBaseUrl("http://10.0.0.5:8765"), false);
    assert.equal(isLoopbackBaseUrl("https://example.com"), false);
    assert.equal(isLoopbackBaseUrl("not a url"), false);
  });

  it("resolves the repository backend directory and honors RETRACK_BACKEND_DIR", () => {
    assert.equal(resolveBackendDir({ env: {} }), path.resolve(process.cwd(), "backend"));
    assert.equal(resolveBackendDir({ env: { RETRACK_BACKEND_DIR: "/tmp/custom-backend" } }), "/tmp/custom-backend");
  });

  it("prefers the backend virtualenv interpreter", () => {
    assert.equal(
      resolvePython({ backendDir: "/x", exists: (p) => p === "/x/.venv/bin/python", probe: () => false }),
      "/x/.venv/bin/python"
    );
    assert.equal(
      resolvePython({ backendDir: "/x", exists: () => false, probe: (cmd) => cmd === "python3" }),
      "python3"
    );
    assert.equal(resolvePython({ backendDir: "/x", exists: () => false, probe: () => false }), null);
  });

  it("shares the desktop runtime's backend log path", () => {
    assert.equal(backendLogPath({ tmpdir: os.tmpdir() }), path.join(os.tmpdir(), "retrack-backend.log"));
  });
});

describe("lifecycle: attach", () => {
  it("adopts an already-reachable backend without spawning or signalling it", async () => {
    const stub = await startStubBackend();
    try {
      const backend = await ensureBackend({
        baseUrl: stub.baseUrl,
        backendDir: path.join(os.tmpdir(), "does-not-exist"),
        spawnImpl: () => {
          throw new Error("must not spawn when a backend is reachable");
        },
      });

      assert.equal(backend.owned, false);
      assert.equal(backend.pid, null);
      assert.equal(backend.baseUrl, stub.baseUrl);

      const before = stub.requests.length;
      await backend.stop();
      const after = await (await fetch(`${stub.baseUrl}/health`)).json();
      assert.equal(after.status, "ok", "the pre-existing backend is still serving");
      assert.ok(stub.requests.length > before, "stop() is a no-op for an attached backend");
    } finally {
      await stub.close();
    }
  });

  it("refuses to start a backend for a non-loopback URL", async () => {
    await assert.rejects(
      () =>
        ensureBackend({
          baseUrl: "http://10.255.255.1:8765",
          probeTimeoutMs: 100,
          spawnImpl: () => {
            throw new Error("must not spawn for a remote URL");
          },
        }),
      (error) => {
        assert.ok(error instanceof BackendStartupError);
        assert.match(error.message, /loopback/);
        return true;
      }
    );
  });

  it("reports an invalid base URL", async () => {
    await assert.rejects(() => ensureBackend({ baseUrl: "::not-a-url::" }), /invalid backend URL/);
  });

  it("reports a missing backend directory before spawning", async () => {
    const port = await freePort();
    await assert.rejects(
      () =>
        ensureBackend({
          baseUrl: baseUrlFor(port),
          backendDir: path.join(os.tmpdir(), `missing-backend-${process.pid}-${port}`),
          probeTimeoutMs: 200,
        }),
      /backend directory not found/
    );
  });
});

describe("lifecycle: spawn and readiness", () => {
  it("spawns with the desktop runtime contract, owns the child, and stops it gracefully", async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "ok" });
    const status = [];

    const backend = await ensureBackend({
      baseUrl: baseUrlFor(port),
      backendDir: fake.backendDir,
      logPath: fake.logPath,
      env: fakeBackendEnv(fake),
      pollIntervalMs: 100,
      probeTimeoutMs: 500,
      readyTimeoutMs: 10_000,
      onStatus: (message) => status.push(message),
    });

    try {
      assert.equal(backend.owned, true);
      assert.ok(backend.pid > 0);
      assert.ok(status.some((message) => /starting backend/.test(message)));

      // Spawn contract: same argv, cwd, environment and watchdog wiring as lib.rs.
      const argv = readJson(path.join(fake.markers, "argv.json"));
      assert.deepEqual(argv, [
        "-m",
        "uvicorn",
        "app.server:app",
        "--host",
        "127.0.0.1",
        "--port",
        String(port),
      ]);

      const env = readJson(path.join(fake.markers, "env.json"));
      assert.equal(env.RETRACK_PARENT_PID, String(process.pid));
      assert.equal(env.PYTHONPATH, fake.backendDir);
      assert.equal(env.LLM_MODEL, "phi3:mini");
      assert.equal(env.VECTOR_DB_PROVIDER, "lancedb");
      assert.equal(env.GRAPH_DB_PROVIDER, "kuzu");
      assert.equal(env.EMBEDDING_DIMENSIONS, "768");
      assert.equal(path.resolve(env.cwd), path.resolve(fake.backendDir));
    } finally {
      const grandchild = readJson(path.join(fake.markers, "grandchild.json"));
      await backend.stop();
      assert.equal(readText(path.join(fake.markers, "signals.log"))?.trim(), "SIGTERM");
      assert.ok(await waitForPidGone(backend.pid), "spawned backend is gone");
      if (process.platform !== "win32") {
        assert.ok(await waitForPidGone(grandchild?.pid), "the whole backend tree is gone");
      }
      await backend.stop(); // idempotent
    }
  });

  it("attaches without ownership when the child loses the port race to another backend", async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "slowlisten" });
    // The child only binds after the external backend has taken the port.
    const running = ensureBackend({
      baseUrl: baseUrlFor(port),
      backendDir: fake.backendDir,
      logPath: fake.logPath,
      env: fakeBackendEnv(fake, { RETRACK_STUB_LISTEN_DELAY_MS: "800" }),
      pollIntervalMs: 100,
      probeTimeoutMs: 400,
      readyTimeoutMs: 10_000,
    });

    // The initial probe must fail first (nothing is listening) so the child is
    // spawned; only then does the external backend take the port.
    const spawned = await waitFor(() => readJson(path.join(fake.markers, "pids.json")), {
      timeoutMs: 5_000,
    });
    assert.ok(spawned?.self, "the TUI spawned its own child before the port race");

    const external = await waitFor(
      () =>
        startStubServerOn(port).catch(() => null),
      { timeoutMs: 5_000 }
    );

    const backend = await running;
    try {
      assert.equal(backend.owned, true, "the live child is the one this invocation started");
      assert.ok(backend.pid > 0);
      // The external backend owns the port; only the spawned child may ever be
      // signalled, so stop() must leave the winner of the race untouched.
      await backend.stop();
      const stillThere = await (await fetch(`${backend.baseUrl}/health`)).json();
      assert.equal(stillThere.status, "ok", "the external backend survived stop()");
      const pids = readJson(path.join(fake.markers, "pids.json"));
      assert.ok(await waitForPidGone(pids?.self), "the spawned child is gone");
    } finally {
      await external?.close();
    }
  });

  it("adopts another backend without ownership when the child dies before readiness", async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "hang" });
    const running = ensureBackend({
      baseUrl: baseUrlFor(port),
      backendDir: fake.backendDir,
      logPath: fake.logPath,
      env: fakeBackendEnv(fake),
      pollIntervalMs: 400,
      probeTimeoutMs: 400,
      readyTimeoutMs: 15_000,
    });

    const pids = await waitFor(() => readJson(path.join(fake.markers, "pids.json")), { timeoutMs: 5_000 });
    process.kill(pids.self, "SIGKILL");
    const external = await startStubServerOn(port);

    const backend = await running;
    try {
      assert.equal(backend.owned, false, "a backend that replaced our dead child is not ours");
      assert.equal(backend.pid, null);
      await backend.stop();
      const health = await (await fetch(`${backend.baseUrl}/health`)).json();
      assert.equal(health.status, "ok", "the adopted backend survived stop()");
    } finally {
      await external.close();
    }
  });
});

describe("lifecycle: startup failure", () => {
  it("reports the child's real failure, its log tail, and leaves no orphan", async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "exit" });

    await assert.rejects(
      () =>
        ensureBackend({
          baseUrl: baseUrlFor(port),
          backendDir: fake.backendDir,
          logPath: fake.logPath,
          env: fakeBackendEnv(fake),
          pollIntervalMs: 50,
          probeTimeoutMs: 300,
          readyTimeoutMs: 5_000,
        }),
      (error) => {
        assert.ok(error instanceof BackendStartupError);
        assert.match(error.message, /exited before readiness/);
        assert.equal(error.exitCode, 3);
        assert.match(error.message, /simulated startup failure/, "the log tail carries the real error");
        assert.equal(error.logPath, fake.logPath);
        return true;
      }
    );

    const pids = readJson(path.join(fake.markers, "pids.json"));
    assert.ok(pids?.self, "the child recorded its pid before failing");
    assert.equal(pidAlive(pids.self), false, "no orphan backend remains");
  });

  it("fails deterministically on readiness timeout and cleans the child up", async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "hang" });
    const startedAt = Date.now();

    await assert.rejects(
      () =>
        ensureBackend({
          baseUrl: baseUrlFor(port),
          backendDir: fake.backendDir,
          logPath: fake.logPath,
          env: fakeBackendEnv(fake),
          pollIntervalMs: 50,
          probeTimeoutMs: 200,
          readyTimeoutMs: 800,
          shutdownGraceMs: 500,
        }),
      /did not become ready within 800ms/
    );

    assert.ok(Date.now() - startedAt < 10_000, "the timeout is bounded");
    const pids = readJson(path.join(fake.markers, "pids.json"));
    assert.ok(await waitForPidGone(pids?.self), "the timed-out child was reaped");
  });
});

describe("lifecycle: shutdown", () => {
  it("falls back to SIGKILL for a backend that ignores SIGTERM", async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "stubborn" });

    const backend = await ensureBackend({
      baseUrl: baseUrlFor(port),
      backendDir: fake.backendDir,
      logPath: fake.logPath,
      env: fakeBackendEnv(fake),
      pollIntervalMs: 100,
      probeTimeoutMs: 500,
      readyTimeoutMs: 10_000,
      shutdownGraceMs: 300,
    });

    const grandchild = readJson(path.join(fake.markers, "grandchild.json"));
    const startedAt = Date.now();
    await backend.stop();
    assert.ok(Date.now() - startedAt < 5_000, "cleanup is bounded");
    assert.ok(await waitForPidGone(backend.pid), "the stubborn backend was killed");
    if (process.platform !== "win32") {
      assert.ok(await waitForPidGone(grandchild?.pid), "the tree was killed too");
    }
    assert.equal(markerCount(fake, "signals.log"), 0, "no graceful exit was possible");
  });

  it("does not touch a backend it did not spawn", async () => {
    const stub = await startStubBackend();
    const fake = createFakeBackend({ mode: "ok" });
    try {
      const backend = await ensureBackend({
        baseUrl: stub.baseUrl,
        backendDir: fake.backendDir,
        env: fakeBackendEnv(fake),
      });
      assert.equal(backend.owned, false);
      await backend.stop();
      assert.equal(markerCount(fake, "starts.log"), 0);
      const health = await (await fetch(`${stub.baseUrl}/health`)).json();
      assert.equal(health.status, "ok");
    } finally {
      await stub.close();
    }
  });
});

/** Start an in-process stub pinned to a specific port (port-race helper). */
async function startStubServerOn(port) {
  const { createServer } = await import("node:http");
  const server = createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");
    if (req.url.startsWith("/health")) {
      res.end(JSON.stringify({ status: "ok", version: "0.1.0" }));
      return;
    }
    res.end(JSON.stringify({ status: "ok", ok: true }));
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () =>
      resolve({ server, close: () => new Promise((done) => server.close(done)) })
    );
  });
}
