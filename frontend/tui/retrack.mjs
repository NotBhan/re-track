#!/usr/bin/env node
/**
 * RE:Track terminal user interface — entry point.
 *
 * Terminal lifecycle and I/O only: alternate-screen handling, raw mode, the
 * key event loop, resize handling, refresh scheduling and every exit path.
 * Application behaviour lives in state.mjs; frame composition in render.mjs;
 * backend discovery/spawn/readiness/shutdown in backend-lifecycle.mjs.
 *
 * This entry point must never import React, Tauri APIs, GUI components, or the
 * CLI, and must restore the terminal (cursor, alternate screen, raw mode) on
 * every exit path — including q, Ctrl+C, SIGINT/SIGTERM, stdin end and
 * uncaught exceptions.
 *
 * The backend is started on demand: `npm run tui` attaches to a backend that
 * is already reachable and only spawns one (using the desktop runtime's startup
 * contract) when there is none. A backend this invocation spawned is shut down
 * on exit; a pre-existing backend is never terminated.
 *
 * Usage:
 *   node frontend/tui/retrack.mjs
 *   npm run tui
 *   node frontend/tui/retrack.mjs | cat      # non-TTY: single snapshot line
 */

import { createBackendClient, BackendRequestError, BackendUnreachableError } from "../shared/backend-client.mjs";
import { ensureBackend } from "./backend-lifecycle.mjs";
import { packageFileName, writeMarkdownExport } from "./export.mjs";
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

/**
 * Transient status line for backend startup. On a terminal it rewrites one
 * inline line so the alternate screen opens onto a clean prompt; when stderr is
 * redirected it emits a plain line instead (stdout stays untouched so the
 * non-TTY snapshot contract remains exactly one line).
 */
function makeStartupReporter() {
  const inline = Boolean(process.stderr.isTTY);
  let lineOpen = false;
  return {
    show(message) {
      if (inline) {
        process.stderr.write(`\r${ESC}2KRE:Track · ${message}`);
        lineOpen = true;
      } else {
        process.stderr.write(`RE:Track · ${message}\n`);
      }
    },
    clear() {
      if (lineOpen) {
        process.stderr.write(`\r${ESC}2K`);
        lineOpen = false;
      }
    },
  };
}

/**
 * Local capabilities the state layer may invoke. Export writes the markdown
 * that was already loaded from the backend to a user-chosen path; there is no
 * backend export endpoint.
 */
function appOptions() {
  return {
    exportMarkdown: ({ target, markdown }) => writeMarkdownExport({ path: target, content: markdown }),
    exportFileName: (name) => packageFileName(name),
  };
}

