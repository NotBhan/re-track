# Purpose

Owns the RE:Track terminal user interface: a keyboard-driven, monochrome ANSI application over the shared backend contract, with a non-TTY snapshot mode.

---

# Ownership

| File | Responsibility |
| --- | --- |
| `retrack.mjs` | Entry point: TTY/snapshot detection, alternate screen, raw mode, key event loop, resize handling, repaint coalescing, keepalive, every exit path. |
| `backend-lifecycle.mjs` | Backend discovery, spawn, `/health` readiness, ownership, and process-tree shutdown. The only TUI module allowed to import `node:child_process`. |
| `state.mjs` | Application state, session/navigation state, async actions, and the single input dispatch with explicit precedence. No terminal I/O, no timers. |
| `render.mjs` | Pure presentation model (`buildModel`) and frame composition (`composeFrame`/`composeLines`). No backend access, no timers, no writes. |
| `layout.mjs` | Frame budget arithmetic, responsive class, list scrolling windows, width-aware text fitting. |
| `theme.mjs` | Styler factory (bold/dim/inverse + semantic ok/warn/err), status and evidence vocabulary, value formatting. |
| `keys.mjs` | Terminal input decoding (CSI/SS3, control keys, mouse/paste stripping, partial-sequence buffering) and the line editor. |
| `markdown.mjs` | Rendered/raw markdown presentation for the context output and package viewer. |
| `tests/` | `node:test` suites: keys, state, render, process (PTY/non-TTY), shared-client contract. |

---

# Local Contracts

