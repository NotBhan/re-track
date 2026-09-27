/**
 * RE:Track CLI argument parsing and value normalization.
 *
 * Pure functions only: no I/O, no backend access, no rendering. Every rejected
 * input raises `UsageError`, which the entry point maps to exit code 2.
 */

/** A malformed command line. Maps to exit code 2. */
export class UsageError extends Error {
  constructor(message) {
    super(message);
    this.name = "UsageError";
    this.exitCode = 2;
  }
}

const BOOLEAN_OPTIONS = new Set([
  "--json",
  "--help",
  "--yes",
  "--force",
  "--graph",
  "--no-graph",
  "--no-start",
]);

const VALUE_OPTIONS = new Set(["--url", "--repo", "--dataset", "--budget", "--output"]);

/** camelCase an option name: --no-graph → noGraph, --json → json. */
function optionKey(name) {
  const [first, ...rest] = name.replace(/^--/, "").split("-");
  return first + rest.map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("");
}

/**
 * Parse argv into booleans, value options and positionals.
 *
 * Long options only (`-h` is the one short alias), `--name value` and
 * `--name=value` both supported, `--` ends option parsing. Unknown options are
 * rejected here; whether an option is valid for a command is checked by the
 * command table, so a typo never silently falls through.
 *
 * @param {string[]} argv
 * @returns {{ flags: Record<string, boolean>, options: Record<string, string>, positionals: string[], used: string[] }}
 */
export function parseArgv(argv) {
  const flags = {};
  const options = {};
  const positionals = [];
  const used = [];

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];

    if (token === "--") {
      positionals.push(...argv.slice(index + 1));
      break;
    }
    if (token === "-h") {
      flags.help = true;
      used.push("--help");
      continue;
    }
    if (token.length > 1 && token.startsWith("-") && !token.startsWith("--")) {
      throw new UsageError(`unknown option: ${token} (-h is the only short option)`);
    }
    if (!token.startsWith("--")) {
      positionals.push(token);
      continue;
    }

    const equals = token.indexOf("=");
    const name = equals === -1 ? token : token.slice(0, equals);
    const inline = equals === -1 ? undefined : token.slice(equals + 1);

    if (BOOLEAN_OPTIONS.has(name)) {
      if (inline !== undefined) throw new UsageError(`${name} does not take a value`);
      if (name === "--graph") flags.graph = true;
      else if (name === "--no-graph") flags.graph = false;
      else flags[optionKey(name)] = true;
      used.push(name);
      continue;
    }

    if (VALUE_OPTIONS.has(name)) {
      const value = inline !== undefined ? inline : argv[index + 1];
      if (value === undefined) throw new UsageError(`${name} requires a value`);
      if (inline === undefined) index += 1;
      options[optionKey(name)] = value;
      used.push(name);
      continue;
    }

    throw new UsageError(`unknown option: ${name}`);
  }

  return { flags, options, positionals, used };
}

/**
 * Normalize a human token budget into the integer the backend accepts.
 *
 * Accepts `4k` / `8k` / `16k` / `32k` (k = 1024, case-insensitive) and plain
 * integers. The backend contract is `max_tokens >= 100` with no upper bound, so
 * nothing below 100 is accepted and no maximum is invented here.
 */
export function parseTokenBudget(value) {
  const raw = String(value ?? "").trim();
  const match = /^([0-9]+)([kK])?$/.exec(raw);
  if (!match) {
    throw new UsageError(`invalid token budget "${value}": use a token count (for example 4k, 8k, 16k) or an integer >= 100`);
  }
  const amount = Number.parseInt(match[1], 10) * (match[2] ? 1024 : 1);
  if (amount < 100) {
    throw new UsageError(`invalid token budget "${value}": the backend requires at least 100 tokens`);
  }
  return amount;
}

/** Reject options a command does not accept (globals are handled by the caller). */
export function assertOptions(used, allowed, command) {
  const allowedSet = new Set(allowed);
  for (const name of used) {
    if (allowedSet.has(name)) continue;
    throw new UsageError(`${name} is not valid for "${command}"`);
  }
}
