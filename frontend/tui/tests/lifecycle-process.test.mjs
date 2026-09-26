/**
 * Entry-point lifecycle suite: the real TUI process, a real child backend.
 *
 * Covers attach vs spawn, readiness, ownership, graceful/forced shutdown on
 * q / Ctrl+C / SIGTERM, startup failure, bounded readiness timeout, the non-TTY
 * snapshot contract, repeated launches, and zero leftover child processes.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

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

const here = path.dirname(fileURLToPath(import.meta.url));
const entry = path.resolve(here, "..", "retrack.mjs");
const hasScript = existsSync("/usr/bin/script");
const ENTER_ALT_SCREEN = "\u001b[?1049h";
const LEAVE_ALT_SCREEN = "\u001b[?1049l";

const url = (port) => `http://127.0.0.1:${port}`;
const readPids = (fake) => readJson(path.join(fake.markers, "pids.json"));

function startPty(baseUrl, { env = {} } = {}) {
  const command = `${JSON.stringify(process.execPath)} ${JSON.stringify(entry)}`;
  const child = spawn("script", ["-qec", command, "/dev/null"], {
    env: { ...process.env, RETRACK_BACKEND_URL: baseUrl, NO_COLOR: "1", ...env },
    stdio: ["pipe", "pipe", "pipe"],
  });
  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (chunk) => {
    stdout += chunk.toString("utf8");
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString("utf8");
  });
  const exited = new Promise((resolve) => child.on("exit", (code, signal) => resolve({ code, signal })));
  return {
    child,
    pid: child.pid,
    output: () => stdout,
    errors: () => stderr,
    exited,
    write: (data) => {
      if (!child.stdin.destroyed) child.stdin.write(data);
    },
    waitForOutput: (pattern, timeoutMs = 15_000) => waitFor(() => pattern.test(stdout), { timeoutMs }),
  };
}

async function withPty(baseUrl, options, body) {
  const pty = startPty(baseUrl, options);
  const guard = setTimeout(() => pty.child.kill("SIGKILL"), options.timeoutMs ?? 30_000);
  try {
    return await body(pty);
  } finally {
    clearTimeout(guard);
    try {
      pty.child.kill("SIGKILL");
    } catch {
      // Already exited.
    }
  }
}

function runPiped(baseUrl, { env = {}, timeoutMs = 25_000 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [entry], {
      env: { ...process.env, RETRACK_BACKEND_URL: baseUrl, ...env },
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
    child.on("error", reject);
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`piped run did not exit in time: ${stdout}${stderr}`));
    }, timeoutMs);
    child.on("exit", (code, signal) => {
      clearTimeout(timer);
      resolve({ code, signal, stdout, stderr, pid: child.pid });
    });
  });
}

/** Walk /proc to find the TUI node process under `script` (Linux only). */
function descendants(pid, acc = []) {
  try {
    const children = readFileSync(`/proc/${pid}/task/${pid}/children`, "utf8").trim();
    for (const value of children.split(/\s+/).filter(Boolean)) {
      const childPid = Number(value);
      acc.push(childPid);
      descendants(childPid, acc);
    }
  } catch {
    // Process already gone or /proc unavailable.
  }
  return acc;
}

function findTuiPid(rootPid) {
  for (const pid of descendants(rootPid)) {
    try {
      const cmdline = readFileSync(`/proc/${pid}/cmdline`, "utf8");
      const [executable] = cmdline.split("\0");
      // The `sh -c` wrapper mentions the entry path too; only the node process
      // has the node binary as argv[0].
      if (/(^|\/)node$/.test(executable) && cmdline.includes("tui/retrack.mjs")) return pid;
    } catch {
      // Raced with process exit.
    }
  }
  return null;
}

