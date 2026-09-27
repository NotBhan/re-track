/**
 * RE:Track TUI clipboard adapter.
 *
 * Terminal-native and dependency-free. The generated markdown is handed over
 * verbatim: no escaping, no wrapping, no styling, no model round-trip.
 *
 * Mechanisms are tried in order, and the result says which one was used:
 *
 * 1. A native clipboard utility for the session's display server/platform
 *    (`wl-copy`, `xclip`, `xsel`, `pbcopy`, `clip.exe`). Its exit status is a
 *    real verdict, so this is the only mechanism reported as a confirmed copy.
 * 2. The OSC 52 terminal clipboard escape, when stdout is a terminal that can
 *    plausibly interpret it. A terminal application cannot observe whether the
 *    terminal accepted it, so the result is reported as *sent*, never as
 *    confirmed — RE:Track never claims a copy it could not verify.
 * 3. Otherwise an explicit unavailable state carrying the reason.
 *
 * This module is the only TUI module allowed to spawn a child process besides
 * `backend-lifecycle.mjs`; it never writes to the screen and holds no state.
 */

import { spawn } from "node:child_process";

const COMMAND_TIMEOUT_MS = 3000;
const STDERR_LIMIT = 400;

/**
 * Clipboard utilities that could serve this session, in priority order.
 * Exported for tests and for diagnostics: nothing is probed by guessing.
 */
export function clipboardCandidates(options = {}) {
  const platform = options.platform ?? process.platform;
  const env = options.env ?? process.env;

  if (platform === "darwin") return [{ command: "pbcopy", args: [] }];
  if (platform === "win32") return [{ command: "clip.exe", args: [] }];

  const candidates = [];
  if (env.WAYLAND_DISPLAY) candidates.push({ command: "wl-copy", args: [] });
  if (env.DISPLAY) {
    candidates.push({ command: "xclip", args: ["-selection", "clipboard"] });
    candidates.push({ command: "xsel", args: ["--clipboard", "--input"] });
  }
  // WSL has no X/Wayland display but ships the Windows clipboard bridge.
  if (env.WSL_DISTRO_NAME || env.WSL_INTEROP) candidates.push({ command: "clip.exe", args: [] });
  return candidates;
}

/** The OSC 52 sequence carrying `text` as the system clipboard selection. */
export function osc52Sequence(text) {
  const payload = Buffer.from(String(text ?? ""), "utf8").toString("base64");
  return `\u001b]52;c;${payload}\u0007`;
}

/**
 * Whether the terminal layer can be asked to hold the clipboard. This is a
 * capability judgement, not a confirmation: OSC 52 is a request.
 */
export function canUseTerminalClipboard(options = {}) {
  const stdout = options.stdout ?? process.stdout;
  const env = options.env ?? process.env;
  if (!stdout?.isTTY) return false;
  const term = String(env.TERM ?? "").trim();
  return term !== "" && term !== "dumb";
}

/** Run one utility with `text` on stdin; resolve with its verdict. */
function runCommand({ command, args }, text, timeoutMs) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(command, args, { stdio: ["pipe", "ignore", "pipe"] });
    } catch (error) {
      resolve({ ok: false, reason: `${command}: ${error?.message ?? error}` });
      return;
    }

    let stderr = "";
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try {
        child.kill("SIGKILL");
      } catch {
        // The process is already gone.
      }
      finish({ ok: false, reason: `${command}: no completion after ${timeoutMs} ms` });
    }, timeoutMs);
    timer.unref?.();

    child.on("error", (error) => finish({ ok: false, reason: `${command}: ${error?.message ?? error}` }));
    child.stderr?.on("data", (chunk) => {
      if (stderr.length < STDERR_LIMIT) stderr += String(chunk);
    });
    child.on("close", (code) => {
      finish(
        code === 0
          ? { ok: true }
          : { ok: false, reason: `${command} exited with code ${code}${stderr.trim() ? `: ${stderr.trim()}` : ""}` }
      );
    });
    child.stdin?.on("error", () => {
      // A utility that closes stdin early reports through its exit code.
    });
    child.stdin?.end(String(text ?? ""));
  });
}

/**
 * Build the clipboard writer the entry point injects into the state layer.
 *
 * @param {{stdout?: NodeJS.WriteStream, env?: NodeJS.ProcessEnv, platform?: string,
 *          candidates?: Array<{command: string, args: string[]}>, timeoutMs?: number}} [options]
 * @returns {(text: string) => Promise<{ok: boolean, mechanism: string, unconfirmed: boolean, reason: string|null}>}
 */
export function createClipboardWriter(options = {}) {
  const stdout = options.stdout ?? process.stdout;
  const env = options.env ?? process.env;
  const platform = options.platform ?? process.platform;
  const timeoutMs = options.timeoutMs ?? COMMAND_TIMEOUT_MS;
  const candidates = options.candidates ?? clipboardCandidates({ platform, env });

  return async function copy(text) {
    const payload = String(text ?? "");
    const failures = [];

    for (const candidate of candidates) {
      const result = await runCommand(candidate, payload, timeoutMs);
      if (result.ok) return { ok: true, mechanism: candidate.command, unconfirmed: false, reason: null };
      failures.push(result.reason);
    }

    if (canUseTerminalClipboard({ stdout, env })) {
      try {
        stdout.write(osc52Sequence(payload));
        return { ok: true, mechanism: "osc52", unconfirmed: true, reason: null };
      } catch (error) {
        failures.push(`osc52: ${error?.message ?? error}`);
      }
    } else if (stdout?.isTTY) {
      failures.push("osc52: terminal reports TERM=dumb, so the clipboard escape would be ignored");
    } else {
      failures.push("osc52: stdout is not a terminal");
    }

    return {
      ok: false,
      mechanism: "none",
      unconfirmed: false,
      reason: failures.length > 0 ? failures.join(" · ") : "no clipboard mechanism is available",
    };
  };
}

/** One truthful sentence for the UI, given a copy result. */
export function clipboardMessage(result, label = "the markdown") {
  if (result?.ok) {
    return result.unconfirmed
      ? `✓ sent ${label} to the terminal clipboard (OSC 52) · the terminal does not confirm delivery`
      : `✓ copied ${label} to the clipboard (${result.mechanism})`;
  }
  return `✗ clipboard unavailable · ${result?.reason ?? "no mechanism available"}`;
}

/**
 * The copy function the entry point injects into the state layer:
 * `(text, label) => Promise<{ok, mechanism, unconfirmed, reason, message}>`.
 * The state layer never needs to know which mechanism ran, only whether it did.
 */
export function createClipboard(options = {}) {
  const write = createClipboardWriter(options);
  return async function copy(text, label = "the markdown") {
    const result = await write(text);
    return { ...result, message: clipboardMessage(result, label) };
  };
}
