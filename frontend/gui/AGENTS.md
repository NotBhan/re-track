# Purpose

Owns the RE:Track desktop GUI: the Tauri-hosted React application.

This directory is the Vite project root for the GUI.

---

# Ownership

- `index.html` — Vite HTML entry (`/src/main.tsx`).
- `src/` — React application source. See `src/AGENTS.md` for the component contract.
- `public/` — static assets served by Vite.

---

# Local Contracts

1. The GUI is a presentation adapter. It communicates with the backend exclusively through Tauri IPC (`src/lib/api.ts`) and never imports `../cli/**`, `../tui/**`, or `../shared/**`.
2. GUI code must not become the shared source of business logic; backend authority is unchanged.
3. Vite `root` is `frontend/gui`; the production bundle is emitted to the repository-root `dist/` so the Tauri runtime (`src-tauri/tauri.conf.json` → `frontendDist: "../dist"`) is unaffected.
4. TUI/CLI additions must not alter GUI bundle contents or runtime behaviour.

---

# Verification

```bash
npm run build     # tsc + vite build (root frontend/gui -> dist/)
npm run test      # vitest, GUI test suites
npm run tauri dev # desktop runtime launches
```
