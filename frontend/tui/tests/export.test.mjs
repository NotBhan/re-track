/**
 * Local package export suite.
 *
 * Export is a local capability: the markdown already loaded from the backend is
 * written to a user-chosen path, an existing file is never overwritten, and the
 * path that was actually written is reported back.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { freeExportPath, packageFileName, resolveExportPath, writeMarkdownExport } from "../export.mjs";

describe("export: path resolution and naming", () => {
  it("expands ~ and resolves relative paths against the working directory", () => {
    assert.equal(resolveExportPath("~/notes/a.md", { home: "/home/u", cwd: "/work" }), "/home/u/notes/a.md");
    assert.equal(resolveExportPath("out/a.md", { home: "/home/u", cwd: "/work" }), "/work/out/a.md");
    assert.equal(resolveExportPath("/abs/a.md", { home: "/home/u", cwd: "/work" }), "/abs/a.md");
    assert.throws(() => resolveExportPath("   "), /export path is required/);
  });

  it("derives a filesystem-safe, visible name from the package title", () => {
    assert.equal(packageFileName("Auth Context!"), "auth-context.md");
    assert.equal(packageFileName("  My Notes  "), "my-notes.md");
    assert.equal(packageFileName("..."), "context-package.md", "a dot-only title would hide the file");
    assert.equal(packageFileName(""), "context-package.md");
    assert.equal(packageFileName("", "fallback"), "fallback.md");
  });

  it("never overwrites: a numbered sibling is chosen instead", () => {
    const taken = new Set(["/d/a.md", "/d/a-2.md"]);
    assert.equal(freeExportPath("/d/a.md", { exists: (candidate) => taken.has(candidate) }), "/d/a-3.md");
    assert.equal(freeExportPath("/d/b.md", { exists: () => false }), "/d/b.md");
  });
});

describe("export: writing markdown", () => {
  it("writes the markdown as given and reports the path actually written", () => {
    const root = mkdtempSync(path.join(os.tmpdir(), "retrack-export-"));
    const target = path.join(root, "nested", "auth.md");

    const first = writeMarkdownExport({ path: target, content: "# Auth\n" });
    assert.equal(first.path, target, "missing parent directories are created");
    assert.equal(first.bytes, 7);
    assert.equal(readFileSync(target, "utf8"), "# Auth\n");

    writeFileSync(target, "existing content");
    const second = writeMarkdownExport({ path: target, content: "# Auth\n" });
    assert.equal(second.path, path.join(root, "nested", "auth-2.md"));
    assert.equal(readFileSync(target, "utf8"), "existing content", "the existing file is untouched");
    assert.equal(readFileSync(second.path, "utf8"), "# Auth\n");
  });
});
