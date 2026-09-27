import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { readSelection, writeSelection, selectionPath, SelectionError } from "../selection.mjs";

function tempFile(name = "cli-state.json") {
  const dir = mkdtempSync(path.join(os.tmpdir(), "retrack-cli-selection-"));
  return { dir, file: path.join(dir, name) };
}

describe("cli selection: store", () => {
  it("returns null when nothing is stored", () => {
    const { dir, file } = tempFile();
    try {
      assert.equal(readSelection({ file }), null);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("round-trips a repository through the state file", () => {
    const { dir, file } = tempFile();
    try {
      const repository = { id: "repo-a", name: "alpha", path: "/work/alpha" };
      assert.equal(writeSelection(repository, { file }), file);
      assert.deepEqual(readSelection({ file }), repository);
      const raw = JSON.parse(readFileSync(file, "utf8"));
      assert.equal(raw.version, 1);
      assert.deepEqual(raw.repository, repository);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("honors the RETRACK_CLI_STATE override", () => {
    const override = "/tmp/custom/state.json";
    assert.equal(selectionPath({ env: { RETRACK_CLI_STATE: override } }), path.resolve(override));
    assert.match(selectionPath({ env: {} }), /\.retrack[/\\]cli-state\.json$/);
  });

  it("reports a corrupt state file instead of guessing", () => {
    const { dir, file } = tempFile();
    try {
      writeFileSync(file, "{not json", "utf8");
      assert.throws(
        () => readSelection({ file }),
        (error) => error instanceof SelectionError && /could not read the CLI selection/.test(error.message)
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("treats a state file without a repository path as no selection", () => {
    const { dir, file } = tempFile();
    try {
      writeFileSync(file, JSON.stringify({ version: 1, repository: { name: "alpha" } }), "utf8");
      assert.equal(readSelection({ file }), null);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
