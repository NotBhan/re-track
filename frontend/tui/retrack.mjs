#!/usr/bin/env node
/**
 * RE:Track terminal user interface.
 *
 * Terminal presentation only. All backend access goes through the shared
 * interface contract module (frontend/shared/backend-client.mjs).
 *
 * This entry point must never import React, Tauri APIs, or GUI components, and
 * must restore the terminal (cursor, alternate screen, raw mode) on every exit
 * path — including Ctrl+C, EOF and uncaught errors.
 *
 * Usage:
 *   node frontend/tui/retrack.mjs
 *   npm run tui
 */

import { createBackendClient, BackendRequestError, BackendUnreachableError } from "../shared/backend-client.mjs";

const ESC = "\x1b[";
const REFRESH_INTERVAL_MS = 5_000;

const supportsTty = Boolean(process.stdin.isTTY && process.stdout.isTTY);

function enterScreen() {
  process.stdout.write(`${ESC}?1049h${ESC}?25l`);
}

function leaveScreen() {
  process.stdout.write(`${ESC}?25h${ESC}?1049l`);
}

function clear() {
  process.stdout.write(`${ESC}2J${ESC}H`);
}

function style(code, text) {
  return supportsTty ? `${ESC}${code}m${text}${ESC}0m` : text;
}

const bold = (t) => style("1", t);
const dim = (t) => style("2", t);
const green = (t) => style("32", t);
const amber = (t) => style("33", t);
const red = (t) => style("31", t);

function stateColor(state) {
  if (state === "healthy" || state === "active" || state === "indexed") return green(state);
  if (state === "degraded" || state === "indexing" || state === "registered") return amber(state);
  return red(state ?? "unknown");
}

function line(label, value, valueRenderer = (v) => v) {
  return `  ${dim(label.padEnd(24))} ${valueRenderer(String(value))}`;
}

class TuiState {
  constructor() {
    this.health = null;
    this.status = null;
    this.repositories = [];
    this.packages = [];
    this.error = null;
    this.loading = true;
    this.lastUpdated = null;
  }
}

async function refresh(client, state) {
  state.loading = true;
  state.error = null;
  try {
    // Independent fetches: one failing subsystem must not blank the whole view.
    const [health, status, repos, packages] = await Promise.allSettled([
      client.health(),
      client.status(),
      client.listRepositories(),
      client.listContextPackages(),
    ]);

    state.health = health.status === "fulfilled" ? health.value : null;
    state.status = status.status === "fulfilled" ? status.value : null;
    state.repositories = repos.status === "fulfilled" ? repos.value?.repositories ?? [] : [];
    state.packages = packages.status === "fulfilled" ? packages.value?.packages ?? [] : [];

    const failures = [health, status, repos, packages].filter((r) => r.status === "rejected");
    state.error = failures.length
      ? `${failures.length}/4 subsystem queries failed: ${failures[0].reason?.message ?? "unknown error"}`
      : null;
  } catch (error) {
    state.error = error instanceof Error ? error.message : String(error);
  } finally {
    state.loading = false;
    state.lastUpdated = new Date();
  }
}