1. Depends on `../shared/backend-client.mjs` and its own `backend-lifecycle.mjs` only. Must not import `../gui/**` or `../cli/**`, React, Tauri, or any third-party runtime dependency, and no module except `backend-lifecycle.mjs` may touch `node:child_process`.
2. **Terminal restoration is mandatory on every exit path**: `q`, Ctrl+C, SIGINT, SIGTERM, SIGHUP, stdin EOF/error, stdout error, and uncaught exceptions must leave the alternate screen, restore the cursor, and disable raw mode — and must release a backend this TUI started before the process exits.
3. **Canonical usage is `npm run tui`.** The TUI attaches to a backend already answering `RETRACK_BACKEND_URL` (default `http://127.0.0.1:8765`); otherwise it spawns one using the desktop runtime's startup contract: `<repo>/backend` (or `RETRACK_BACKEND_DIR`), `backend/.venv/bin/python` first, `python -m uvicorn app.server:app --host 127.0.0.1 --port <port>`, `PYTHONPATH` + the desktop environment (`BACKEND_ENV`), `RETRACK_PARENT_PID` (the backend's own watchdog reaps it if the TUI dies abruptly), output appended to `$TMPDIR/retrack-backend.log`, and bounded `/health` polling before the interface opens. `RETRACK_BACKEND_STARTUP_TIMEOUT_MS` overrides the readiness budget.
4. **Ownership is explicit, never inferred from the port.** `ensureBackend()` returns `owned`, true only when this invocation spawned the child; it also carries the child PID and process group. Shutdown targets only that child's process group (`SIGTERM`, then SIGKILL after a bounded grace). A backend that was already running — even one that won a port race against a spawned child — is attached to and never signalled.
5. Non-TTY invocation (pipe, CI) emits exactly **one** snapshot line and exits:
   `RE:Track · <base-url> · backend=<status> · repos=<n> · packages=<n>`.
   The snapshot may start (and then shut down) a backend of its own, but stdout stays exactly one line and no child outlives it. An unreachable backend that cannot be started exits non-zero with the startup failure on stderr (the client's error text for a backend that dies later). This contract is byte-compatible with earlier releases.
6. Subsystem reads are independent: a failing endpoint degrades that pane/section rather than blanking the view, and `r` (or the automatic cadence) reconciles.
7. Rendered values come from backend responses only. Missing values render as `unavailable` / `none` / `never` — never `0`, unknown percentages, or empty successes.
8. Repaints are coalesced (one frame per ~50 ms of input) and idle output stays quiet: the tick repaints only while an operation or notice is live, plus a 4 s no-op keepalive that surfaces terminal-layer failures.

---

# Container Hierarchy

```
Frame
├─ Header        brand · active repository (status) · backend/degrades · transient notice
├─ Rule          hidden when compact
├─ Body          (replaced by an overlay while one is open)
│   ├─ Rail        persistent navigation: Repositories · Code · Context · System (+ counts)
│   └─ View        primary list region (+ inline filter row) and the inspector
├─ Operation     sticky line while indexing/synthesizing (real phase / elapsed / runtime state)
├─ Footer        contextual hints derived from the same table as the help sheet
└─ Overlays      Add repository · Delete confirmation · New task · Save package · Help
```

Focus ownership: exactly one of `rail`, `list`, `inspector`; an open overlay owns input and focus returns to the previous region when it closes. Per-view cursors and scroll offsets are preserved across view switches.

Responsive classes (from `layout.mjs`):

| Class | Condition | Layout |
| --- | --- | --- |
| `wide` | `cols ≥ 110` | rail + list + inspector side by side; `Tab` cycles all three |
| `medium` | `48 ≤ cols < 110` | rail + list; `enter` opens the inspector as a full-region mode (`esc` returns) |
| `compact` | `rows < 18` | no rule line, fewer footer hints, static operation text |
| `tooSmall` | `cols < 48 or rows < 12` | `terminal too small` notice with backend, repository and quit hint only |

---

# Views

- **Repositories** — list rows (name, files, languages, last indexed, status) and an inspector with path, source, branch, commit, status, files, size, languages, frameworks, architecture, entry points, components, call-graph counts, last index time, error message, `automatic updates: not available`, `cancellation: not supported by the backend`, and the summary. Actions: `a` add, `s` scan, `i` index/re-index (blocked with a notice while a run is active), `d` delete (confirmation overlay), `enter` inspect.
- **Code** — scoped to the selected repository: a banner for the call-graph state (`not_analyzed`, `analyzing`, `zero_edges`, `failed` with the backend error verbatim), component and entry-point rows, and AST symbols from `call_graph_nodes`; the inspector shows file/kind/line and callers/callees derived from `call_graph_edges`. Code search and AST detail are not exposed over HTTP, and the view says so.
- **Context** — suggested tasks (`/repos/{id}/prompts`, labelled with their `ai`/`heuristic` source) and saved packages in the list; the inspector shows evidence state, evidence strength, the qualitative confidence tier, symbols, callers/callees, grounded files, missing evidence, abstention reason, inference telemetry, measured phases, and the output in rendered or raw markdown. Actions: `n` new task (prefilled from the selected suggestion), `b` token budget, `g` structural-graph toggle, `m` rendered/raw, `S` save package, `enter` open package, `d` delete package.
- **System** — a single full-width read-only report: provider identity/reachability/health/endpoint, configured vs verified active model, embedding and semantic-memory provider states, engine/cognee state and reasons, MCP readiness, concurrency guard, hardware (RAM/CPU/GPU/VRAM/execution device), counts, memory statistics, storage paths, recent structured log records, and explicit `provider switching: GUI only` / `settings mutation: GUI only` notes. `e` exports a diagnostics bundle and reports the returned path.

---

# Keyboard Map

| Keys | Action |
| --- | --- |
| `1` `2` `3` `4` | Switch to Repositories / Code / Context / System |
| `tab` | Cycle focus (rail → list → inspector when visible) |
| `↑` `↓` | Move selection (list/rail) or scroll (inspector/system/viewer) |
| `PgUp` `PgDn` `home` `end` | Page and jump within the focused region |
| `enter` | Primary action (inspect, open, submit) |
| `esc` | Close overlay / leave inspector mode / clear filter |
| `/` | Filter the list (Repositories, Code) |
| `?` | Keyboard help sheet (single source with the footer hints) |
| `r` | Refresh from the backend |
| `q` / `Ctrl+C` | Quit (terminal restored) |
| `a` `s` `i` `d` | Repositories: add, scan, index, delete |
| `n` `b` `g` `m` `S` | Context: new task, budget, AST graph, rendered/raw, save package |
| `e` | System: export diagnostics bundle |

Overlays use one shared editor: visible cursor, `←`/`→`, `home`/`end`, `Backspace`, `Ctrl+U`/`W`/`K`/`A`/`E`, `enter` to submit, `esc` to cancel. Validation errors come from the client/backend responses; malformed input is never silently accepted.

---

# Truthfulness Rules

- Indexing shows the backend's own phases (`phase N/M · <stage>`) while a run is active, otherwise an indeterminate stage with elapsed time. No fabricated percentage, no cancel control.
- Synthesis shows elapsed time plus the runtime guard state derived from `/health` (`submitting`, `preparing`, `executing`, `queued`, `unreachable`). Post-completion telemetry (phases, tokens, model, fallback) is rendered exactly as returned.
- Evidence confidence is the engine's channel agreement (0.0 / 0.5 / 1.0) rendered as `Cross-validated` / `Single-channel` / `Not computed`; evidence *strength* is the engine's weighted score. A confidence percentage is never displayed.
- An indexing run started elsewhere (GUI/MCP) is adopted as the operation line, marked as external, and never re-triggered.
- Unsupported capabilities are stated in the UI (no cancellation, no automatic updates, no HTTP code search, provider/settings changes are GUI-only) instead of being offered as controls.

---

# Verification

```bash
npm run test:tui              # node:test suites (keys, state, render, lifecycle, process, client)
npm run lint                  # oxlint over gui, cli, tui, shared
node frontend/tui/retrack.mjs | cat   # non-TTY snapshot path, must terminate
npm run tui                   # interactive; starts the backend when needed, attaches when running
```

PTY verification (real backend on `127.0.0.1:8765`, 40×120 unless noted):

```bash
script -qec "stty rows 40 cols 120; node frontend/tui/retrack.mjs" /dev/null
```

Checklist: cold start hydrates persisted repositories without an import; repository selection/switching/filtering; add → scan → index with real phases → completion; context synthesis with evidence and rendered/raw output; package save/open/delete; backend loss and `r` reconciliation; view navigation and modal input; resizing (120×40 → 40×10); `q` and `Ctrl+C` exit with the alternate screen and cursor restored; no orphan processes. `process.test.mjs` covers the snapshot contract, the failed-startup path, PTY startup/quit/Ctrl+C, alternate-screen restoration, and the published scroll bounds; `lifecycle.test.mjs` and `lifecycle-process.test.mjs` cover discovery/spawn/readiness/ownership/shutdown (attach without spawning, graceful and SIGKILL-fallback shutdown, startup failure, readiness timeout, port-race protection, repeated launch, snapshot cleanup) against a real child backend.
