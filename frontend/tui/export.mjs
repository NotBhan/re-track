/**
 * RE:Track TUI local package export.
 *
 * The backend exposes no context-package export endpoint; the desktop GUI only
 * copies the loaded markdown to the system clipboard. Exporting from the
 * terminal is therefore a clearly scoped *local* operation: the markdown that
 * was already loaded from the backend is written to a path the user chose, and
 * the path that was actually written is reported back.
 *
 * Nothing is generated, transformed, or sent anywhere, and an existing file is
 * never overwritten — a numbered sibling is used instead.
 */

import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const MAX_SUFFIX = 99;

/** Expand `~` and resolve relative paths against the working directory. */
export function resolveExportPath(target, { cwd = process.cwd(), home = os.homedir() } = {}) {
  const value = String(target ?? "").trim();
  if (!value) throw new Error("export path is required");
  const expanded = value === "~" || value.startsWith("~/") ? path.join(home, value.slice(1)) : value;
  return path.resolve(cwd, expanded);
}

/** Readable file name for a package title; used to prefill the export dialog. */
export function packageFileName(name, fallback = "context-package") {
  const slug = String(name ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    // Leading separators would hide the file (a dot) and a trailing separator
    // is invalid on Windows; an empty stem falls back to a readable name.
    .replace(/^[-._]+|[-._]+$/g, "")
    .slice(0, 60);
  return `${slug || fallback}.md`;
}

/** First free path: `name.md`, then `name-2.md`, … — never overwrites. */
export function freeExportPath(target, { exists = existsSync } = {}) {
  if (!exists(target)) return target;
  const directory = path.dirname(target);
  const extension = path.extname(target);
  const base = path.basename(target, extension);
  for (let index = 2; index <= MAX_SUFFIX; index += 1) {
    const candidate = path.join(directory, `${base}-${index}${extension}`);
    if (!exists(candidate)) return candidate;
  }
  throw new Error(`no free file name next to ${target}`);
}

/**
 * Write the loaded markdown to disk.
 * @returns {{ path: string, bytes: number }} the absolute path actually written.
 */
export function writeMarkdownExport({ path: target, content, cwd, home, exists } = {}) {
  const resolved = resolveExportPath(target, { cwd, home });
  const destination = freeExportPath(resolved, { exists });
  const markdown = String(content ?? "");
  try {
    mkdirSync(path.dirname(destination), { recursive: true });
    writeFileSync(destination, markdown, "utf8");
  } catch (error) {
    throw new Error(`export failed: ${error?.message ?? error}`);
  }
  return { path: destination, bytes: Buffer.byteLength(markdown, "utf8") };
}