function render(client, state) {
  clear();
  const width = process.stdout.columns || 100;
  const rule = dim("─".repeat(Math.max(20, Math.min(width, 100))));

  process.stdout.write(`${bold("RE:Track")} ${dim("· terminal interface")}  ${dim(client.baseUrl)}\n`);
  process.stdout.write(`${rule}\n`);

  if (state.error) {
    process.stdout.write(`${red("!")} ${state.error}\n\n`);
  }

  // --- Runtime & engine health -------------------------------------------------
  process.stdout.write(`${bold("Runtime")}\n`);
  if (state.health) {
    const h = state.health;
    process.stdout.write(`${line("Backend", h.status, stateColor)}\n`);
    process.stdout.write(
      `${line("Provider", `${h.provider_identity ?? h.provider ?? "unknown"}`, (v) => v)}\n`
    );
    process.stdout.write(
      `${line("Provider state", h.provider_health_state ?? "unknown", stateColor)}\n`
    );
    process.stdout.write(`${line("Configured model", h.configured_model ?? "None")}\n`);
    process.stdout.write(
      `${line("Verified active", h.active_model ?? "None verified", (v) =>
        h.active_model ? green(v) : dim(v))}\n`
    );
    process.stdout.write(
      `${line("Cognee engine", h.cognee_state ?? (h.cognee_initialized ? "healthy" : "unavailable"), stateColor)}\n`
    );
    process.stdout.write(
      `${line("Concurrency", `${h.concurrency_queue_depth ?? 0}/${h.concurrency_queue_capacity ?? 0} queued`, (v) => v)}\n`
    );
    process.stdout.write(
      `${line(
        "RAM / CPU",
        `${h.ram_used_gb ?? "?"}/${h.ram_total_gb ?? "?"} GB · CPU ${h.cpu_percent ?? "?"}%`
      )}\n`
    );
    process.stdout.write(`${line("Execution device", h.execution_device ?? "Unavailable")}\n`);
  } else {
    process.stdout.write(`  ${dim("unavailable")}\n`);
  }
  process.stdout.write("\n");

  // --- Repositories ------------------------------------------------------------
  process.stdout.write(`${bold(`Repositories (${state.repositories.length})`)}\n`);
  if (state.repositories.length === 0) {
    process.stdout.write(`  ${dim("none registered")}\n`);
  } else {
    for (const repo of state.repositories.slice(0, 8)) {
      process.stdout.write(
        `  ${String(repo.name).padEnd(26)} ${stateColor(repo.status)}  ${dim(repo.local_path)}\n`
      );
    }
    if (state.repositories.length > 8) {
      process.stdout.write(`  ${dim(`… ${state.repositories.length - 8} more`)}\n`);
    }
  }
  process.stdout.write("\n");

  // --- Context packages --------------------------------------------------------
  process.stdout.write(`${bold(`Context packages (${state.packages.length})`)}\n`);
  if (state.packages.length === 0) {
    process.stdout.write(`  ${dim("none saved")}\n`);
  } else {
    for (const pkg of state.packages.slice(0, 5)) {
      process.stdout.write(
        `  ${String(pkg.name).slice(0, 38).padEnd(40)} ${dim(`${pkg.token_estimate ?? 0} tokens`)}\n`
      );
    }
    if (state.packages.length > 5) {
      process.stdout.write(`  ${dim(`… ${state.packages.length - 5} more`)}\n`);
    }
  }
  process.stdout.write("\n");

  process.stdout.write(`${rule}\n`);
  const stamp = state.lastUpdated ? state.lastUpdated.toLocaleTimeString() : "--:--:--";
  process.stdout.write(
    `${dim(`updated ${stamp}`)}${state.loading ? dim(" · refreshing…") : ""}   ${dim("[r] refresh  [q] quit")}\n`
  );
}

async function main() {
  const client = createBackendClient({ baseUrl: process.env.RETRACK_BACKEND_URL });
  const state = new TuiState();

  if (!supportsTty) {
    // Non-interactive invocation (pipe / CI): emit a single snapshot and exit.
    await refresh(client, state);
    if (state.error) {
      process.stderr.write(`${state.error}\n`);
      return 1;
    }
    process.stdout.write(
      `RE:Track · ${client.baseUrl} · backend=${state.health?.status ?? "unknown"} · ` +
        `repos=${state.repositories.length} · packages=${state.packages.length}\n`
    );
    return 0;
  }

  let refreshTimer = null;
  let finished = false;

  const cleanup = () => {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = null;
    if (process.stdin.isTTY && typeof process.stdin.setRawMode === "function") {
      process.stdin.setRawMode(false);
    }
    process.stdin.removeListener("data", onKey);
    leaveScreen();
  };

  const finish = (code) => {
    if (finished) return;
    finished = true;
    cleanup();
    process.exitCode = code;
    process.exit(code);
  };

  function onKey(buffer) {
    const key = buffer.toString("utf8");
    if (key === "q" || key === "\u0003") {
      finish(0);
      return;
    }
    if (key === "r") {
      refresh(client, state).then(() => render(client, state));
    }
  }

  enterScreen();
  process.stdin.setRawMode(true);
  process.stdin.resume();
  process.stdin.on("data", onKey);
  process.stdin.on("end", () => finish(0));
  process.on("SIGINT", () => finish(0));
  process.on("SIGTERM", () => finish(0));
  process.on("uncaughtException", (error) => {
    cleanup();
    process.stderr.write(`\nRE:Track TUI fatal error: ${error.message}\n`);
    finish(1);
  });

  await refresh(client, state);
  render(client, state);

  refreshTimer = setInterval(() => {
    refresh(client, state).then(() => render(client, state));
  }, REFRESH_INTERVAL_MS);

  return null;
}

main()
  .then((code) => {
    if (code !== null && code !== undefined) {
      process.exitCode = code;
      // Interactive mode keeps running until the user quits.
      process.exit(code);
    }
  })
  .catch((error) => {
    if (error instanceof BackendUnreachableError || error instanceof BackendRequestError) {
      process.stderr.write(`${error.message}\n`);
    } else {
      process.stderr.write(`Error: ${error.message}\n`);
    }
    if (supportsTty) leaveScreen();
    process.exitCode = 1;
  });