describe("tui lifecycle: interactive", () => {
  it("attaches to a running backend, spawns nothing, and leaves it alive", { timeout: 40_000 }, async (t) => {
    if (!hasScript) return t.skip("script(1) is not available");
    const stub = await startStubBackend();
    const fake = createFakeBackend();
    try {
      await withPty(
        stub.baseUrl,
        { env: fakeBackendEnv(fake) },
        async (pty) => {
          await pty.waitForOutput(/Repositories/);
          assert.equal(markerCount(fake, "starts.log"), 0, "no backend may be spawned while one is reachable");
          pty.write("q");
          const { code } = await pty.exited;
          assert.equal(code, 0, pty.errors());
          assert.ok(pty.output().includes(ENTER_ALT_SCREEN));
          assert.ok(pty.output().includes(LEAVE_ALT_SCREEN), "terminal restored");
        }
      );

      const health = await (await fetch(`${stub.baseUrl}/health`)).json();
      assert.equal(health.status, "ok", "the pre-existing backend is still running");
      assert.equal(markerCount(fake, "starts.log"), 0, "still nothing spawned");
    } finally {
      await stub.close();
    }
  });

  it("starts a backend when none is reachable and shuts it down on q", { timeout: 40_000 }, async (t) => {
    if (!hasScript) return t.skip("script(1) is not available");
    const port = await freePort();
    const fake = createFakeBackend();

    await withPty(url(port), { env: fakeBackendEnv(fake) }, async (pty) => {
      await pty.waitForOutput(/Repositories/);
      assert.equal(markerCount(fake, "starts.log"), 1, "exactly one backend was started");
      const pids = readPids(fake);
      assert.ok(pidAlive(pids.self), "the owned backend is running while the TUI is up");

      pty.write("q");
      const { code } = await pty.exited;
      assert.equal(code, 0, pty.errors());
      assert.ok(pty.output().includes(LEAVE_ALT_SCREEN), "terminal restored");

      assert.ok(await waitForPidGone(pids.self), "the owned backend was shut down");
      assert.equal(readText(path.join(fake.markers, "signals.log"))?.trim(), "SIGTERM");
    });
  });

  it("restores the terminal and stops the owned backend on ctrl-c", { timeout: 40_000 }, async (t) => {
    if (!hasScript) return t.skip("script(1) is not available");
    const port = await freePort();
    const fake = createFakeBackend();

    await withPty(url(port), { env: fakeBackendEnv(fake) }, async (pty) => {
      await pty.waitForOutput(/Repositories/);
      const pids = readPids(fake);
      pty.write("\u0003");
      const { code } = await pty.exited;
      assert.equal(code, 0, pty.errors());
      assert.ok(pty.output().includes(LEAVE_ALT_SCREEN), "terminal restored");
      assert.ok(await waitForPidGone(pids.self), "the owned backend was shut down");
    });
  });

  it("restores the terminal and stops the owned backend on SIGTERM", { timeout: 40_000 }, async (t) => {
    if (!hasScript) return t.skip("script(1) is not available");
    if (process.platform !== "linux") return t.skip("pid discovery requires /proc");
    const port = await freePort();
    const fake = createFakeBackend();

    await withPty(url(port), { env: fakeBackendEnv(fake) }, async (pty) => {
      await pty.waitForOutput(/Repositories/);
      const pids = readPids(fake);
      const tuiPid = await waitFor(() => findTuiPid(pty.pid), { timeoutMs: 5_000 });
      assert.ok(tuiPid, "found the interactive TUI process");

      process.kill(tuiPid, "SIGTERM");
      const { code } = await pty.exited;
      assert.equal(code, 0, pty.errors());
      assert.ok(pty.output().includes(LEAVE_ALT_SCREEN), "terminal restored");
      assert.ok(await waitForPidGone(pids.self), "the owned backend was shut down");
    });
  });

  it("lets a second TUI attach without spawning or killing the first backend", { timeout: 45_000 }, async (t) => {
    if (!hasScript) return t.skip("script(1) is not available");
    const port = await freePort();
    const fake = createFakeBackend();

    await withPty(url(port), { env: fakeBackendEnv(fake) }, async (pty) => {
      await pty.waitForOutput(/Repositories/);
      assert.equal(markerCount(fake, "starts.log"), 1);
      const pids = readPids(fake);

      const second = await runPiped(url(port), { env: fakeBackendEnv(fake) });
      assert.equal(second.code, 0, second.stderr);
      assert.match(
        second.stdout.split("\n").filter(Boolean).at(-1),
        /^RE:Track · http:\/\/127\.0\.0\.1:\d+ · backend=ok · repos=0 · packages=0$/
      );
      assert.equal(markerCount(fake, "starts.log"), 1, "the second instance must not spawn another backend");
      assert.equal(pidAlive(pids.self), true, "the second instance must not stop the first instance's backend");

      pty.write("q");
      await pty.exited;
      assert.ok(await waitForPidGone(pids.self), "the owning instance shut its backend down");
    });
  });
});

describe("tui lifecycle: non-TTY", () => {
  it("starts a backend, prints the single snapshot line, and cleans up", { timeout: 40_000 }, async () => {
    const port = await freePort();
    const fake = createFakeBackend();

    const run = await runPiped(url(port), { env: fakeBackendEnv(fake) });
    assert.equal(run.code, 0, run.stderr);

    const lines = run.stdout.split("\n").filter(Boolean);
    assert.equal(lines.length, 1, `stdout must stay a single line: ${run.stdout}`);
    assert.match(lines[0], /^RE:Track · http:\/\/127\.0\.0\.1:\d+ · backend=ok · repos=0 · packages=0$/);
    assert.equal(markerCount(fake, "starts.log"), 1, "the snapshot started the backend it needed");

    const pids = readPids(fake);
    assert.ok(await waitForPidGone(pids.self), "no child outlives stdout");
  });

  it("reports a startup failure, exits non-zero, and leaves no orphan", { timeout: 40_000 }, async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "exit" });

    const run = await runPiped(url(port), { env: fakeBackendEnv(fake) });
    assert.notEqual(run.code, 0);
    assert.equal(run.stdout, "", "nothing is printed to stdout on a failed startup");
    assert.match(run.stderr, /backend startup failed/);
    assert.match(run.stderr, /exited before readiness/);
    assert.match(run.stderr, /simulated startup failure/, "the backend's own error is reported");

    const pids = readPids(fake);
    assert.ok(await waitForPidGone(pids.self), "the failed child was reaped");
  });

  it("fails deterministically when readiness times out and still cleans up", { timeout: 40_000 }, async () => {
    const port = await freePort();
    const fake = createFakeBackend({ mode: "hang" });

    const run = await runPiped(url(port), {
      env: fakeBackendEnv(fake, { RETRACK_BACKEND_STARTUP_TIMEOUT_MS: "1500" }),
    });
    assert.notEqual(run.code, 0);
    assert.match(run.stderr, /did not become ready within 1500ms/);

    const pids = readPids(fake);
    assert.ok(await waitForPidGone(pids.self), "the timed-out child was reaped");
  });
});
