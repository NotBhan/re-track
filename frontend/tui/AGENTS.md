# Purpose

Owns the RE:Track terminal user interface: an interactive ANSI dashboard with a non-TTY snapshot mode.

---

# Ownership

- `retrack.mjs` — screen lifecycle (alternate screen buffer, raw mode), keyboard handling, ANSI layout, auto-refresh.

---

# Local Contracts

1. Depends on `../shared/backend-client.mjs` only. Must not import `../gui/**` or `../cli/**`.
2. Zero runtime dependencies — plain Node ESM, no React, no Tauri.
3. **Terminal restoration is mandatory on every exit path**: `q`, Ctrl+C, SIGINT, SIGTERM, stdin EOF, and uncaught exceptions must leave the alternate screen, restore the cursor, and disable raw mode.
4. Non-TTY invocation (pipe, CI) must emit one snapshot line and exit instead of blocking.
5. Subsystem reads are independent: a failing endpoint degrades that pane rather than blanking the view.
6. Rendered values come from backend responses only; unavailable values are shown as unavailable.

---

# Verification

```bash
npm run tui                    # interactive (requires a running backend)
node frontend/tui/retrack.mjs | cat   # non-TTY snapshot path, must terminate
```
