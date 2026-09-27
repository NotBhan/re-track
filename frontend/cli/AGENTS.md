# Purpose

Owns the RE:Track command-line interface: an explicit, scriptable command surface over the shared backend contract.

The CLI is **not** an interactive interface. The TUI is the interactive terminal application; the CLI is a set of commands with predictable arguments, deterministic output, machine-readable mode, meaningful exit codes and shell composability. It never prompts, never renders menus, never uses the alternate screen, and never copies the TUI interaction model.

---

# Ownership

- `retrack.mjs` — entry point: routing, command implementations, rendering, exit codes.
- `args.mjs` — argv parsing, option validation and token-budget normalization (pure functions only).
- `help.mjs` — the command tree and per-command reference; one data table drives `help` and `<command> --help`.
- `selection.mjs` — the persisted default repository (`~/.retrack/cli-state.json`, `RETRACK_CLI_STATE` override).
- `backend-lifecycle.mjs` — attach / start / readiness / ownership / shutdown for the backend process.
- `tests/` — `node:test` suites: unit (args, selection, lifecycle with injected fakes), integration against a stub HTTP backend, and real-process lifecycle runs against a fake backend directory.

---

# Command model

```
retrack <command> [arguments] [options]
```

| Command | Purpose |
|---|---|
| `help [command]` | Command tree, or one command's arguments/options/examples |
| `health` | Is RE:Track operational? (backend, provider, engine, concurrency, hardware) |
| `status` | What is RE:Track configured with? (+ the CLI's selected repository) |
| `list repositories` | Tracked repositories (name, path, status, files, languages, indexed time) |
| `list packages` | Saved context packages (with the ids later commands need) |
| `select [<path\|name>]` | Set (or report) the CLI's default repository — persistent |
| `index [<path>]` | Index a repository (registers and scans an untracked path first) |
| `scan [<path>]` | Refresh languages/frameworks/size without indexing |
| `construct "<prompt>" [<budget>]` | Generate a context package for a task |
| `show package <id>` | Print a stored package and its Markdown |
| `append package <id> "<text>"` | Append a task/note to a stored package (the note becomes its task **and** extends the stored Markdown; never regenerates) |
| `delete package <id> --yes` | Delete a stored package |
| `export package <id> <path>` | Write the stored Markdown to a file |
| `resynthesize package <id> --yes` | Regenerate a stored package in place |
| `delete repository <path\|name> --yes` | Delete a repository and its indexed memory |
| `settings` | Persisted application configuration (read-only) |
| `provider [models]` | Active provider status, or the models its endpoint offers (read-only) |
| `memory` | Memory layer statistics |
| `benchmark` | Run the deterministic benchmark suite |

Canonical examples:

```bash
retrack help
retrack list repositories
retrack select ~/Projects/my-project
retrack index
retrack construct "Explain how authentication works" 4k
retrack construct "Trace the evidence gate" --repo re-track --json | jq .evidence_state
retrack export package 5f3a9c2b1d ./context.md
retrack append package 5f3a9c2b1d "Include deployment considerations"
retrack resynthesize package 5f3a9c2b1d --yes
```

---

# Selected-repository semantics

- `retrack select <path|name>` resolves the target against the backend's repository catalog (path first, then exact name; an ambiguous name is an error) and persists `{ id, name, path }` at `~/.retrack/cli-state.json` — beside the application's other canonical state, never in the backend (which has no such concept) and never only in memory.
- Commands that need a repository resolve it as: **positional argument → `--repo` → persisted selection**. An explicit argument or `--repo` is command-local and never changes the stored selection.
- The selection is re-resolved against the backend on every use, so a stale selection is reported, not trusted.
- `retrack select` with no argument reports the stored selection and needs no backend.
- `RETRACK_CLI_STATE` overrides the state file path (portable installs and tests).

---

# Token budgets

`construct` and `resynthesize` accept `4k` / `8k` / `16k` / `32k` (`k` = 1024, case-insensitive) or a plain integer. The backend contract is `max_tokens >= 100` with no upper bound, so nothing below 100 is accepted and no maximum is invented at the CLI boundary. The default is `4k` (4096). The budget may be positional (`construct "..." 4k`) or a flag (`--budget 4k`) — never both.

---

Every command answers `retrack <command> --help` (and `-h`) with its own reference: the help key is resolved from the command path before argument validation, so `retrack construct --help` and `retrack delete --help` work with no arguments, no backend, no selection and no filesystem access. Grouped verbs (`list`, `delete`) have their own reference page and their concrete forms (`list packages`, `delete repository`) resolve to theirs.

---

# Output contract

- Default: human-readable on stdout (tables and small metadata headers). Terminal width never changes the output.
- `--json`: the raw backend payload, unmodified — valid JSON, no ANSI escapes, no progress noise, safe to pipe into `jq`. `--json` and `--output` are mutually exclusive.
- Progress and diagnostics go to **stderr** only. Indexing progress is a single updating line derived from the backend's own progress record (`phase N/M · stage · elapsed`), shown only on an interactive stderr and suppressed entirely under `--json`. No percentages are fabricated.
- `construct` prints a small header (`repository`, `budget`, `evidence`, `tokens`) followed by the generated Markdown **exactly as returned**; `--output <path>` writes only the Markdown byte for byte and reports the path and size. `export package` does the same for stored Markdown and refuses to overwrite unless `--force` is given.

---

# Exit codes and errors

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Command failed: backend unreachable/unstartable, HTTP error, repository/package not found, failed generation, refused overwrite |
| `2` | Usage error: unknown command/option, bad arguments, invalid budget, missing `--yes` |

Errors are concise and actionable on stderr (`repository not found: …`, `package not found: …`, `backend unavailable at …`) with no tracebacks by default. Failures are never converted into empty results.

---

# Backend lifecycle

A command works without a manually started backend:

- A backend already answering `--url` (default `$RETRACK_BACKEND_URL`, else `http://127.0.0.1:8765`) is **attached** to and never signalled.
- Otherwise one is started with the desktop runtime's contract (backend directory resolution, `.venv` interpreter, `python -m uvicorn app.server:app`, the desktop environment, `$TMPDIR/retrack-backend.log`, `RETRACK_PARENT_PID` watchdog, bounded `/health` readiness) and **terminated on exit only if this invocation started it** (SIGTERM to the process group, bounded SIGKILL fallback). A startup failure reaps the child and reports the real error with the log tail.
- `--no-start` disables startup: the command fails fast when no backend is reachable.
- `RETRACK_BACKEND_DIR` overrides the backend directory; `RETRACK_BACKEND_STARTUP_TIMEOUT_MS` bounds readiness.

`backend-lifecycle.mjs` is a deliberate port of the TUI's module (same contract, trimmed to command needs): the interface trees must not import one another (`frontend/AGENTS.md`) and the TUI is frozen, so the contract — not the file — is shared.

---

# Local contracts

1. Depends on `../shared/backend-client.mjs` and its own modules only. Never imports `../gui/**` or `../tui/**`.
2. Zero runtime dependencies — plain Node ESM.
3. All backend interaction goes through the shared client; no HTTP calls are inlined here.
4. `--json` emits the raw backend payload unmodified.
5. Output never invents values for fields the backend did not return; missing data is stated as missing.
6. No interactive prompts. Destructive commands (`delete`, `resynthesize`) require `--yes`; the CLI is safe to run from scripts.
7. The CLI never creates a second package, never regenerates as part of `append`, and never overwrites a file without `--force`.
8. `append package` sends the supplied note as both the append's task and its Markdown, because the backend contract replaces the task metadata and extends the stored content from those two fields; an append never invokes a model.

---

# Limitations (deliberate)

- **No package creation**: saving a generated package stays in the TUI/GUI (`construct` output can be written to a file with `--output`).
- **No clipboard commands**: `construct --copy` / `copy package` are not implemented; the TUI owns clipboard integration.
- **No configuration mutations**: `settings`, `provider` and `provider models` are read-only; provider switching/resets stay in the TUI/GUI.
- **No interactive selection of any kind** — repositories, providers and models are named on the command line.

---

# Verification

```bash
npm run test:cli                                  # node:test suites
node frontend/cli/retrack.mjs help
node frontend/cli/retrack.mjs list repositories   # requires (or starts) a backend
node frontend/cli/retrack.mjs construct "Explain the auth flow" 4k --json | jq .evidence_state
```
