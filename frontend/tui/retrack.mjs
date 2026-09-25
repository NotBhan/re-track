#!/usr/bin/env node
/**
 * RE:Track terminal user interface — entry point.
 *
 * Terminal lifecycle and I/O only: alternate-screen handling, raw mode, the
 * key event loop, resize handling, refresh scheduling and every exit path.
 * Application behaviour lives in state.mjs; frame composition in render.mjs.
 *
 * This entry point must never import React, Tauri APIs, GUI components, or the
 * CLI, and must restore the terminal (cursor, alternate screen, raw mode) on
 * every exit path — including q, Ctrl+C, SIGINT/SIGTERM, stdin end and
 * uncaught exceptions.
 *
 * Usage:
 *   node frontend/tui/retrack.mjs
 *   npm run tui
 *   node frontend/tui/retrack.mjs | cat      # non-TTY: single snapshot line
 */

import { createBackendClient, BackendRequestError, BackendUnreachableError } from "../shared/backend-client.mjs";
import { createApp, decodeInput } from "./state.mjs";
import { buildModel, composeFrame } from "./render.mjs";
import { createStyler } from "./theme.mjs";

const ESC = "\x1b[";
const TICK_MS = 250;
// Keystrokes can arrive faster than a terminal can absorb full frames (typing,
// paste, key repeat). Repaints are coalesced into one frame per window so input
// echo stays prompt without flooding the terminal.
const PAINT_COALESCE_MS = 50;
// While idle the TUI writes nothing, so failures at the terminal layer (closed
// pipe, hangup that survives as an I/O error) would go unnoticed. A periodic
// no-op write surfaces them so the process can exit.
const KEEPALIVE_MS = 4000;

const supportsTty = Boolean(process.stdin.isTTY && process.stdout.isTTY);

function enterScreen() {
  process.stdout.write(`${ESC}?1049h${ESC}?25l`);
}

function leaveScreen() {
  process.stdout.write(`${ESC}?25h${ESC}?1049l`);
}

function clearScreen() {
  process.stdout.write(`${ESC}2J${ESC}H`);
}

async function runSnapshot(client) {
  const app = createApp({ client });
  await app.load();
  const state = app.getState();

  if (state.error) {
    process.stderr.write(`${state.errorDetail ?? state.error}\n`);
    return 1;
  }

  process.stdout.write(
    `RE:Track · ${client.baseUrl} · backend=${state.health?.status ?? "unknown"} · ` +
      `repos=${state.repositories.length} · packages=${state.packages.length}\n`
  );
  return 0;
}

async function runInteractive(client) {
  const app = createApp({ client });
  const styler = createStyler({ enabled: !process.env.NO_COLOR });

  let finished = false;
  let repaintTimer = null;
  let pendingInput = "";
  let spinnerFrame = 0;
  let clearNext = false;
  let lastWriteAt = Date.now();

  const render = () => {
    const cols = process.stdout.columns || 100;
    const rows = process.stdout.rows || 30;
    const model = buildModel(app, { cols, rows, spinnerFrame });
    // Scroll bounds are derived from the built frame, so the state layer always
    // clamps paging against what is actually on screen.
    app.setViewport({
      pageSize: Math.max(3, model.view.list.height - 1),
      inspectorMax: model.scrollMax.inspector,
      systemMax: model.scrollMax.system,
      viewerMax: model.scrollMax.viewer,
    });
    if (clearNext) {
      clearScreen();
      clearNext = false;
    }
    write(composeFrame(model, { styler }));
  };

  function write(text) {
    process.stdout.write(text);
    lastWriteAt = Date.now();
  }

  const scheduleRepaint = () => {
    if (repaintTimer || finished) return;
    repaintTimer = setTimeout(() => {
      repaintTimer = null;
      if (!finished) render();
    }, PAINT_COALESCE_MS);
    repaintTimer.unref?.();
  };

  const cleanup = () => {
    clearInterval(tickTimer);
    if (repaintTimer) {
      clearTimeout(repaintTimer);
      repaintTimer = null;
    }
    unsubscribe?.();
    process.stdin.removeListener("data", onData);
    process.stdin.removeListener("end", onEnd);
    if (process.stdin.isTTY && typeof process.stdin.setRawMode === "function") {
      process.stdin.setRawMode(false);
    }
    process.stdin.pause();
    leaveScreen();
  };

  const finish = (code) => {
    if (finished) return;
    finished = true;
    cleanup();
    process.exitCode = code;
    process.exit(code);
  };

  const onData = (chunk) => {
    const decoded = decodeInput(chunk, pendingInput);
    pendingInput = decoded.pending;
    for (const intent of decoded.keys) {
      let result;
      try {
        result = app.dispatch(intent);
      } catch (error) {
        finishWithError(error);
        return;
      }
      if (result?.quit) {
        finish(0);
        return;
      }
      scheduleRepaint();
    }
  };

  const onEnd = () => finish(0);

  const onResize = () => {
    clearNext = true;
    if (repaintTimer) {
      clearTimeout(repaintTimer);
      repaintTimer = null;
    }
    render();
  };

  function finishWithError(error) {
    if (finished) return;
    process.stderr.write(`\nRE:Track TUI error: ${error?.message ?? error}\n`);
    finish(1);
  }

  enterScreen();
  process.stdin.setRawMode(true);
  process.stdin.resume();
  process.stdin.on("data", onData);
  process.stdin.on("end", onEnd);
  process.stdout.on("resize", onResize);
  process.on("SIGINT", () => finish(0));
  process.on("SIGTERM", () => finish(0));
  // Terminal window closed: leave the screen behind before exiting.
  process.on("SIGHUP", () => finish(0));
  // A terminal that disappears (closed window, killed wrapper) surfaces EIO on
  // the streams; the TUI must exit rather than linger without a screen.
  process.stdin.on("error", () => finish(0));
  process.stdout.on("error", () => finish(0));
  process.on("uncaughtException", finishWithError);
  process.on("unhandledRejection", finishWithError);

  const unsubscribe = app.subscribe(scheduleRepaint);

  // First frame paints the shell immediately; data arrives from the backend next.
  render();
  await app.load();
  render();

  // Repaint on tick only while something is visibly changing (operation
  // spinner/elapsed, notice countdown). Idle views repaint when data changes
  // or the user acts, which keeps terminal output quiet.
  const tickTimer = setInterval(() => {
    void app.tick(Date.now()).then(() => {
      const state = app.getState();
      if (state.operation || state.notice) {
        spinnerFrame += 1;
        render();
        return;
      }
      // Idle keepalive: repeat the (idempotent) cursor-hide sequence.
      if (Date.now() - lastWriteAt >= KEEPALIVE_MS) {
        write(`${ESC}?25l`);
      }
    });
  }, TICK_MS);
  tickTimer.unref?.();

  return null;
}

async function main() {
  const client = createBackendClient({ baseUrl: process.env.RETRACK_BACKEND_URL });
  if (!supportsTty) return runSnapshot(client);
  return runInteractive(client);
}

main()
  .then((code) => {
    if (code !== null && code !== undefined) process.exit(code);
  })
  .catch((error) => {
    if (error instanceof BackendUnreachableError || error instanceof BackendRequestError) {
      process.stderr.write(`${error.message}\n`);
    } else {
      process.stderr.write(`Error: ${error?.message ?? error}\n`);
    }
    if (supportsTty) leaveScreen();
    process.exit(1);
  });
