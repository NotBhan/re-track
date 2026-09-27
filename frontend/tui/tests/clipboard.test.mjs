/**
 * Clipboard suite.
 *
 * Clipboard writing is a local capability with an honest verdict: a native
 * utility confirms by exit status, the OSC 52 escape can only be reported as
 * sent, and a session with no mechanism says so. The text handed over is always
 * the backend's markdown, byte for byte.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  canUseTerminalClipboard,
  clipboardCandidates,
  clipboardMessage,
  createClipboard,
  createClipboardWriter,
  osc52Sequence,
} from "../clipboard.mjs";

const NODE = process.execPath;
const succeed = { command: NODE, args: ["-e", "process.exit(0)"] };
const fail = (code = 3) => ({ command: NODE, args: ["-e", `process.exit(${code})`] });

describe("clipboard: candidate selection", () => {
  it("picks the platform's native writer without guessing", () => {
    assert.deepEqual(clipboardCandidates({ platform: "darwin", env: {} }), [{ command: "pbcopy", args: [] }]);
    assert.deepEqual(clipboardCandidates({ platform: "win32", env: {} }), [{ command: "clip.exe", args: [] }]);
  });

  it("uses the display server the session actually has", () => {
    assert.deepEqual(clipboardCandidates({ platform: "linux", env: { WAYLAND_DISPLAY: "wayland-0" } }), [
      { command: "wl-copy", args: [] },
    ]);

    assert.deepEqual(clipboardCandidates({ platform: "linux", env: { DISPLAY: ":0" } }), [
      { command: "xclip", args: ["-selection", "clipboard"] },
      { command: "xsel", args: ["--clipboard", "--input"] },
    ]);

    assert.deepEqual(clipboardCandidates({ platform: "linux", env: { WSL_DISTRO_NAME: "Ubuntu" } }), [
      { command: "clip.exe", args: [] },
    ]);

    assert.equal(clipboardCandidates({ platform: "linux", env: {} }).length, 0, "no display, no guess");
  });

  it("prefers the session's own display over the WSL bridge", () => {
    const commands = clipboardCandidates({
      platform: "linux",
      env: { WAYLAND_DISPLAY: "w", DISPLAY: ":0", WSL_INTEROP: "/run/WSL/1" },
    }).map((candidate) => candidate.command);
    assert.deepEqual(commands, ["wl-copy", "xclip", "xsel", "clip.exe"]);
  });
});

describe("clipboard: terminal fallback", () => {
  it("builds the OSC 52 sequence from the text's UTF-8 bytes", () => {
    const text = "# Auth ☕\n";
    const sequence = osc52Sequence(text);
    assert.equal(sequence, `\u001b]52;c;${Buffer.from(text, "utf8").toString("base64")}\u0007`);
    assert.ok(sequence.startsWith("\u001b]52;c;"));
    assert.ok(sequence.endsWith("\u0007"));
  });

  it("offers the terminal fallback only where it could work", () => {
    assert.equal(canUseTerminalClipboard({ stdout: { isTTY: true }, env: { TERM: "xterm-256color" } }), true);
    assert.equal(canUseTerminalClipboard({ stdout: { isTTY: false }, env: { TERM: "xterm-256color" } }), false);
    assert.equal(canUseTerminalClipboard({ stdout: { isTTY: true }, env: { TERM: "dumb" } }), false);
    assert.equal(canUseTerminalClipboard({ stdout: { isTTY: true }, env: {} }), false);
  });
});

describe("clipboard: writer verdicts", () => {
  it("confirms only a native utility that exited 0", async () => {
    const write = createClipboardWriter({
      candidates: [fail(), succeed],
      stdout: { isTTY: true, write() {} },
      env: { TERM: "xterm-256color" },
    });
    const result = await write("text");
    assert.deepEqual(result, { ok: true, mechanism: succeed.command, unconfirmed: false, reason: null });
  });

  it("hands over the markdown byte for byte, without escaping or stripping", async () => {
    const root = mkdtempSync(path.join(os.tmpdir(), "retrack-clipboard-"));
    const capture = path.join(root, "captured.md");
    const markdown = "# Auth ☕\n\n- `create_session`\n\u001b[31mraw escape stays\u001b[0m\n";
    const write = createClipboardWriter({
      candidates: [
        {
          command: NODE,
          args: ["-e", "require('node:fs').writeFileSync(process.argv[1], require('node:fs').readFileSync(0))", capture],
        },
      ],
      stdout: { isTTY: false, write() {} },
      env: {},
    });
    const result = await write(markdown);
    assert.equal(result.ok, true);
    assert.equal(readFileSync(capture, "utf8"), markdown);
  });

  it("sends through OSC 52 when no utility works, and reports it as unconfirmed", async () => {
    const written = [];
    const write = createClipboardWriter({
      candidates: [fail(9)],
      stdout: {
        isTTY: true,
        write: (chunk) => {
          written.push(String(chunk));
          return true;
        },
      },
      env: { TERM: "xterm-256color" },
    });
    const result = await write("# x");
    assert.equal(result.ok, true);
    assert.equal(result.mechanism, "osc52");
    assert.equal(result.unconfirmed, true);
    assert.equal(written.length, 1);
    assert.equal(written[0], osc52Sequence("# x"));
  });

  it("reports unavailable with the real reasons when nothing can copy", async () => {
    const write = createClipboardWriter({ candidates: [fail(7)], stdout: { isTTY: false, write() {} }, env: {} });
    const result = await write("x");
    assert.equal(result.ok, false);
    assert.equal(result.mechanism, "none");
    assert.match(result.reason, /exited with code 7/);
    assert.match(result.reason, /osc52: stdout is not a terminal/);
  });

  it("explains why the terminal escape would be ignored on a dumb terminal", async () => {
    const write = createClipboardWriter({ candidates: [], stdout: { isTTY: true, write() {} }, env: { TERM: "dumb" } });
    const result = await write("x");
    assert.equal(result.ok, false);
    assert.match(result.reason, /TERM=dumb/);
  });

  it("reports a missing utility by name", async () => {
    const write = createClipboardWriter({
      candidates: [{ command: "retrack-no-such-utility-3125", args: [] }],
      stdout: { isTTY: false, write() {} },
      env: {},
    });
    const result = await write("x");
    assert.equal(result.ok, false);
    assert.match(result.reason, /retrack-no-such-utility-3125/);
  });

  it("kills a utility that never completes and says so", async () => {
    const write = createClipboardWriter({
      candidates: [{ command: NODE, args: ["-e", "setTimeout(() => {}, 5000)"] }],
      stdout: { isTTY: false, write() {} },
      env: {},
      timeoutMs: 60,
    });
    const result = await write("x");
    assert.equal(result.ok, false);
    assert.match(result.reason, /no completion after 60 ms/);
  });
});

describe("clipboard: message vocabulary", () => {
  it("states a confirmed copy, an unconfirmed send and an unavailable session differently", () => {
    assert.equal(
      clipboardMessage({ ok: true, unconfirmed: false, mechanism: "wl-copy" }),
      "✓ copied the markdown to the clipboard (wl-copy)"
    );
    assert.equal(
      clipboardMessage({ ok: true, unconfirmed: true, mechanism: "osc52" }, "“Auth”"),
      "✓ sent “Auth” to the terminal clipboard (OSC 52) · the terminal does not confirm delivery"
    );
    assert.equal(clipboardMessage({ ok: false, reason: "no mechanism" }), "✗ clipboard unavailable · no mechanism");
  });

  it("wraps the writer with the same verdict and message the state layer shows", async () => {
    const copy = createClipboard({ candidates: [succeed], stdout: { isTTY: false }, env: {} });
    const result = await copy("# x", "the generated markdown");
    assert.equal(result.ok, true);
    assert.match(result.message, /✓ copied the generated markdown to the clipboard \(/);
  });
});
