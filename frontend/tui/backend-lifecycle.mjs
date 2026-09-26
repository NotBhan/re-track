/**
 * RE:Track TUI backend lifecycle.
 *
 * Discovery, spawn, readiness, ownership and shutdown of the backend the TUI
 * talks to. This is the only TUI module that touches `node:child_process`:
 * state and rendering modules stay free of process management.
 *
 * The startup contract mirrors the desktop runtime (src-tauri/src/lib.rs):
 *   - resolve `backend/` and prefer `backend/.venv/bin/python`
 *   - run `python -m uvicorn app.server:app --host 127.0.0.1 --port <port>`
 *     from the backend directory with PYTHONPATH and the desktop environment
 *   - pass `RETRACK_PARENT_PID` so the backend's own parent-death watchdog
 *     terminates it if the TUI dies abruptly (SIGKILL, crash)
 *   - append stdout/stderr to `$TMPDIR/retrack-backend.log`
 *   - poll `GET /health` until ready, bounded by a deadline
 *   - shutdown sends SIGTERM to the backend process group, then SIGKILL after
 *     a bounded grace period
 *
 * Ownership: a backend is terminated only when THIS invocation spawned it
 * (`owned === true`). A backend that already answered `/health` is attached to
 * and never signalled — reachability, not the port, is what decides.
 */

import { spawn as nodeSpawn, spawnSync } from "node:child_process";
import { closeSync, existsSync, fstatSync, openSync, readSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));

export const DEFAULT_BASE_URL = "http://127.0.0.1:8765";

// Mirrors the desktop runtime: 60 polls, 1 s apart, 2 s per /health request.
const DEFAULT_READY_TIMEOUT_MS = 60_000;
const DEFAULT_POLL_INTERVAL_MS = 1_000;
const DEFAULT_PROBE_TIMEOUT_MS = 2_000;
// Mirrors the desktop runtime's 3 s SIGTERM window before SIGKILL.
const DEFAULT_SHUTDOWN_GRACE_MS = 3_000;
const SHUTDOWN_KILL_WAIT_MS = 1_000;
const LOG_TAIL_LINES = 12;
const LOG_TAIL_BYTES = 64 * 1024;
const READY_TIMEOUT_ENV = "RETRACK_BACKEND_STARTUP_TIMEOUT_MS";

/** Environment applied to a spawned backend — identical to the desktop runtime. */
export const BACKEND_ENV = Object.freeze({
  HUGGINGFACE_TOKENIZER: "nomic-ai/nomic-embed-text-v1",
  COGNEE_SKIP_CONNECTION_TEST: "true",
  ENABLE_BACKEND_ACCESS_CONTROL: "false",
  CACHING: "false",
  LLM_MODEL: "phi3:mini",
  EMBEDDING_MODEL: "nomic-embed-text:latest",
  EMBEDDING_DIMENSIONS: "768",
  VECTOR_DB_PROVIDER: "lancedb",
  GRAPH_DB_PROVIDER: "kuzu",
});

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);

/** Raised when automatic backend startup cannot reach readiness. */
export class BackendStartupError extends Error {
  constructor(message, { cause, logPath = null, exitCode = null, signal = null } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = "BackendStartupError";
    this.logPath = logPath;
    this.exitCode = exitCode;
    this.signal = signal;
  }
}

export function resolveBaseUrl(value) {
  const raw = typeof value === "string" && value.trim() ? value.trim() : DEFAULT_BASE_URL;
  return raw.replace(/\/+$/, "");
}

export function isLoopbackBaseUrl(baseUrl) {
  try {
    const hostname = new URL(baseUrl).hostname.replace(/^\[|\]$/g, "");
    return LOOPBACK_HOSTS.has(hostname);
  } catch {
    return false;
  }
}

/** Same log file the desktop runtime writes: $TMPDIR/retrack-backend.log. */
export function backendLogPath({ tmpdir = os.tmpdir() } = {}) {
  return path.join(tmpdir, "retrack-backend.log");
}

/**
 * Resolve the backend directory. Defaults to `<repo>/backend` relative to this
 * module (the desktop runtime resolves relative to the Tauri crate); the
 * RETRACK_BACKEND_DIR override exists for portable installs and tests.
 */
export function resolveBackendDir({ env = process.env, moduleDir = MODULE_DIR } = {}) {
  const override = env.RETRACK_BACKEND_DIR?.trim();
  if (override) return path.resolve(override);
  return path.resolve(moduleDir, "..", "..", "backend");
}

/** Resolve the interpreter exactly as the desktop runtime does. */
export function resolvePython({
  backendDir,
  onWindows = process.platform === "win32",
  exists = existsSync,
  probe = probeCommand,
} = {}) {
  const venvPython = onWindows
    ? path.join(backendDir, ".venv", "Scripts", "python.exe")
    : path.join(backendDir, ".venv", "bin", "python");
  if (exists(venvPython)) return venvPython;

  for (const command of ["python3.13", "python3", "python"]) {
    if (probe(command)) return command;
  }
  return null;
}

