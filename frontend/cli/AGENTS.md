# Purpose

Owns the RE:Track command-line interface: command parsing and text/grid presentation.

---

# Ownership

- `retrack.mjs` — argument parsing, command dispatch, table/JSON rendering, exit codes.

---

# Local Contracts

1. Depends on `../shared/backend-client.mjs` only. Must not import `../gui/**` or `../tui/**`.
2. Zero runtime dependencies — plain Node ESM.
3. All backend interaction is delegated to the shared client; no HTTP calls are inlined here.
4. `--json` emits the raw backend payload unmodified.
5. Exit codes: `0` success, `1` usage/backend failure. Unknown commands print help to stderr.
6. Output never invents values for fields the backend did not return.

---

# Commands

`health`, `status`, `repos`, `packages`, `memory`, `context <task>`, `index <path>`, `benchmark`, `help`.

---

# Verification

```bash
node frontend/cli/retrack.mjs help
node frontend/cli/retrack.mjs health --json   # requires a running backend
```
