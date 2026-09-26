# Purpose

Owns the RE:Track terminal user interface: a keyboard-driven, monochrome ANSI application over the shared backend contract, with a non-TTY snapshot mode.

---

# Ownership

| File | Responsibility |
| --- | --- |
| `retrack.mjs` | Entry point: TTY/snapshot detection, alternate screen, raw mode, key event loop, resize handling, repaint coalescing, keepalive, every exit path. |
| `backend-lifecycle.mjs` | Backend discovery, spawn, `/health` readiness, ownership, and process-tree shutdown. The only TUI module allowed to import `node:child_process`. |
| `keymap.mjs` | The control map: every advertised control, its terse footer label, its descriptive help text, the contextual hint order, and the derived `?` sheet. The single source of truth for footer and help. |
| `state.mjs` | Application state, session/navigation state, async actions, and the single input dispatch with explicit precedence. No terminal I/O, no timers. |
| `render.mjs` | Pure presentation model (`buildModel`) and frame composition (`composeFrame`/`composeLines`). No backend access, no timers, no writes. |
| `layout.mjs` | Frame budget arithmetic, responsive class, list scrolling windows, width-aware text fitting. |
| `theme.mjs` | Styler factory (bold/dim/inverse + semantic ok/warn/err), status and evidence vocabulary, value formatting. |
| `keys.mjs` | Terminal input decoding (CSI/SS3, control keys, mouse/paste stripping, partial-sequence buffering) and the line editor. |
| `markdown.mjs` | Rendered/raw markdown presentation for the context output and package viewer. |
| `export.mjs` | Local package export: path resolution (`~`, relative), filesystem-safe naming, never-overwrite resolution, markdown write. No backend access. |
| `tests/` | `node:test` suites: keys, state, render, menu, export, process (PTY/non-TTY), lifecycle, shared-client contract. |

---

# Local Contracts

