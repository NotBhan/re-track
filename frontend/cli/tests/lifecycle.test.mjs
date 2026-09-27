import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  ensureBackend,
  isLoopbackBaseUrl,
  resolveBaseUrl,
  backendLogPath,
  resolveBackendDir,
  BackendStartupError,
  BACKEND_ENV,
} from "../backend-lifecycle.mjs";

/** A scripted child process: records signals, emits exit when the script says so. */
function fakeChild({ pid = 4242, exitOnSigterm = true } = {}) {
  const child = new EventEmitter();
  child.pid = pid;
  child.exitCode = null;
  child.signalCode = null;
  child.kills = [];
  child.kill = (signal) => {
    child.kills.push(signal);
    child.exitCode = child.exitCode ?? 0;
    child.emit("exit", child.exitCode, null);
    return true;
  };
  child.exitOnSigterm = exitOnSigterm;
  child.exitWith = (code) => {
    child.exitCode = code;
    child.emit("exit", code, null);
  };
  return child;
}

function scriptedFetch(results) {
  const calls = [];
  const fetchImpl = async (url) => {
    calls.push(url);
    const next = results.length > 1 ? results.shift() : results[0];
    if (next instanceof Error) throw next;
    return { ok: Boolean(next) };
  };
  fetchImpl.calls = calls;
  return fetchImpl;
}

function tempLog(contents = "") {
  const dir = mkdtempSync(path.join(os.tmpdir(), "retrack-cli-lifecycle-"));
  const logPath = path.join(dir, "retrack-backend.log");
  writeFileSync(logPath, contents, "utf8");
  return { dir, logPath };
}

const SPAWN_OPTIONS = {
  backendDir: "/tmp/retrack-cli-fake-backend",
  python: "/tmp/retrack-cli-fake-backend/.venv/bin/python",
  exists: () => true,
  pollIntervalMs: 1,
};