function probeCommand(command) {
  const result = spawnSync(command, ["--version"], { stdio: "ignore" });
  return result.status === 0;
}

function readPositiveInt(value) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

/** Single bounded `GET /health` — any 2xx counts as ready, like the runtime. */
async function probeHealth(baseUrl, { timeoutMs, fetchImpl }) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(`${baseUrl}/health`, {
      signal: controller.signal,
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cleanup();
      resolve();
    }, ms);
    const onAbort = () => {
      cleanup();
      reject(new BackendStartupError("backend startup interrupted"));
    };
    function cleanup() {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    }
    if (!signal) return;
    if (signal.aborted) {
      cleanup();
      reject(new BackendStartupError("backend startup interrupted"));
      return;
    }
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

function readLogTail(logPath, { lines = LOG_TAIL_LINES, maxBytes = LOG_TAIL_BYTES } = {}) {
  if (!logPath) return "";
  let fd;
  try {
    fd = openSync(logPath, "r");
    const { size } = fstatSync(fd);
    const length = Math.min(size, maxBytes);
    if (length <= 0) return "";
    const buffer = Buffer.alloc(length);
    readSync(fd, buffer, 0, length, size - length);
    return buffer
      .toString("utf8")
      .split("\n")
      .filter((line) => line.trim())
      .slice(-lines)
      .join("\n")
      .trim();
  } catch {
    return "";
  } finally {
    if (fd !== undefined) {
      try {
        closeSync(fd);
      } catch {
        // The log is diagnostic only; a failed close must not mask startup errors.
      }
    }
  }
}

function describeExit({ code, signal }) {
  if (signal) return `signal ${signal}`;
  return `exit code ${code ?? "unknown"}`;
}

function startupFailure(error, logPath) {
  error.logPath = error.logPath ?? logPath;
  const tail = readLogTail(logPath);
  if (tail) {
    error.message += `\n--- ${logPath} ---\n${tail}`;
  }
  return error;
}

function startBackendProcess({
  python,
  backendDir,
  port,
  env,
  logPath,
  spawn,
  platform,
  parentPid,
}) {
  const logFd = openSync(logPath, "a");
  try {
    return spawn(
      python,
      ["-m", "uvicorn", "app.server:app", "--host", "127.0.0.1", "--port", String(port)],
      {
        cwd: backendDir,
        env: {
          ...env,
          ...BACKEND_ENV,
          PYTHONPATH: backendDir,
          RETRACK_PARENT_PID: String(parentPid),
        },
        stdio: ["ignore", logFd, logFd],
        // Own process group so the whole backend tree can be signalled on exit.
        // The desktop runtime gets the same effect from PR_SET_PDEATHSIG.
        detached: platform !== "win32",
      }
    );
  } finally {
    closeSync(logFd);
  }
}

function signalProcessGroup(child, signal, platform) {
  try {
    if (platform !== "win32" && child.pid) {
      process.kill(-child.pid, signal);
    } else {
      child.kill(signal);
    }
  } catch (error) {
    // ESRCH means the tree is already gone — nothing left to terminate.
    if (error?.code !== "ESRCH") {
      try {
        child.kill(signal);
      } catch {
        // Fall through to the bounded kill below.
      }
    }
  }
}

function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null || child.signalCode !== null) return Promise.resolve(true);
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      child.removeListener("exit", onExit);
      resolve(false);
    }, timeoutMs);
    const onExit = () => {
      clearTimeout(timer);
      resolve(true);
    };
    child.once("exit", onExit);
  });
}

/** SIGTERM the backend process tree, then SIGKILL it after a bounded grace. */
async function terminateChild(child, { graceMs, platform }) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return true;
  signalProcessGroup(child, "SIGTERM", platform);
  if (await waitForExit(child, graceMs)) return true;
  signalProcessGroup(child, "SIGKILL", platform);
  if (await waitForExit(child, SHUTDOWN_KILL_WAIT_MS)) return true;
  try {
    child.kill("SIGKILL");
  } catch {
    // Already reaped.
  }
  return waitForExit(child, SHUTDOWN_KILL_WAIT_MS);
}

async function waitForReady({
  baseUrl,
  readyTimeoutMs,
  deadline,
  pollIntervalMs,
  probeTimeoutMs,
  fetchImpl,
  logPath,
  signal,
  state,
}) {
  for (;;) {
    if (signal?.aborted) throw new BackendStartupError("backend startup interrupted");

    if (state.spawnError) {
      throw startupFailure(
        new BackendStartupError(`failed to start backend: ${state.spawnError.message}`, {
          cause: state.spawnError,
        }),
        logPath
      );
    }

    if (state.exit) {
      // The child can lose a race for the port to a backend someone else
      // started in the meantime; if that backend answers, attach to it.
      if (await probeHealth(baseUrl, { timeoutMs: probeTimeoutMs, fetchImpl })) {
        return { attached: true };
      }
      throw startupFailure(
        new BackendStartupError(
          `backend process exited before readiness (${describeExit(state.exit)})`,
          { exitCode: state.exit.code, signal: state.exit.signal }
        ),
        logPath
      );
    }

    if (await probeHealth(baseUrl, { timeoutMs: probeTimeoutMs, fetchImpl })) {
      return { attached: false };
    }

    if (Date.now() >= deadline) {
      throw startupFailure(
        new BackendStartupError(`backend did not become ready within ${readyTimeoutMs}ms`),
        logPath
      );
    }

    await delay(pollIntervalMs, signal);
  }
}

