import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { applyEdit, decodeChunk, stripMouseSequences } from "../keys.mjs";

const names = (chunk) => decodeChunk(chunk).keys.map((key) => key.name);

describe("key decoding", () => {
  it("decodes arrow keys in both CSI and SS3 forms", () => {
    assert.deepEqual(names("\u001b[A"), ["up"]);
    assert.deepEqual(names("\u001b[B"), ["down"]);
    assert.deepEqual(names("\u001b[C"), ["right"]);
    assert.deepEqual(names("\u001b[D"), ["left"]);
    assert.deepEqual(names("\u001bOA"), ["up"]);
    assert.deepEqual(names("\u001bOD"), ["left"]);
  });

  it("decodes paging and jump keys", () => {
    assert.deepEqual(names("\u001b[5~"), ["pageUp"]);
    assert.deepEqual(names("\u001b[6~"), ["pageDown"]);
    assert.deepEqual(names("\u001b[H"), ["home"]);
    assert.deepEqual(names("\u001b[F"), ["end"]);
    assert.deepEqual(names("\u001b[1~"), ["home"]);
    assert.deepEqual(names("\u001b[4~"), ["end"]);
  });

  it("decodes editing keys", () => {
    assert.deepEqual(names("\r"), ["enter"]);
    assert.deepEqual(names("\n"), ["enter"]);
    assert.deepEqual(names("\t"), ["tab"]);
    assert.deepEqual(names("\u007f"), ["backspace"]);
    assert.deepEqual(names("\b"), ["backspace"]);
    assert.deepEqual(names("\u001b[3~"), ["delete"]);
    assert.deepEqual(names("\u001b"), ["escape"]);
  });

  it("decodes ctrl combinations and printable characters", () => {
    assert.deepEqual(decodeChunk("\u0003").keys, [{ name: "ctrl", char: "c" }]);
    assert.deepEqual(decodeChunk("\u0015").keys, [{ name: "ctrl", char: "u" }]);
    assert.deepEqual(decodeChunk("\u0017").keys, [{ name: "ctrl", char: "w" }]);
    assert.deepEqual(decodeChunk("q").keys, [{ name: "char", char: "q" }]);
    assert.deepEqual(decodeChunk(" ").keys, [{ name: "space", char: " " }]);
  });

  it("returns multiple intents for a pasted chunk", () => {
    assert.deepEqual(names("abc"), ["char", "char", "char"]);
    assert.deepEqual(decodeChunk("abc").keys.map((key) => key.char), ["a", "b", "c"]);
  });

  it("holds a partial escape sequence until the next chunk", () => {
    const first = decodeChunk("\u001b[");
    assert.deepEqual(first.keys, []);
    assert.equal(first.pending, "\u001b[");
    const second = decodeChunk("A", first.pending);
    assert.deepEqual(second.keys, [{ name: "up" }]);
    assert.equal(second.pending, "");
  });

  it("ignores mouse and bracketed-paste sequences", () => {
    assert.deepEqual(names("\u001b[<0;12;5M"), []);
    assert.deepEqual(names("\u001b[200~"), []);
    assert.deepEqual(names("\u001b[Mabc"), []);
    assert.equal(stripMouseSequences("ab\u001b[<0;1;1Mc"), "abc");
  });

  it("reports unknown escape sequences without throwing", () => {
    assert.deepEqual(names("\u001b[99X"), ["unknown"]);
  });
});

describe("line editor", () => {
  const state = (value, cursor = value.length) => ({ value, cursor });

  it("inserts text at the cursor", () => {
    assert.deepEqual(applyEdit(state("ab", 1), { type: "insert", text: "XY" }), { value: "aXYb", cursor: 3 });
  });

  it("deletes before the cursor", () => {
    assert.deepEqual(applyEdit(state("abc", 2), { type: "backspace" }), { value: "ac", cursor: 1 });
    assert.deepEqual(applyEdit(state("abc", 0), { type: "backspace" }), { value: "abc", cursor: 0 });
  });

  it("deletes the word before the cursor", () => {
    assert.deepEqual(applyEdit(state("foo bar baz", 11), { type: "deleteWord" }), { value: "foo bar ", cursor: 8 });
    assert.deepEqual(applyEdit(state("foo bar", 7), { type: "deleteWord" }), { value: "foo ", cursor: 4 });
  });

  it("kills to the end and clears", () => {
    assert.deepEqual(applyEdit(state("abcdef", 3), { type: "killToEnd" }), { value: "abc", cursor: 3 });
    assert.deepEqual(applyEdit(state("abcdef", 3), { type: "clear" }), { value: "", cursor: 0 });
  });

  it("moves the cursor and clamps at the boundaries", () => {
    assert.deepEqual(applyEdit(state("ab", 0), { type: "left" }), { value: "ab", cursor: 0 });
    assert.deepEqual(applyEdit(state("ab", 2), { type: "right" }), { value: "ab", cursor: 2 });
    assert.deepEqual(applyEdit(state("ab", 1), { type: "home" }), { value: "ab", cursor: 0 });
    assert.deepEqual(applyEdit(state("ab", 0), { type: "end" }), { value: "ab", cursor: 2 });
  });

  it("never mutates the source state", () => {
    const before = state("abc", 3);
    applyEdit(before, { type: "backspace" });
    assert.deepEqual(before, { value: "abc", cursor: 3 });
  });
});
