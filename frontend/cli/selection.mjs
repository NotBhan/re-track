/**
 * The CLI's persisted repository selection.
 *
 * `retrack select <repository>` records the repository later commands operate
 * on. The selection lives beside the application's other canonical state
 * (`~/.retrack/`), never in the backend (which has no such concept) and never
 * in memory only. `--repo` overrides it for a single invocation; nothing else
 * changes it.
 *
 * The file is presentation-neutral: it stores the repository identity the
 * backend reported (id, name, path) and every command re-resolves it against
 * the backend before using it, so a stale selection is reported instead of
 * being trusted blindly.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

/** Raised when the selection file cannot be read or written. */
export class SelectionError extends Error {
  constructor(message) {
    super(message);
    this.name = "SelectionError";
  }
}

const FILE_NAME = "cli-state.json";

/** The selection file path: `RETRACK_CLI_STATE` override, else `~/.retrack/cli-state.json`. */
export function selectionPath({ env = process.env } = {}) {
  const override = env.RETRACK_CLI_STATE?.trim();
  if (override) return path.resolve(override);
  return path.join(os.homedir(), ".retrack", FILE_NAME);
}

/**
 * Read the persisted selection.
 *
 * @returns {{ id: string, name: string, path: string } | null}
 */
export function readSelection({ env = process.env, file = selectionPath({ env }) } = {}) {
  if (!existsSync(file)) return null;
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(file, "utf8"));
  } catch (error) {
    throw new SelectionError(`could not read the CLI selection at ${file}: ${error.message} (fix or delete the file)`);
  }
  const repository = parsed?.repository;
  if (!repository || typeof repository.path !== "string" || repository.path === "") return null;
  return {
    id: typeof repository.id === "string" ? repository.id : "",
    name: typeof repository.name === "string" ? repository.name : "",
    path: repository.path,
  };
}

/** Persist a repository as the CLI selection, returning the file it wrote. */
export function writeSelection(repository, { env = process.env, file = selectionPath({ env }) } = {}) {
  try {
    mkdirSync(path.dirname(file), { recursive: true });
    writeFileSync(file, `${JSON.stringify({ version: 1, repository }, null, 2)}\n`, "utf8");
  } catch (error) {
    throw new SelectionError(`could not persist the CLI selection at ${file}: ${error.message}`);
  }
  return file;
}