async function runSnapshot(client) {
  const app = createApp({ client, ...appOptions() });
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

async function runInteractive(client, { onExit }) {
  const app = createApp({ client, ...appOptions() });
  const styler = createStyler({ enabled: !process.env.NO_COLOR });

  let finished = false;
  let repaintTimer = null;
  let tickTimer = null;
  let unsubscribe = null;
  let pendingInput = "";
  let spinnerFrame = 0;
  let clearNext = false;
  let lastWriteAt = Date.now();

  const render = () => {
    // A frame that arrives after teardown would paint over the restored screen.
    if (finished) return;
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
      // Focus rules depend on whether the inspector is a pane or a mode.
      sideBySide: model.layout.sideBySide,
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
    if (tickTimer !== null) {
      clearInterval(tickTimer);
      tickTimer = null;
    }
    if (repaintTimer) {
      clearTimeout(repaintTimer);
      repaintTimer = null;
    }
    unsubscribe?.();
    unsubscribe = null;
    process.stdin.removeListener("data", onData);
    process.stdin.removeListener("end", onEnd);
    if (process.stdin.isTTY && typeof process.stdin.setRawMode === "function") {
      // The terminal can already be gone (hangup); backend shutdown must still run.
      try {
        process.stdin.setRawMode(false);
      } catch {
        // Nothing left to restore.
      }
    }
    process.stdin.pause();
    try {
      leaveScreen();
    } catch {
      // The screen is already gone; the process still has to shut down the backend.
    }
  };

  const finish = (code) => {
    if (finished) return;
    finished = true;
    // Teardown runs even if the terminal is already unusable: releasing the
    // owned backend is what must never be skipped.
    try {
      cleanup();
    } catch {
      // Nothing left to restore.
    }
    void onExit(code);
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
    process.stderr.write(`\nRE:Track TUI error: ${error?.message ?? error}\n`);
    // A cleanup path is already running; it owns the exit.
    if (finished) return;
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

  unsubscribe = app.subscribe(scheduleRepaint);

  // First frame paints the shell immediately; data arrives from the backend next.
  render();
  await app.load();
  render();

  // Repaint on tick only while something is visibly changing (operation
  // spinner/elapsed, notice countdown). Idle views repaint when data changes
  // or the user acts, which keeps terminal output quiet.
  tickTimer = setInterval(() => {
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

let activeBackend = null;

async function main() {
  // Signals during startup abort the readiness wait so an owned child is reaped
  // before the failure is reported.
  const startup = new AbortController();
  const abortStartup = () => startup.abort();
  process.on("SIGINT", abortStartup);
  process.on("SIGTERM", abortStartup);
  process.on("SIGHUP", abortStartup);

  const reporter = makeStartupReporter();
  let backend;
  try {
    backend = await ensureBackend({
      baseUrl: process.env.RETRACK_BACKEND_URL,
      signal: startup.signal,
      onStatus: (message) => reporter.show(message),
    });
  } catch (error) {
    reporter.clear();
    const interrupted = startup.signal.aborted;
    process.stderr.write(
      interrupted
        ? "RE:Track · backend startup interrupted\n"
        : `RE:Track · backend startup failed: ${error?.message ?? error}\n`
    );
    return interrupted ? 130 : 1;
  } finally {
    process.off("SIGINT", abortStartup);
    process.off("SIGTERM", abortStartup);
    process.off("SIGHUP", abortStartup);
  }

  reporter.clear();
  activeBackend = backend;

  const client = createBackendClient({ baseUrl: backend.baseUrl });

  // Shutdown path shared by q, Ctrl+C, signals, EOF and uncaught errors:
  // stop only the backend this invocation owns, then exit.
  const shutdown = async (code) => {
    try {
      await backend.stop();
    } catch {
      // stop() is bounded internally; the process still has to exit.
    }
    process.exit(code);
  };

  if (!supportsTty) {
    const onSignal = (code) => () => void shutdown(code);
    const onSigint = onSignal(130);
    const onSigterm = onSignal(143);
    const onSighup = onSignal(129);
    process.on("SIGINT", onSigint);
    process.on("SIGTERM", onSigterm);
    process.on("SIGHUP", onSighup);
    try {
      return await runSnapshot(client);
    } finally {
      process.off("SIGINT", onSigint);
      process.off("SIGTERM", onSigterm);
      process.off("SIGHUP", onSighup);
      // stdout is closed; nothing that outlives this process may stay running.
      await backend.stop();
    }
  }

  try {
    return await runInteractive(client, { onExit: shutdown });
  } catch (error) {
    // Startup of the interface itself failed before the exit paths were armed.
    await backend.stop();
    throw error;
  }
}

main()
  .then((code) => {
    if (code !== null && code !== undefined) process.exit(code);
  })
  .catch(async (error) => {
    if (error instanceof BackendUnreachableError || error instanceof BackendRequestError) {
      process.stderr.write(`${error.message}\n`);
    } else {
      process.stderr.write(`Error: ${error?.message ?? error}\n`);
    }
    try {
      await activeBackend?.stop();
    } catch {
      // The failure that reached this point is what must be reported.
    }
    if (supportsTty) {
      try {
        leaveScreen();
      } catch {
        // The terminal is already gone.
      }
    }
    process.exit(1);
  });