/**
 * Ensure a RE:Track backend is reachable for `baseUrl`.
 *
 * - already reachable → attached (`owned: false`), never signalled
 * - unreachable and loopback → spawned with the desktop runtime's contract,
 *   then bounded readiness polling; the caller only proceeds once ready
 * - startup failure → any spawned child is reaped first, then
 *   `BackendStartupError` is thrown with the real failure and log tail
 *
 * @returns {Promise<{ baseUrl: string, owned: boolean, pid: number|null, logPath: string|null, stop: () => Promise<void> }>}
 */
export async function ensureBackend(options = {}) {
  const env = options.env ?? process.env;
  const fetchImpl = options.fetchImpl ?? fetch;
  const spawn = options.spawnImpl ?? nodeSpawn;
  const exists = options.exists ?? existsSync;
  const platform = options.platform ?? process.platform;
  const parentPid = options.parentPid ?? process.pid;
  const onStatus = options.onStatus ?? (() => {});
  const signal = options.signal;

  const baseUrl = resolveBaseUrl(options.baseUrl ?? env.RETRACK_BACKEND_URL);
  const probeTimeoutMs = options.probeTimeoutMs ?? DEFAULT_PROBE_TIMEOUT_MS;
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
  const readyTimeoutMs =
    options.readyTimeoutMs ?? readPositiveInt(env[READY_TIMEOUT_ENV]) ?? DEFAULT_READY_TIMEOUT_MS;
  const shutdownGraceMs = options.shutdownGraceMs ?? DEFAULT_SHUTDOWN_GRACE_MS;
  const logPath = options.logPath ?? backendLogPath();

  try {
    new URL(baseUrl);
  } catch {
    throw new BackendStartupError(`invalid backend URL: ${baseUrl}`);
  }

  if (await probeHealth(baseUrl, { timeoutMs: probeTimeoutMs, fetchImpl })) {
    return { baseUrl, owned: false, pid: null, logPath: null, stop: async () => {} };
  }

  if (!isLoopbackBaseUrl(baseUrl)) {
    throw new BackendStartupError(
      `backend unreachable at ${baseUrl}; automatic startup only supports a loopback backend URL`
    );
  }

  const backendDir = options.backendDir ?? resolveBackendDir({ env });
  if (!exists(path.join(backendDir, "app", "server.py"))) {
    throw new BackendStartupError(
      `backend directory not found: ${backendDir} (expected app/server.py; set RETRACK_BACKEND_DIR)`
    );
  }

  const python = options.python ?? resolvePython({ backendDir, onWindows: platform === "win32", exists });
  if (!python) {
    throw new BackendStartupError(
      `Python not found for ${backendDir}. Create backend/.venv or install Python.`
    );
  }

  const port = new URL(baseUrl).port || "80";
  onStatus(`starting backend · ${path.basename(backendDir)} · log ${logPath}`);

  const child = startBackendProcess({
    python,
    backendDir,
    port,
    env,
    logPath,
    spawn,
    platform,
    parentPid,
  });

  const state = { spawnError: null, exit: null };
  child.once("error", (error) => {
    state.spawnError = error;
  });
  child.once("exit", (code, exitSignal) => {
    state.exit = { code, signal: exitSignal };
  });

  let ready;
  try {
    ready = await waitForReady({
      baseUrl,
      readyTimeoutMs,
      deadline: Date.now() + readyTimeoutMs,
      pollIntervalMs,
      probeTimeoutMs,
      fetchImpl,
      logPath,
      signal,
      state,
    });
  } catch (error) {
    // Never surface a startup failure while leaving the child we spawned behind.
    try {
      await terminateChild(child, { graceMs: shutdownGraceMs, platform });
    } catch {
      // The child is already gone; the startup error is what matters.
    }
    throw error;
  }

  if (ready.attached) {
    // Another backend won the race for the port; it is not ours to terminate.
    return { baseUrl, owned: false, pid: null, logPath, stop: async () => {} };
  }

  let stopped = false;
  return {
    baseUrl,
    owned: true,
    pid: child.pid ?? null,
    logPath,
    stop: async () => {
      if (stopped) return;
      stopped = true;
      await terminateChild(child, { graceMs: shutdownGraceMs, platform });
    },
  };
}
