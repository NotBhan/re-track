# Purpose

Owns every **interface implementation** of RE:Track: the desktop GUI, the terminal UI, and the command-line interface.

Interfaces are presentation and transport adapters. They contain no repository analysis, indexing, retrieval, ranking, or persistence logic — that authority stays in `backend/` (see `backend/AGENTS.md`) and is reached over the backend HTTP contract.

---

# Ownership

Owns:

- `gui/` — Tauri/React desktop application (`gui/index.html`, `gui/src/`, `gui/public/`).
- `tui/` — Terminal user interface (`tui/retrack.mjs`).
- `cli/` — Command-line interface and argument parsing (`cli/retrack.mjs`).
- `shared/` — Interface-agnostic backend contract client used by TUI and CLI.

---

# Layer Boundaries (hard rules)

1. **No interface-to-interface dependencies.**
   - `gui/` must not import from `cli/` or `tui/`.
   - `tui/` must not import from `gui/` or `cli/`.
   - `cli/` must not import from `gui/` or `tui/`.
2. **TUI never imports React or Tauri.** No `.tsx` component, no `@tauri-apps/*`.
3. **CLI never imports GUI or TUI presentation components.**
4. **Shared is the only cross-interface dependency.** `cli/` and `tui/` depend on `shared/`; `gui/` reaches the backend through Tauri IPC (`gui/src/lib/api.ts`) and must not depend on `shared/`.
5. **No duplicated domain logic.** Repository indexing, AST extraction, retrieval, ranking, context synthesis, and memory statistics are never re-implemented in this tree — they are requested from the backend.
6. **Truth boundary applies here too.** Interfaces render only what the backend returns; missing data is shown as missing, never invented.

---

# Build & Run Boundaries

| Interface | Entry point | Build |
|---|---|---|
| GUI | `gui/index.html` → `gui/src/main.tsx` | Vite root `frontend/gui`, output `dist/` at repository root (Tauri `frontendDist: ../dist`) |
| TUI | `tui/retrack.mjs` | none (plain Node ESM, zero dependencies) |
| CLI | `cli/retrack.mjs` | none (plain Node ESM, zero dependencies) |

Scripts: `npm run dev` / `npm run build` (GUI), `npm run cli`, `npm run tui`.

The TUI and CLI are excluded from the GUI bundle: Vite only bundles what `gui/index.html` imports, so their addition must not change the GUI bundle contents.

---

# Local Contracts

- `shared/backend-client.mjs` is the single backend contract surface for non-GUI interfaces. New backend endpoints are added there, not inlined per interface.
- Terminal interfaces must restore the terminal (cursor, alternate screen, raw mode) on every exit path, including Ctrl+C, EOF, and uncaught errors.
- Keep interface-specific dependencies isolated. Do not introduce a framework solely to populate a folder.

---

# Verification

```bash
npm run build                 # GUI typecheck + production build
npm run test                  # GUI unit/integration suite
npm run lint                  # oxlint over gui, cli, tui, shared
npx playwright test           # live-backend E2E (backend must be running on 127.0.0.1:8765)
node frontend/cli/retrack.mjs help
node frontend/tui/retrack.mjs # non-TTY invocations emit a single snapshot
```

---

# Child DOX Index

- `gui/` — Desktop GUI (Tauri/React). See `gui/AGENTS.md`.
- `gui/src/` — GUI source contract and component ownership. See `gui/src/AGENTS.md`.
- `cli/` — Command-line interface. See `cli/AGENTS.md`.
- `tui/` — Terminal user interface. See `tui/AGENTS.md`.
- `shared/` — Interface-agnostic backend client. See `shared/AGENTS.md`.