1. Depends on `../shared/backend-client.mjs` and its own `backend-lifecycle.mjs` only. Must not import `../gui/**` or `../cli/**`, React, Tauri, or any third-party runtime dependency, and no module except `backend-lifecycle.mjs` may touch `node:child_process`.
2. **Terminal restoration is mandatory on every exit path**: `q`, Ctrl+C, SIGINT, SIGTERM, SIGHUP, stdin EOF/error, stdout error, and uncaught exceptions must leave the alternate screen, restore the cursor, and disable raw mode — and must release a backend this TUI started before the process exits.
3. **Canonical usage is `npm run tui`.** The TUI attaches to a backend already answering `RETRACK_BACKEND_URL` (default `http://127.0.0.1:8765`); otherwise it spawns one using the desktop runtime's startup contract: `<repo>/backend` (or `RETRACK_BACKEND_DIR`), `backend/.venv/bin/python` first, `python -m uvicorn app.server:app --host 127.0.0.1 --port <port>`, `PYTHONPATH` + the desktop environment (`BACKEND_ENV`), `RETRACK_PARENT_PID` (the backend's own watchdog reaps it if the TUI dies abruptly), output appended to `$TMPDIR/retrack-backend.log`, and bounded `/health` polling before the interface opens. `RETRACK_BACKEND_STARTUP_TIMEOUT_MS` overrides the readiness budget.
4. **Ownership is explicit, never inferred from the port.** `ensureBackend()` returns `owned`, true only when this invocation spawned the child; it also carries the child PID and process group. Shutdown targets only that child's process group (`SIGTERM`, then SIGKILL after a bounded grace). A backend that was already running — even one that won a port race against a spawned child — is attached to and never signalled.
5. **The control map is the single source of truth (Torlink's keymap model).** `keymap.mjs` holds every advertised control with a terse footer label, a descriptive help label, a help group and a context list. `footerHints(context)` and the `?` sheet are both derived from it, so they cannot disagree; a hint that is not in the table is shown nowhere. The footer drops whole hints when the row is full (never wraps or clips) and always keeps the `?` affordance when the context advertises it.
6. **Input precedence is explicit**: Ctrl+C → open overlay → active text edit (filter/field) → global keys (`q`, `?`, `r`, `1-5`, `tab`, `esc`, `←→`/`h l`) → focused region → ignored. A modal or field never leaks a keystroke to the view behind it, and the footer context is resolved with the same precedence.
7. Non-TTY invocation (pipe, CI) emits exactly **one** snapshot line and exits:
   `RE:Track · <base-url> · backend=<status> · repos=<n> · packages=<n>`.
   The snapshot may start (and then shut down) a backend of its own, but stdout stays exactly one line and no child outlives it. An unreachable backend that cannot be started exits non-zero with the startup failure on stderr (the client's error text for a backend that dies later). This contract is byte-compatible with earlier releases.
8. Subsystem reads are independent: a failing endpoint degrades that pane/section rather than blanking the view, and `r` (or the automatic cadence) reconciles.
9. Rendered values come from backend responses only. Missing values render as `unavailable` / `none` / `never` — never `0`, unknown percentages, or empty successes.
10. Repaints are coalesced (one frame per ~50 ms of input) and idle output stays quiet: the tick repaints only while an operation or notice is live, plus a 4 s no-op keepalive that surfaces terminal-layer failures.

---

# Container Hierarchy

```
Frame
├─ Header        brand · active repository (status) · backend/degrades · transient notice
├─ Rule          hidden when compact
├─ Body          (replaced by an overlay while one is open)
│   ├─ Rail        persistent menu: Repositories · Code · Context · System · Settings (+ counts)
│   └─ View        primary list region (+ inline filter row) and the inspector
├─ Operation     sticky line while indexing/synthesizing (real phase / elapsed / runtime state,
│                 determinate only from backend-reported counts)
├─ Footer        contextual hints derived from the same table as the help sheet
└─ Overlays      Add repository · Delete confirmation · New task · Save package ·
                Append to package · Export package · Pipeline settings · Help
```

Navigation follows the Torlink interaction model. The rail selection **is** the active destination: ↑↓ move it (with wrap-around) and the content pane follows immediately. `enter` activates — it moves focus into the list for the destination, or opens the detail for the selected row. Focus and activation are separate visual states, both monochrome-safe: the active destination always carries `▍` and the focused region adds the `▍` marker to its own title (the rail's `Workspace` header, the list title, the inspector title), so `NO_COLOR` still shows where the keyboard is.

Focus ownership: exactly one of `rail`, `list`, `inspector`; below the side-by-side breakpoint the inspector is a **mode** that owns input while open and closes when focus leaves it (Torlink's rule), so focus never rests on a hidden region. `esc` walks back one level — detail → list → menu — and clears an applied filter first. Per-view cursors and scroll offsets are preserved across view switches. Responsive classes (from `layout.mjs`):

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
- **Context** — suggested tasks (`/repos/{id}/prompts`, labelled with their `ai`/`heuristic` source) and a saved-package catalog in the list; opening the workbench fetches the suggestions for the selected repository (a set already loaded for that repository is kept, because generating them is not free — `r` forces a re-read), and `p` scopes the catalog to packages alone so they are navigable independently of the suggestions. The inspector shows evidence state, evidence strength, the qualitative confidence tier, symbols, callers/callees, grounded files, missing evidence, abstention reason, inference telemetry, measured phases, and the output in rendered or raw markdown; a selected package shows its repository/branch/commit, tokens, sections and timestamps from the package record. Actions: `n` new task (prefilled from the selected suggestion), `b` token budget, `g` structural-graph toggle, `m` rendered/raw, `S` save package, `enter` open package, `A` append a task/note to the selected package, `e` export the stored markdown to a local file, `d` delete package. The package viewer adds `a` (append) and `e` (export) as first-class actions.
- **System** — a single full-width read-only report: provider identity/reachability/health/endpoint, configured vs verified active model, embedding and semantic-memory provider states, engine/cognee state and reasons, MCP readiness, concurrency guard, hardware (RAM/CPU/GPU/VRAM/execution device), counts, memory statistics, storage paths, recent structured log records, and pointers to the Settings view (`configuration: Settings view`) plus `cancellation: not supported by the backend`. `e` exports a diagnostics bundle and reports the returned path.
- **Settings** — the persisted configuration as reported by `GET /settings` plus the runtime facts that qualify it: Provider (endpoint, configured model, verified active model, reachability, health, masked API key; embedding and semantic-memory providers), Storage & pipeline (data/system roots, logs and cache directories, storage canonicity/writability, engines), Hardware & runtime (RAM/CPU/GPU/VRAM, execution device, engine/cognee state, MCP readiness, concurrency, memory statistics), and Capabilities (an explicit matrix of what this interface can and cannot do). Two mutations exist over HTTP and are exposed here: `t` opens the pipeline toggles (knowledge-graph extraction, entity auto-linking, ingestion caching) persisted through `POST /settings/cognee`, and `e` opens the provider editor (provider · endpoint · model · API key) persisted through `POST /provider/update`; both re-read the authoritative values after saving. Storage engines are shown as fixed by the backend (the desktop UI disables them for the same reason: one engine each). Display scaling is a desktop-window property and states `GUI only`. A failed settings read renders `settings unavailable: <error>` rather than stale values.
- **Provider editor** (opened with `e` in Settings) — `tab` cycles the provider (lmstudio / ollama / openai_compatible) and carries its default endpoint unless the endpoint was edited here; `↑↓` moves between fields, which share the text editor; `ctrl+p` runs the non-mutating discovery probe (`POST /provider/discover`) and lists the models the endpoint reports (a probe never changes the active provider); `enter` saves through `POST /provider/update` after requiring an endpoint and a model; `esc` cancels. Failures keep the form open with the backend's message.

---

# Keyboard Map

| Keys | Action |
| --- | --- |
| `↑` `↓` (`j` `k`) | Move the menu selection, the list selection, or scroll the focused region (wraps in menus/lists; `PgUp` `PgDn` `home` `end` page and jump) |
| `←` `→` (`h` `l`) | Move between panes (rail ↔ list ↔ inspector when it is open) |
| `enter` | Activate: rail → list, list row → its detail (which then owns the keyboard), dialogs → submit |
| `esc` | Back one level: overlay → detail → list → menu; clears an applied filter first |
| `tab` | Cycle focus (rail → list → detail when open); a mode that loses focus closes |
| `1` `2` `3` `4` `5` | Menu shortcuts: jump straight to Repositories / Code / Context / System / Settings |
| `/` | Filter the list (field owns the keyboard; `enter` applies, `esc` clears, `↓` leaves the field) |
| `?` | Control reference from the shared keymap (`↑↓` scroll it, any other key closes it) |
| `r` | Refresh from the backend |
| `q` / `Ctrl+C` | Quit (terminal restored, owned backend stopped) |
| `a` `s` `i` `d` | Repositories: add, scan, index, delete |
| `n` `b` `g` `m` `S` | Context: new task, budget, AST graph, rendered/raw, save package |
| `p` `A` `e` | Context: scope the catalog to packages / append to the selected package / export its markdown locally |
| `a` `e` | Package viewer: append to this package / export it; `m` toggles rendered-raw |
| `t` `e` | Settings: pipeline toggles (`POST /settings/cognee`) / provider editor (`POST /provider/update`) |
| `ctrl+p` `tab` | Provider editor: probe the endpoint for models (changes nothing) / cycle provider or discovered model |
| `e` | System: export diagnostics bundle |

Overlays own input completely — no view shortcut leaks through. Text fields use one shared editor (visible cursor: inverse cell, or the `▏` caret when styling is disabled): `←`/`→` move the cursor, `home`/`end`, `Backspace`, `Ctrl+U`/`W`/`K`/`A`/`E`, `enter` to submit, `esc` to cancel. The add-repository dialog moves between its fields with `↑`/`↓` and switches source with `tab`. Validation errors come from the client/backend responses; malformed input is never silently accepted.

---

# Truthfulness Rules

- Indexing shows the backend's own stage text while a run is active; a determinate bar is drawn only when the backend reports file counts (`processed/total`, with `phase N/M` alongside when a phase index is present) or a phase index alone, and otherwise the stage stays indeterminate with elapsed time. No fabricated percentage, no cancel control.
- Synthesis shows elapsed time plus the runtime guard state derived from `/health` (`submitting`, `preparing`, `executing`, `queued`, `unreachable`). Post-completion telemetry (phases, tokens, model, fallback) is rendered exactly as returned.
- Evidence confidence is the engine's channel agreement (0.0 / 0.5 / 1.0) rendered as `Cross-validated` / `Single-channel` / `Not computed`; evidence *strength* is the engine's weighted score. A confidence percentage is never displayed.
- An indexing run started elsewhere (GUI/MCP) is adopted as the operation line, marked as external, and never re-triggered. Its end comes from the backend too: the progress poll's terminal status publishes the completion/failure line from the returned counts and the reconciling read clears the operation, so the spinner cannot outlive the run.
- Unsupported capabilities are stated in the UI (no cancellation, no automatic updates, no HTTP code search, storage engines fixed by the backend, display scaling GUI-only) instead of being offered as controls. Provider configuration and model discovery are *not* among them: both have HTTP contracts and are exposed.
- The `?` affordance survives compact terminals: the footer reserves it before fitting whole hints, and drops hints rather than wrapping or clipping.
- Settings render exactly the persisted payload: a failed read stays visible as `settings unavailable: <error>`, and a write failure leaves the stored value unchanged. Only the mutations the HTTP contract exposes are editable here (the three pipeline booleans and the provider configuration); everything else is shown as reported.
- A package append is sent as `additional_task` through `POST /packages/{id}/append` and the updated package is re-read; errors keep the dialog open with the backend message.
- Package export is local and honest: the markdown already stored on the backend is written to the chosen path, an existing file is never overwritten (a numbered sibling is used), and the path actually written is reported. No backend export endpoint exists or is invented.

---

# Verification

```bash
npm run test:tui              # node:test suites (keys, state, render, menu, export, lifecycle, process, client)
npm run lint                  # oxlint over gui, cli, tui, shared
node frontend/tui/retrack.mjs | cat   # non-TTY snapshot path, must terminate
npm run tui                   # interactive; starts the backend when needed, attaches when running
```

PTY verification (real backend on `127.0.0.1:8765`, 40×120 unless noted):

```bash
script -qec "stty rows 40 cols 120; node frontend/tui/retrack.mjs" /dev/null
```

Checklist: cold start hydrates persisted repositories without an import; repository selection/switching/filtering; add → scan → index with real phases → completion; context synthesis with evidence and rendered/raw output; package save/open/append/delete and local export (an existing file is not overwritten); Settings loads the persisted payload, a pipeline toggle round-trips through `POST /settings/cognee`, and the provider editor probes (`POST /provider/discover`) and saves (`POST /provider/update`); backend loss and `r` reconciliation; view navigation and modal input; resizing (120×40 → 40×10); `q` and `Ctrl+C` exit with the alternate screen and cursor restored; no orphan processes. `process.test.mjs` covers the snapshot contract, the failed-startup path, PTY startup/quit/Ctrl+C, alternate-screen restoration, and the published scroll bounds; `lifecycle.test.mjs` and `lifecycle-process.test.mjs` cover discovery/spawn/readiness/ownership/shutdown (attach without spawning, graceful and SIGKILL-fallback shutdown, startup failure, readiness timeout, port-race protection, repeated launch, snapshot cleanup) against a real child backend; `menu.test.mjs` covers menu navigation (movement with wrap-around, activation, vim aliases, preserved per-view cursors), input precedence (overlay, field, filter, help, globals), focus rules (detail mode below the breakpoint, back chain, hidden regions) and rendering (focus markers without color, contextual footers that never clip, footer/help single-source agreement, visible input cursor); `state.test.mjs`/`render.test.mjs` additionally cover settings (load, toggle persistence, failure surfacing, non-persistable keys), the package catalog scope, append and export flows, and determinate vs indeterminate indexing progress; `export.test.mjs` covers path resolution, safe naming and no-overwrite semantics.

Menu acceptance run (real backend, PTY): drive the whole interface with `↑` `↓` `enter` `tab` `esc` plus contextual keys at 120×40, 90×24, 60×20 and 48×16 — menu movement and activation, dialog/filter/help owning input, detail mode focus, contextual footers, and clean exit with the terminal restored — and once with `NO_COLOR=1` to confirm focus and selection markers survive without styling.
