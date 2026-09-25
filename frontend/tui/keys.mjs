/* eslint-disable no-control-regex -- decoding raw terminal control sequences is this module's purpose */
/**
 * RE:Track TUI input decoding and line editing.
 *
 * Pure functions only: no terminal writes, no state. The entry point feeds raw
 * stdin chunks in and dispatches the decoded intents; overlays and the inline
 * filter share the same line-editor operations.
 */

const CSI_ARROWS = { A: "up", B: "down", C: "right", D: "left", H: "home", F: "end" };
const CSI_TILDES = { "1": "home", "3": "delete", "4": "end", "5": "pageUp", "6": "pageDown", "7": "home", "8": "end" };

// SGR mouse (ESC[<b;x;yM), X10 mouse (ESC[M + 3 bytes) and bracketed paste markers.
const MOUSE_SGR = /^\u001b\[<\d+;\d+;\d+[Mm]/;
const MOUSE_X10 = /^\u001b\[M[\s\S]{3}/;
const PASTE_MARKER = /^\u001b\[(200|201)~/;

export function stripMouseSequences(input) {
  return String(input)
    .replace(/\u001b\[<\d+;\d+;\d+[Mm]/g, "")
    .replace(/\u001b\[M[\s\S]{3}/g, "")
    .replace(/\u001b\[(200|201)~/g, "");
}

function controlKey(code) {
  if (code === 0x03) return { name: "ctrl", char: "c" };
  if (code === 0x09) return { name: "tab" };
  if (code === 0x0d || code === 0x0a) return { name: "enter" };
  if (code === 0x7f || code === 0x08) return { name: "backspace" };
  if (code === 0x1b) return { name: "escape" };
  if (code >= 0x01 && code <= 0x1a) return { name: "ctrl", char: String.fromCharCode(96 + code) };
  return null;
}

/**
 * Decode one stdin chunk into intents.
 *
 * `pending` carries a partial escape sequence across chunks; the caller must
 * feed the returned `pending` back with the next chunk. A lone ESC is treated
 * as the Escape key (a split sequence is held instead, because it always
 * continues with `[` or `O` in the next chunk).
 */
export function decodeChunk(chunk, pending = "") {
  const buffer = pending + String(chunk ?? "");
  const keys = [];
  let index = 0;

  while (index < buffer.length) {
    const rest = buffer.slice(index);

    if (rest === "\x1b") {
      keys.push({ name: "escape" });
      index += 1;
      continue;
    }

    if (rest.startsWith("\x1b")) {
      const mouseSgr = rest.match(MOUSE_SGR);
      if (mouseSgr) {
        index += mouseSgr[0].length;
        continue;
      }
      const mouseX10 = rest.match(MOUSE_X10);
      if (mouseX10) {
        index += mouseX10[0].length;
        continue;
      }
      const paste = rest.match(PASTE_MARKER);
      if (paste) {
        index += paste[0].length;
        continue;
      }

      const csi = rest.match(/^\u001b\[([0-9;]*)([A-Za-z~])/);
      if (csi) {
        const [, params, final] = csi;
        index += csi[0].length;
        if (final === "~") {
          const name = CSI_TILDES[params.split(";")[0]];
          keys.push(name ? { name } : { name: "unknown" });
          continue;
        }
        if (final === "Z") {
          keys.push({ name: "tab", shift: true });
          continue;
        }
        const name = CSI_ARROWS[final];
        keys.push(name ? { name } : { name: "unknown" });
        continue;
      }

      const ss3 = rest.match(/^\u001bO([A-Za-z])/);
      if (ss3) {
        index += ss3[0].length;
        const name = CSI_ARROWS[ss3[1]];
        keys.push(name ? { name } : { name: "unknown" });
        continue;
      }

      if (/^\u001b\[[0-9;]*$/.test(rest) || /^\u001bO$/.test(rest)) {
        // Partial sequence: hold it until the next chunk arrives.
        return { keys, pending: rest };
      }

      keys.push({ name: "unknown" });
      index += 1;
      continue;
    }

    const code = rest.codePointAt(0);
    const control = controlKey(code);
    if (control) {
      keys.push(control);
      index += 1;
      continue;
    }

    const char = String.fromCodePoint(code);
    index += char.length;
    keys.push(char === " " ? { name: "space", char } : { name: "char", char });
  }

  return { keys, pending: "" };
}

/* ------------------------------------------------------------------ *
 * Line editor
 * ------------------------------------------------------------------ */

export function insertAt(state, text) {
  const value = state.value.slice(0, state.cursor) + text + state.value.slice(state.cursor);
  return { value, cursor: state.cursor + text.length };
}

export function deleteBefore(state) {
  if (state.cursor === 0) return { value: state.value, cursor: 0 };
  return {
    value: state.value.slice(0, state.cursor - 1) + state.value.slice(state.cursor),
    cursor: state.cursor - 1,
  };
}

export function deleteWordBefore(state) {
  let index = state.cursor;
  while (index > 0 && state.value[index - 1] === " ") index -= 1;
  while (index > 0 && state.value[index - 1] !== " ") index -= 1;
  return { value: state.value.slice(0, index) + state.value.slice(state.cursor), cursor: index };
}

export function killToEnd(state) {
  return { value: state.value.slice(0, state.cursor), cursor: state.cursor };
}

/** Apply a named edit to `{value, cursor}`; unknown actions are a no-op. */
export function applyEdit(state, action) {
  const value = state?.value ?? "";
  const cursor = clampCursor(state?.cursor ?? value.length, value.length);
  const current = { value, cursor };
  switch (action?.type) {
    case "insert":
      return insertAt(current, String(action.text ?? ""));
    case "backspace":
      return deleteBefore(current);
    case "deleteWord":
      return deleteWordBefore(current);
    case "killToEnd":
      return killToEnd(current);
    case "clear":
      return { value: "", cursor: 0 };
    case "home":
      return { value, cursor: 0 };
    case "end":
      return { value, cursor: value.length };
    case "left":
      return { value, cursor: Math.max(0, cursor - 1) };
    case "right":
      return { value, cursor: Math.min(value.length, cursor + 1) };
    default:
      return current;
  }
}

function clampCursor(cursor, length) {
  if (!Number.isFinite(cursor)) return length;
  return Math.min(Math.max(0, cursor), length);
}
