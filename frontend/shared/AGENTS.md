# Purpose

Owns the interface-agnostic RE:Track backend contract used by non-GUI interfaces.

This is the single integration point for CLI and TUI. It contains transport concerns only.

---

# Ownership

- `backend-client.mjs` — `createBackendClient()`, `ENDPOINTS`, `BackendRequestError`, `BackendUnreachableError`.

---

# Local Contracts

1. **No presentation, no UI framework.** No React, no Tauri, no ANSI/terminal styling, no argument parsing.
2. **No domain logic.** Endpoint paths and payload shapes mirror `backend/app/api/routers/`; nothing is computed, defaulted, or synthesized here.
3. **No silent fabrication.** Absent response fields stay absent. HTTP failures raise `BackendRequestError`; transport failures raise `BackendUnreachableError`.
4. **Explicit timeouts.** Every request carries an `AbortController` deadline; long-running operations (indexing, synthesis, benchmarks) declare their own longer budget.

---

# Verification

```bash
npm run lint
# Import surface check (must load without React/Tauri present)
node --input-type=module -e "import('./frontend/shared/backend-client.mjs').then(m => console.log(Object.keys(m).sort().join(',')))"
```