describe("cli lifecycle: attach and ownership", () => {
  it("attaches to a reachable backend without spawning anything", async () => {
    let spawned = false;
    const backend = await ensureBackend({
      baseUrl: "http://127.0.0.1:8765",
      fetchImpl: scriptedFetch([true]),
      spawnImpl: () => {
        spawned = true;
        return fakeChild();
      },
    });
    assert.equal(backend.owned, false);
    assert.equal(backend.pid, null);
    assert.equal(spawned, false, "a reachable backend is never replaced");
    await backend.stop(); // must be a no-op
  });

  it("starts a backend when none answers and terminates only that tree", async () => {
    const { dir, logPath } = tempLog();
    try {
      const child = fakeChild();
      const kills = [];
      const fetchImpl = scriptedFetch([false, false, true]);
      const backend = await ensureBackend({
        ...SPAWN_OPTIONS,
        baseUrl: "http://127.0.0.1:8765",
        logPath,
        fetchImpl,
        spawnImpl: () => child,
        kill: (pid, signal) => {
          kills.push({ pid, signal });
          if (signal === "SIGTERM" && child.exitOnSigterm) child.exitWith(0);
        },
      });
      assert.equal(backend.owned, true);
      assert.equal(backend.pid, 4242);
      await backend.stop();
      assert.deepEqual(kills, [{ pid: -4242, signal: "SIGTERM" }], "owned backends are SIGTERMed, then reaped");
      await backend.stop(); // idempotent
      assert.equal(kills.length, 1);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("attaches when the spawned child loses the port race to a real backend", async () => {
    const { dir, logPath } = tempLog();
    try {
      const child = fakeChild();
      const backend = await ensureBackend({
        ...SPAWN_OPTIONS,
        baseUrl: "http://127.0.0.1:8765",
        logPath,
        // initial probe misses, first loop probe misses, the race probe answers
        fetchImpl: scriptedFetch([false, false, true]),
        spawnImpl: () => {
          setImmediate(() => child.exitWith(3));
          return child;
        },
        kill: () => {},
      });
      assert.equal(backend.owned, false, "a backend that answers is attached to, never killed");
      assert.equal(backend.pid, null);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("does not start anything under autoStart: false", async () => {
    await assert.rejects(
      ensureBackend({
        baseUrl: "http://127.0.0.1:8765",
        autoStart: false,
        fetchImpl: scriptedFetch([false]),
      }),
      (error) => error instanceof BackendStartupError && /automatic startup disabled by --no-start/.test(error.message)
    );
  });
});

describe("cli lifecycle: startup failures", () => {
  it("reports the child's own failure with the log tail and reaps it", async () => {
    const { dir, logPath } = tempLog("boot\nsimulated startup failure\n");
    try {
      const child = fakeChild();
      const error = await ensureBackend({
        ...SPAWN_OPTIONS,
        baseUrl: "http://127.0.0.1:8765",
        logPath,
        readyTimeoutMs: 500,
        fetchImpl: scriptedFetch([false, false]),
        spawnImpl: () => {
          setImmediate(() => child.exitWith(3));
          return child;
        },
        kill: () => {},
      }).catch((caught) => caught);

      assert.ok(error instanceof BackendStartupError, `expected a startup error, got ${error}`);
      assert.match(error.message, /backend process exited before readiness \(exit code 3\)/);
      assert.match(error.message, /simulated startup failure/, "the backend's own log is reported");
      assert.equal(error.exitCode, 3);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("times out under a bounded deadline and terminates the child", async () => {
    const { dir, logPath } = tempLog();
    try {
      const child = fakeChild({ exitOnSigterm: false });
      const kills = [];
      const error = await ensureBackend({
        ...SPAWN_OPTIONS,
        baseUrl: "http://127.0.0.1:8765",
        logPath,
        readyTimeoutMs: 20,
        shutdownGraceMs: 10,
        fetchImpl: scriptedFetch([false]),
        spawnImpl: () => child,
        kill: (pid, signal) => kills.push(signal),
      }).catch((caught) => caught);

      assert.ok(error instanceof BackendStartupError);
      assert.match(error.message, /backend did not become ready within 20ms/);
      assert.deepEqual(kills, ["SIGTERM", "SIGKILL"], "a wedged child is escalated, never left behind");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("refuses to start a non-loopback backend URL", async () => {
    await assert.rejects(
      ensureBackend({
        ...SPAWN_OPTIONS,
        baseUrl: "http://192.0.2.10:8765",
        fetchImpl: scriptedFetch([false]),
      }),
      /automatic startup only supports a loopback backend URL/
    );
  });

  it("states a missing backend directory, interpreter or URL precisely", async () => {
    await assert.rejects(
      ensureBackend({ baseUrl: "http://127.0.0.1:8765", fetchImpl: scriptedFetch([false]), exists: () => false, env: {} }),
      /backend directory not found/
    );
    await assert.rejects(
      ensureBackend({
        ...SPAWN_OPTIONS,
        python: undefined,
        baseUrl: "http://127.0.0.1:8765",
        fetchImpl: scriptedFetch([false]),
        resolvePython: () => null,
      }),
      /Python not found/
    );
    await assert.rejects(ensureBackend({ baseUrl: "not-a-url" }), /invalid backend URL/);
  });
});

describe("cli lifecycle: pure helpers", () => {
  it("resolves base URLs the same way the desktop runtime does", () => {
    assert.equal(resolveBaseUrl("http://127.0.0.1:9999/"), "http://127.0.0.1:9999");
    assert.equal(resolveBaseUrl(""), "http://127.0.0.1:8765");
    assert.equal(isLoopbackBaseUrl("http://localhost:8765"), true);
    assert.equal(isLoopbackBaseUrl("http://192.0.2.10:8765"), false);
    assert.match(backendLogPath({ tmpdir: "/tmp/x" }), /retrack-backend\.log$/);
    assert.equal(resolveBackendDir({ env: { RETRACK_BACKEND_DIR: "/opt/backend" } }), path.resolve("/opt/backend"));
    assert.equal(BACKEND_ENV.COGNEE_SKIP_CONNECTION_TEST, "true");
  });
});
