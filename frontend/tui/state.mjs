/**
 * RE:Track TUI application state.
 *
 * Owns data loaded from the backend, session/navigation state, and every async
 * action. It performs no terminal I/O and keeps no timers: the entry point
 * drives `tick(now)` and renders `getState()`. All backend access goes through
 * the shared client (frontend/shared/backend-client.mjs).
 */

import { decodeChunk, applyEdit, stripMouseSequences } from "./keys.mjs";
import { clamp, wrapStep } from "./layout.mjs";

export const VIEWS = Object.freeze(["repositories", "code", "context", "system", "settings"]);
export const VIEW_LABELS = Object.freeze({
  repositories: "Repositories",
  code: "Code",
  context: "Context",
  system: "System",
  settings: "Settings",
});

export const TOKEN_BUDGETS = Object.freeze([2048, 4096, 8192]);

/** Settings sections (navigation); the renderer builds the rows for each one. */
export const SETTINGS_SECTIONS = Object.freeze([
  { key: "provider", label: "Provider" },
  { key: "storage", label: "Storage & pipeline" },
  { key: "hardware", label: "Hardware & runtime" },
  { key: "capabilities", label: "Capabilities" },
]);

/**
 * Inference providers the backend accepts for hot-reload (POST /provider/update).
 * The same three the desktop provider picker offers.
 */
export const PROVIDER_OPTIONS = Object.freeze(["lmstudio", "ollama", "openai_compatible"]);

/** Endpoint defaults used when cycling providers; a custom endpoint is kept. */
export const PROVIDER_ENDPOINTS = Object.freeze({
  lmstudio: "http://localhost:1234/v1",
  ollama: "http://localhost:11434/v1",
});

/**
 * Field order of the provider editor. `provider` cycles (tab) or opens a choice
 * list (enter), `endpoint`/`apiKey` are text, and `model` opens the selector —
 * there is deliberately no field in which a model name could be typed.
 */
const PROVIDER_FIELDS = Object.freeze(["provider", "endpoint", "apiKey", "model"]);

/**
 * Pipeline settings the backend HTTP contract can persist (POST /settings/cognee).
 * The storage engines the same request accepts are deliberately not exposed: the
 * desktop UI disables them too, because the backend supports a single engine each.
 */
export const PIPELINE_SETTINGS = Object.freeze([
  {
    key: "enable_kg_extraction",
    label: "Knowledge graph extraction",
    help: "Extract entities and relationships into the graph store during ingestion",
  },
  {
    key: "auto_link_entities",
    label: "Auto-link entities",
    help: "Link detected symbols and entities automatically",
  },
  {
    key: "caching",
    label: "Ingestion caching",
    help: "Cache intermediate ingestion results",
  },
]);

const NOTICE_TTL_MS = 4000;
const PROGRESS_POLL_MS = 700;
const HEALTH_POLL_MS = 2000;
const SUMMARY_REFRESH_MS = 5000;
const ERROR_RETRY_MS = 2000;
const SYSTEM_LOG_LIMIT = 20;

function initialState() {
  return {
    ready: false,
    loading: false,
    error: null,
    degraded: [],
    lastRefreshAt: null,

    health: null,
    status: null,
    providerStatus: null,
    detailedHealth: null,
    memoryStats: null,
    logs: null,
    appSettings: null,
    settingsError: null,
    settingsBusy: false,
    // Provider editor draft (open only while its overlay is) and the model
    // discovery result for the endpoint it points at.
    providerDraft: null,
    models: { state: "idle", provider: null, endpoint: null, status: null, items: [], message: null, errorDetails: null },

    repositories: [],
    packages: [],
    packageScope: "all",
    prompts: { state: "idle", source: null, items: [], error: null, repoId: null },
    context: null,
    contextError: null,
    progress: null,
    lastRun: null,

    view: "repositories",
    focus: "list",
    inspectorOpen: false,
    overlay: null,
    filter: "",
    filterCursor: 0,
    filterActive: false,
    markdownView: "rendered",
    tokenBudget: 4096,
    includeGraph: true,

    cursors: { repositories: 0, code: 0, context: 0, system: 0, settings: 0 },
    // One scroll offset per surface that can overflow: each destination keeps
    // its own detail position, and the two scrolling overlays keep theirs.
    scroll: { repositories: 0, code: 0, context: 0, settings: 0, system: 0, viewer: 0, help: 0 },

    notice: null,
    operation: null,
    viewport: {
      pageSize: 8,
      detailMax: 0,
      detailPage: 8,
      systemMax: 0,
      systemPage: 8,
      viewerMax: 0,
      viewerPage: 8,
      helpMax: 0,
      helpPage: 8,
    },
    nowMs: 0,
  };
}

const errorText = (error) => (error instanceof Error ? error.message : String(error));

export function createApp(options = {}) {
  const client = options.client;
  if (!client) throw new Error("createApp requires a client");
  const exportMarkdown = options.exportMarkdown ?? null;
  const exportFileName = options.exportFileName ?? ((name) => `${String(name ?? "").trim() || "context-package"}.md`);
  // Clipboard adapter (frontend/tui/clipboard.mjs in the real entry point):
  // `(text, label) => Promise<{ok, message}>`. Absent means this session has no
  // clipboard, and the Copy action says so instead of pretending to work.
  const copyText = options.copyText ?? null;

  const now = options.now ?? (() => Date.now());
  const noticeTtlMs = options.noticeTtlMs ?? NOTICE_TTL_MS;
  const progressPollMs = options.progressPollMs ?? PROGRESS_POLL_MS;
  const healthPollMs = options.healthPollMs ?? HEALTH_POLL_MS;
  const summaryRefreshMs = options.summaryRefreshMs ?? SUMMARY_REFRESH_MS;
  const errorRetryMs = options.errorRetryMs ?? ERROR_RETRY_MS;

  const state = initialState();
  state.nowMs = now();
  const listeners = new Set();
  const timers = { lastProgressPoll: 0, lastHealthPoll: 0, lastSummaryRefresh: 0 };

  function emit() {
    for (const listener of listeners) listener(state);
  }

  function set(patch) {
    Object.assign(state, patch);
    state.nowMs = now();
    emit();
  }

  function notice(message, level = "info") {
    set({ notice: { message: String(message), level, at: now() } });
  }

  function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  /* ------------------------------- selectors ------------------------------- */

  function matchesFilter(repo, filter) {
    if (!filter) return true;
    const needle = filter.toLowerCase();
    const haystack = [repo.name, repo.local_path, ...(repo.languages ?? []), ...(repo.frameworks ?? [])]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  }

  function visibleRepositories() {
    return state.repositories.filter((repo) => matchesFilter(repo, state.filter));
  }

  function selectedRepository() {
    const rows = visibleRepositories();
    if (rows.length === 0) return null;
    return rows[clamp(state.cursors.repositories, 0, rows.length - 1)];
  }

  function codeSymbols() {
    const repo = selectedRepository();
    const nodes = Array.isArray(repo?.call_graph_nodes) ? repo.call_graph_nodes : [];
    return nodes;
  }

  function contextRows() {
    // The catalog can be scoped to saved packages so they are navigable on
    // their own, independently of the generated output and suggestions.
    // "Run new task" leads the catalog as a visible way into the custom prompt
    // (`n` opens the same dialog from anywhere in the view); the packages-only
    // scope stays packages alone, so the action row is not repeated there.
    const newTask =
      state.packageScope === "packages" ? [] : [{ kind: "task", label: "Run new task" }];
    const suggestions =
      state.packageScope === "packages"
        ? []
        : (state.prompts.items ?? []).map((item) => ({
            kind: "suggestion",
            label: item.label,
            prompt: item.prompt,
          }));
    const packages = (state.packages ?? []).map((pkg) => ({
      kind: "package",
      id: pkg.id,
      label: pkg.name,
      task: pkg.task || pkg.objective,
      tokens: pkg.token_estimate,
      repository: pkg.repository_name,
      branch: pkg.repository_branch,
      commit: pkg.repository_commit,
      created: pkg.created_at,
      updated: pkg.updated_at,
      sections: pkg.section_count,
      compression: pkg.compression_ratio,
      totalTime: pkg.total_time_ms,
      memories: pkg.retrieved_memories,
      deduplicated: pkg.deduplicated_memories,
      tags: Array.isArray(pkg.tags) ? pkg.tags : [],
    }));
    return [...newTask, ...suggestions, ...packages];
  }

  function selectedContextRow() {
    const rows = contextRows();
    if (rows.length === 0) return null;
    return rows[clamp(state.cursors.context, 0, rows.length - 1)];
  }

  function settingsRows() {
    return SETTINGS_SECTIONS.map((section) => ({ ...section }));
  }

  function selectedSettingsSection() {
    return SETTINGS_SECTIONS[clamp(state.cursors.settings, 0, SETTINGS_SECTIONS.length - 1)] ?? null;
  }

  function currentRows() {
    if (state.view === "repositories") return visibleRepositories();
    if (state.view === "code") return codeSymbols();
    if (state.view === "context") return contextRows();
    if (state.view === "settings") return settingsRows();
    return [];
  }

  /* -------------------------------- loading -------------------------------- */

  /**
   * Suggested tasks for a repository. Generating them is not free, so an
   * already-loaded set for the same repository is kept unless `force` is set
   * (the `r` refresh); a failed load is always retried.
   */
  async function loadPrompts(repo, { force = false } = {}) {
    if (!repo?.id) {
      set({ prompts: { state: "idle", source: null, items: [], error: null, repoId: null } });
      return;
    }
    if (!force && state.prompts.repoId === repo.id && state.prompts.state === "loaded") return;
    set({ prompts: { state: "loading", source: state.prompts.source, items: state.prompts.items, error: null, repoId: repo.id } });
    try {
      const payload = await client.repositoryPrompts(repo.id);
      const items = Array.isArray(payload?.prompts) ? payload.prompts : [];
      set({ prompts: { state: "loaded", source: payload?.source ?? null, items, error: null, repoId: repo.id } });
    } catch (error) {
      set({ prompts: { state: "error", source: null, items: [], error: errorText(error), repoId: repo.id } });
    }
  }

  async function loadSummary({ quiet = false } = {}) {
    if (state.loading) return false;
    state.loading = true;
    if (!quiet) emit();

    const names = ["health", "status", "providerStatus", "repositories", "packages", "memoryStats"];
    const results = await Promise.allSettled([
      client.health(),
      client.status(),
      client.providerStatus(),
      client.listRepositories(),
      client.listContextPackages(),
      client.memoryStats(),
    ]);

    const [health, status, providerStatus, repositories, packages, memoryStats] = results;
    const failed = names.filter((_, index) => results[index].status === "rejected");

    const repositoriesValue =
      repositories.status === "fulfilled" && Array.isArray(repositories.value?.repositories)
        ? repositories.value.repositories
        : null;

    const patch = {
      loading: false,
      ready: true,
      lastRefreshAt: now(),
      degraded: failed,
      health: health.status === "fulfilled" ? health.value : state.health,
      status: status.status === "fulfilled" ? status.value : state.status,
      providerStatus: providerStatus.status === "fulfilled" ? providerStatus.value : state.providerStatus,
      packages:
        packages.status === "fulfilled" && Array.isArray(packages.value?.packages)
          ? packages.value.packages
          : state.packages,
      memoryStats: memoryStats.status === "fulfilled" ? memoryStats.value : state.memoryStats,
      repositories: repositoriesValue ?? state.repositories,
    };

    // Unreachable means nothing at all answered; that is a different condition
    // from a partially degraded backend.
    patch.error = failed.length === names.length ? "backend unavailable" : null;

    Object.assign(state, patch);
    state.nowMs = now();

    if (repositoriesValue) {
      const rows = visibleRepositories();
      state.cursors.repositories = clamp(state.cursors.repositories, 0, Math.max(0, rows.length - 1));
      adoptExternalIndexingRun(repositoriesValue);
    }

    emit();
    return true;
  }

  async function loadSystem() {
    const results = await Promise.allSettled([
      client.detailedHealth(),
      client.recentLogs(SYSTEM_LOG_LIMIT),
    ]);
    const [detailedHealth, logs] = results;
    set({
      detailedHealth: detailedHealth.status === "fulfilled" ? detailedHealth.value : state.detailedHealth,
      logs: logs.status === "fulfilled" ? logs.value?.logs ?? [] : state.logs,
    });
  }

  /**
   * Settings answers "what is RE:Track configured to use?": the persisted
   * application settings plus the storage/runtime detail the backend reports.
   * `settingsError` keeps a failed settings read visible instead of rendering
   * stale configuration as if it were current.
   */
  async function loadSettings() {
    const results = await Promise.allSettled([client.appSettings(), client.detailedHealth()]);
    const [appSettings, detailedHealth] = results;
    set({
      appSettings: appSettings.status === "fulfilled" ? appSettings.value : state.appSettings,
      settingsError: appSettings.status === "rejected" ? errorText(appSettings.reason) : null,
      detailedHealth: detailedHealth.status === "fulfilled" ? detailedHealth.value : state.detailedHealth,
    });
  }

  /**
   * Reconciled provider identity after a switch: the persisted settings, the
   * health/status facts that verify it, and the authoritative provider status.
   */
  async function loadProviderContext() {
    const results = await Promise.allSettled([
      client.appSettings(),
      client.health(),
      client.status(),
      client.providerStatus(),
    ]);
    const [settings, health, status, providerStatus] = results;
    set({
      appSettings: settings.status === "fulfilled" ? settings.value : state.appSettings,
      settingsError: settings.status === "rejected" ? errorText(settings.reason) : null,
      health: health.status === "fulfilled" ? health.value : state.health,
      status: status.status === "fulfilled" ? status.value : state.status,
      providerStatus: providerStatus.status === "fulfilled" ? providerStatus.value : state.providerStatus,
    });
  }

  /** Attach the operation line to a run started elsewhere (GUI/MCP) — read-only. */
  function adoptExternalIndexingRun(repositoriesValue) {
    if (state.operation?.kind === "synthesis") return;
    const running = repositoriesValue.find((repo) => repo.status === "indexing");
    if (running && state.operation?.kind !== "indexing") {
      state.operation = {
        kind: "indexing",
        repoId: running.id,
        repoName: running.name,
        startedAt: now(),
        external: true,
        stage: "indexing",
        stageIndex: null,
        stageTotal: null,
        processedFiles: null,
        totalFiles: null,
        failedFiles: null,
        elapsedMs: 0,
      };
    } else if (!running && state.operation?.kind === "indexing" && state.operation.external) {
      state.operation = null;
    }
  }

  async function refresh({ quiet = false } = {}) {
    await loadSummary({ quiet });
    if (state.view === "system") await loadSystem();
    if (state.view === "settings") await loadSettings();
    const repo = selectedRepository();
    if (repo) await loadPrompts(repo, { force: true });
    if (!quiet) notice("refreshed");
  }

  /* --------------------------------- actions -------------------------------- */

  function switchView(view) {
    if (!VIEWS.includes(view)) return;
    // Every destination keeps its own detail scroll position (and so does the
    // system report), because switching away and back should not lose the spot.
    const patch = { view, overlay: null, filterActive: false, providerDraft: null };
    // Below the side-by-side breakpoint the inspector is a mode, and Torlink's
    // rule is that a region's mode resets once focus leaves it: switching
    // destinations from the menu must not leave the previous detail covering
    // the new list.
    if (!state.viewport.sideBySide) patch.inspectorOpen = false;
    // System has no detail pane, so focus must never rest on a pane that is not
    // on screen: the report itself is the scrolled region there.
    if (view === "system" && state.focus === "inspector") {
      patch.focus = "list";
      patch.inspectorOpen = false;
    }
    set(patch);
    if (view === "system") void loadSystem();
    if (view === "settings") void loadSettings();
    // Suggested tasks belong to the selected repository, so they are fetched
    // when the workbench opens rather than waiting for an explicit refresh.
    if (view === "context") void loadPrompts(selectedRepository());
  }

  /** Jump the list cursor to an absolute row index (clamped). */
  function moveCursor(target) {
    const rows = currentRows();
    if (rows.length === 0) return;
    state.cursors[state.view] = clamp(target, 0, rows.length - 1);
    state.scroll[state.view] = 0;
    set({});
  }

  /** Move the list cursor `delta` rows with wrap-around (Torlink movement). */
  function stepCursor(delta) {
    const rows = currentRows();
    if (rows.length === 0) return;
    moveCursor(wrapStep(state.cursors[state.view], delta, rows.length));
  }

  function pageCursor(direction, pageSize) {
    const rows = currentRows();
    if (rows.length === 0) return;
    const size = Math.max(1, pageSize);
    moveCursor(clamp(state.cursors[state.view] + direction * size, 0, rows.length - 1));
  }

  function selectRepositoryById(id) {
    const index = visibleRepositories().findIndex((repo) => repo.id === id);
    if (index < 0) return;
    state.cursors.repositories = index;
    state.scroll.repositories = 0;
    set({ view: "repositories" });
    void loadPrompts(selectedRepository());
  }

  /** Every destination has a detail pane except System, which is one report. */
  function hasDetailPane() {
    return state.view !== "system";
  }

  /**
   * The detail pane is on screen whenever it is a mode that was opened, or the
   * terminal is wide enough to show it side by side (its scroll position is
   * then reachable with `tab` without opening anything first).
   */
  function detailVisible() {
    return hasDetailPane() && (state.inspectorOpen || state.viewport.sideBySide);
  }

  /**
   * Cycle focus between the applicable regions (Torlink's tab). A detail mode
   * that loses focus closes, so focus never rests on a hidden region.
   */
  function cycleFocus() {
    const order = detailVisible() ? ["rail", "list", "inspector"] : ["rail", "list"];
    const current = order.indexOf(state.focus);
    const next = order[wrapStep(current, 1, order.length)];
    const patch = { focus: next };
    if (next !== "inspector" && state.inspectorOpen && !state.viewport.sideBySide) {
      patch.inspectorOpen = false;
    }
    set(patch);
  }

  function setFocus(focus) {
    set({ focus });
  }

  function openInspector() {
    set({ inspectorOpen: true, scroll: { ...state.scroll, [state.view]: 0 } });
  }

  /** Open the detail and hand it the keyboard — the menu's activation target. */
  function enterInspector() {
    set({ inspectorOpen: true, focus: "inspector", scroll: { ...state.scroll, [state.view]: 0 } });
  }

  function closeInspector() {
    set({ inspectorOpen: false, focus: state.focus === "inspector" ? "list" : state.focus });
  }

  /** Menu movement: the selection *is* the active destination, and it wraps. */
  function moveRail(delta) {
    const current = VIEWS.indexOf(state.view);
    switchView(VIEWS[wrapStep(current, delta, VIEWS.length)]);
  }

  /** Back one level (Torlink's esc): detail → list → menu, clearing a filter first. */
  function back() {
    if (state.inspectorOpen) {
      closeInspector();
      return;
    }
    if (state.filter) {
      cancelFilter();
      return;
    }
    if (state.focus !== "rail") setFocus("rail");
  }

  function focusLeft() {
    if (state.focus === "inspector") closeInspector();
    else if (state.focus === "list") setFocus("rail");
  }

  function focusRight() {
    if (state.focus === "rail") setFocus("list");
    else if (state.focus === "list" && detailVisible() && state.viewport.sideBySide) setFocus("inspector");
  }

  /**
   * Scroll one surface by `delta`, clamped to the bound the renderer published.
   * `detail` resolves to the active destination, so every view scrolls its own
   * position and switching destinations never moves another pane.
   */
  function scrollRegion(region, delta, size) {
    const key = region === "detail" ? state.view : region;
    const current = state.scroll[key] ?? 0;
    const max = Math.max(0, size);
    state.scroll[key] = clamp(current + delta, 0, max);
    set({});
  }

  /**
   * Rendered and raw markdown are two views of the same output. The offset is
   * kept across the toggle and clamped by the next frame, so switching does not
   * throw the reader back to the top of a long package.
   */
  function toggleMarkdown() {
    set({ markdownView: state.markdownView === "rendered" ? "raw" : "rendered" });
  }

  function cycleBudget() {
    const index = TOKEN_BUDGETS.indexOf(state.tokenBudget);
    set({ tokenBudget: TOKEN_BUDGETS[(index + 1) % TOKEN_BUDGETS.length] });
  }

  function toggleGraph() {
    set({ includeGraph: !state.includeGraph });
  }

  function startFilter() {
    set({ filterActive: true, focus: "list", filterCursor: state.filter.length });
  }

  function cancelFilter() {
    set({ filterActive: false, filter: "", filterCursor: 0, cursors: { ...state.cursors, [state.view]: 0 } });
  }

  /** Replace the filter text and place the caret — the field keeps a real cursor. */
  function applyFilterText(text, cursor = String(text ?? "").length) {
    const value = stripMouseSequences(text);
    set({
      filter: value,
      filterCursor: clamp(cursor, 0, value.length),
      cursors: { ...state.cursors, [state.view]: 0 },
    });
  }

  /* -------------------------------- overlays -------------------------------- */

  function openOverlay(overlay) {
    set({ overlay });
  }

  /** Close the open overlay; any provider draft belongs to it and goes with it. */
  function closeOverlay() {
    set({ overlay: null, providerDraft: null });
  }

  function openHelp() {
    // The reference sheet opens at the top; its own offset is kept while open.
    openOverlay({ kind: "help" });
    set({ scroll: { ...state.scroll, help: 0 } });
  }

  function openAddRepository() {
    openOverlay({
      kind: "addRepo",
      source: "local",
      field: "path",
      values: { path: "", name: "" },
      cursors: { path: 0, name: 0 },
      error: null,
    });
  }

  function requestDeleteRepository() {
    const repo = selectedRepository();
    if (!repo) return;
    openOverlay({ kind: "confirm", target: { type: "deleteRepository", id: repo.id, label: repo.name } });
  }

  function requestDeletePackage() {
    const row = selectedContextRow();
    if (!row || row.kind !== "package") {
      notice("select a saved package first");
      return;
    }
    openOverlay({ kind: "confirm", target: { type: "deletePackage", id: row.id, label: row.label } });
  }

  function openNewTask() {
    const row = selectedContextRow();
    const prefill = row?.kind === "suggestion" ? row.prompt : "";
    openOverlay({ kind: "newTask", value: prefill, cursor: prefill.length, error: null });
  }

  function openSavePackage() {
    if (!state.context) {
      notice("generate context before saving a package");
      return;
    }
    const value = state.context.task_summary || "Context Package";
    openOverlay({ kind: "savePackage", value, cursor: value.length, error: null });
  }

  async function openPackageViewer(packageId) {
    try {
      const pkg = await client.getContextPackage(packageId);
      // Reading a package never regenerates it and never touches the stored
      // record; the viewer opens at the top of what was already persisted.
      openOverlay({ kind: "viewPackage", package: pkg });
      set({ scroll: { ...state.scroll, viewer: 0 } });
    } catch (error) {
      notice(errorText(error), "error");
    }
  }

  /**
   * The saved-package catalog is a first-class scope of the Context list:
   * `p` switches between tasks/suggestions and packages alone.
   */
  function togglePackageScope() {
    set({
      packageScope: state.packageScope === "packages" ? "all" : "packages",
      cursors: { ...state.cursors, context: 0 },
      scroll: { ...state.scroll, context: 0 },
    });
  }

  /** The package under the cursor, from the catalog or from the open viewer. */
  function selectedPackage() {
    if (state.overlay?.kind === "viewPackage" && state.overlay.package) {
      return { id: state.overlay.package.id, label: state.overlay.package.name };
    }
    const row = selectedContextRow();
    return row && row.kind === "package" ? { id: row.id, label: row.label } : null;
  }

  function openAppendPackage() {
    const target = selectedPackage();
    if (!target) {
      notice("select a saved package first", "warn");
      return;
    }
    openOverlay({ kind: "appendPackage", packageId: target.id, label: target.label, value: "", cursor: 0, error: null, busy: false });
  }

  async function runAppendPackage(packageId, note) {
    const value = String(note ?? "").trim();
    if (!value) {
      overlayError("a task or note is required");
      return;
    }
    set({ overlay: { ...state.overlay, busy: true, error: null } });
    try {
      const updated = await client.appendContextPackage(packageId, { task: value });
      if (updated?.id) {
        state.packages = state.packages.map((pkg) => (pkg.id === updated.id ? updated : pkg));
      }
      set({ overlay: null });
      notice(`appended to ${updated?.name ?? packageId}`);
      // Show the updated package from the append response, then reconcile the
      // catalog with the backend.
      if (updated?.id) await openPackageViewer(updated.id);
      await loadSummary({ quiet: true });
    } catch (error) {
      set({ overlay: { ...state.overlay, busy: false, error: errorText(error) } });
      notice(`append failed: ${errorText(error)}`, "error");
    }
  }

  function openExportPackage() {
    const target = selectedPackage();
    if (!target) {
      notice("select a saved package first", "warn");
      return;
    }
    if (!exportMarkdown) {
      notice("package export is unavailable in this session", "warn");
      return;
    }
    const value = exportFileName(target.label);
    openOverlay({ kind: "exportPackage", packageId: target.id, label: target.label, value, cursor: value.length, error: null, busy: false });
  }

  /**
   * Write the package markdown that is already stored on the backend to a local
   * file. Nothing is regenerated and no backend endpoint is invented — the
   * report names the path that was actually written.
   */
  async function runExportPackage(packageId, target) {
    const destination = String(target ?? "").trim();
    if (!destination) {
      overlayError("export path is required");
      return;
    }
    set({ overlay: { ...state.overlay, busy: true, error: null } });
    try {
      const pkg = await client.getContextPackage(packageId);
      // A missing package is a failure, never an empty file reported as success.
      if (!pkg) throw new Error("package not found");
      const written = await exportMarkdown({ target: destination, markdown: pkg.markdown ?? "", name: pkg.name ?? packageId });
      set({ overlay: null });
      notice(`exported ${pkg.name ?? packageId} to ${written?.path ?? destination}`);
    } catch (error) {
      set({ overlay: { ...state.overlay, busy: false, error: errorText(error) } });
      notice(`export failed: ${errorText(error)}`, "error");
    }
  }

  /* -------------------------------- settings -------------------------------- */

  function openPipelineSettings() {
    // The overlay carries its own item list so the renderer stays a pure
    // presentation layer with no dependency on the state module.
    openOverlay({ kind: "pipelineSettings", items: PIPELINE_SETTINGS, cursor: 0, error: null, busy: false });
  }

  function settingLabel(key) {
    return PIPELINE_SETTINGS.find((item) => item.key === key)?.label ?? key;
  }

  /**
   * Persist one pipeline boolean through POST /settings/cognee and re-read it.
   * There is no Save step: the toggle *is* the commit, and the value shown after
   * it is the one the backend now stores.
   */
  async function toggleSetting(key) {
    if (!PIPELINE_SETTINGS.some((item) => item.key === key)) {
      notice(`${key}: not editable from the TUI`, "warn");
      return;
    }
    if (state.settingsBusy) return;
    const current = Boolean(state.appSettings?.[key]);
    set({ settingsBusy: true, settingsError: null });
    try {
      await client.updateCogneeSettings({ [key]: !current });
      await loadSettings();
      notice(`✓ saved · ${settingLabel(key)} ${current ? "disabled" : "enabled"}`);
    } catch (error) {
      notice(`✗ save failed · ${settingLabel(key)} · ${errorText(error)}`, "error");
      // Keep the failure visible in the overlay that owns the toggle, and re-read
      // the stored value so nothing that was not saved is shown as saved.
      if (state.overlay?.kind === "pipelineSettings") {
        set({ overlay: { ...state.overlay, error: errorText(error) } });
      }
      await loadSettings();
    } finally {
      set({ settingsBusy: false });
    }
  }

  /* ---------------------------- settings reset ------------------------------ */

  /**
   * Reset restores the *mutable* configuration — the settings the HTTP contract
   * persists — to the application defaults the backend resolves from its own
   * configuration source. Nothing else is touched, which is why the overlay says
   * so before the user confirms.
   */
  function requestResetSettings() {
    openOverlay({ kind: "resetSettings", error: null, busy: false });
  }

  async function runResetSettings() {
    if (state.settingsBusy) return;
    set({ settingsBusy: true, settingsError: null, overlay: { ...state.overlay, busy: true, error: null } });
    try {
      const reset = await client.resetSettings();
      closeOverlay();
      // The response is the authoritative read-back; reconcile the runtime facts
      // that qualify it (health/status/provider) with the same values.
      set({ appSettings: reset ?? state.appSettings, settingsError: null });
      await loadProviderContext();
      notice("✓ settings reset to application defaults");
    } catch (error) {
      set({ settingsError: errorText(error) });
      notice(`✗ reset failed · ${errorText(error)}`, "error");
      // Show what is actually stored, never the values the reset would have set.
      await loadSettings();
      if (state.overlay?.kind === "resetSettings") {
        set({ overlay: { ...state.overlay, busy: false, error: errorText(error) } });
      }
    } finally {
      set({ settingsBusy: false });
    }
  }

  /* -------------------------------- clipboard ------------------------------- */

  /**
   * Copy the exact markdown the backend produced. The rendered/raw toggle only
   * changes what is drawn on screen: the clipboard always receives the source
   * Markdown, never terminal escape sequences or reflowed text.
   */
  async function copyMarkdown(markdown, label) {
    const text = typeof markdown === "string" ? markdown : "";
    if (text.trim() === "") {
      notice("nothing to copy: no generated markdown yet", "warn");
      return false;
    }
    if (!copyText) {
      notice("✗ clipboard unavailable · this session has no clipboard adapter", "error");
      return false;
    }
    try {
      const result = await copyText(text, label);
      notice(result?.message ?? (result?.ok ? `✓ copied ${label}` : "✗ clipboard unavailable"), result?.ok ? "info" : "error");
      return Boolean(result?.ok);
    } catch (error) {
      notice(`✗ clipboard unavailable · ${errorText(error)}`, "error");
      return false;
    }
  }

  /** Copy from the generated output view — available as soon as synthesis returned. */
  function copyContext() {
    if (state.operation) {
      notice(
        state.operation.kind === "synthesis"
          ? "synthesis is running · copy is available when it finishes"
          : "an operation is running · copy is available when it finishes",
        "warn"
      );
      return;
    }
    const result = state.context;
    if (!result || typeof result.context_markdown !== "string") {
      notice("nothing to copy: generate context first", "warn");
      return;
    }
    void copyMarkdown(result.context_markdown, "the generated markdown");
  }

  /** Copy the stored markdown of the package open in the viewer. */
  function copyPackage() {
    const pkg = state.overlay?.kind === "viewPackage" ? state.overlay.package : null;
    if (!pkg) {
      notice("open a saved package first", "warn");
      return;
    }
    if (typeof pkg.markdown !== "string" || pkg.markdown.trim() === "") {
      notice(`nothing to copy: ${pkg.name ?? pkg.id ?? "this package"} has no stored markdown`, "warn");
      return;
    }
    void copyMarkdown(pkg.markdown, `“${pkg.name ?? pkg.id}”`);
  }

  /* ---------------------------- provider + models --------------------------- */

  /** The authoritative persisted provider/model, for the saved-vs-chosen split. */
  function savedProviderIdentity() {
    const settings = state.appSettings ?? {};
    const provider =
      settings.llm_provider ?? state.providerStatus?.provider ?? state.health?.provider_identity ?? PROVIDER_OPTIONS[1];
    const endpoint = settings.llm_endpoint ?? state.providerStatus?.base_url ?? PROVIDER_ENDPOINTS[provider] ?? "";
    const model = settings.llm_model ?? state.health?.configured_model ?? state.status?.configured_model ?? null;
    return { provider, endpoint: String(endpoint ?? ""), model: model ? String(model) : null };
  }

  /**
   * The discovery result that belongs to the draft on screen. Discovery is keyed
   * on provider + endpoint so a result for another endpoint can never validate a
   * commit for this one.
   */
  function modelsForDraft(draft) {
    const models = state.models ?? {};
    const endpoint = String(draft?.values?.endpoint ?? "").trim();
    if (models.endpoint !== endpoint || models.provider !== draft?.values?.provider) return null;
    return models;
  }

  /** The provider's own list for the draft, and only when it actually answered. */
  function discoveredModels(draft) {
    const models = modelsForDraft(draft);
    return models && models.state === "ready" ? models.items ?? [] : [];
  }

  function modelInList(draft, label) {
    if (!label) return null;
    return discoveredModels(draft).find((model) => model.label === label) ?? null;
  }

  /**
   * The model a commit would persist: the one chosen in the selector, or the
   * stored one while the provider still reports it. Null means the configuration
   * cannot be written — RE:Track never saves a model the endpoint did not report.
   */
  function committableModel(draft) {
    return modelInList(draft, draft?.selected?.label) ?? modelInList(draft, draft?.saved?.model);
  }

  /** Why a commit cannot proceed, in the backend's own words when it gave any. */
  function commitFailureReason(models) {
    const current = models ?? state.models ?? {};
    if (current.state === "idle" || current.state === "loading") return "still reading the provider's models";
    if (current.state === "empty") {
      return current.message ? `the provider reported no models · ${current.message}` : "the provider reported no models";
    }
    if (current.state === "failed") return current.message ?? "the provider could not be read";
    return "select a model from the provider's list";
  }

  /** The discovery probe in flight, so a commit can wait for the answer it needs. */
  let discoveryInFlight = null;

  /**
   * Discover the models the provider endpoint actually serves
   * (POST /provider/discover). Nothing is invented here: the list is whatever
   * the endpoint returned, and a provider that cannot enumerate them keeps the
   * backend's own status/message so the UI can say why.
   */
  async function discoverModels({ provider, endpoint, apiKey }) {
    const baseUrl = String(endpoint ?? "").trim();
    const run = (async () => {
      if (!baseUrl) {
        set({
          models: {
            state: "failed",
            provider,
            endpoint: baseUrl,
            status: "not_configured",
            items: [],
            message: "Provider endpoint URL is not configured.",
            errorDetails: null,
          },
        });
        return;
      }
      set({ models: { state: "loading", provider, endpoint: baseUrl, status: null, items: [], message: null, errorDetails: null } });
      try {
        const result = await client.discoverProvider({ provider, base_url: baseUrl, api_key: String(apiKey ?? "").trim() || "local" });
        const items = (Array.isArray(result?.models) ? result.models : [])
          .map((model) => ({
            id: model?.model_id ?? null,
            label: model?.name || model?.model_id || null,
            quantization: model?.quantization ?? null,
            warning: model?.warning ?? null,
          }))
          .filter((model) => model.label);
        const status = String(result?.status ?? "");
        const failed = ["unreachable", "discovery_failed", "not_configured"].includes(status);
        set({
          models: {
            state: items.length > 0 ? "ready" : failed ? "failed" : "empty",
            provider,
            endpoint: baseUrl,
            status: status || null,
            items,
            message: result?.message ?? null,
            errorDetails: result?.error_details ?? null,
          },
        });
      } catch (error) {
        set({
          models: {
            state: "failed",
            provider,
            endpoint: baseUrl,
            status: null,
            items: [],
            message: errorText(error),
            errorDetails: null,
          },
        });
      }
      dropStaleSelection({ provider, endpoint: baseUrl });
    })();

    discoveryInFlight = { provider, endpoint: baseUrl, promise: run };
    try {
      await run;
    } finally {
      if (discoveryInFlight?.promise === run) discoveryInFlight = null;
    }
  }

  /**
   * A model chosen for one provider/endpoint is not that provider's model: when
   * the answer for the draft arrives without it, the choice is cleared instead of
   * being carried into a configuration the endpoint never reported.
   */
  function dropStaleSelection({ provider, endpoint }) {
    const draft = state.providerDraft;
    if (!draft) return;
    if (draft.values.provider !== provider || String(draft.values.endpoint).trim() !== endpoint) return;
    const items = state.models.items ?? [];
    if (state.models.state !== "ready") return;
    const chosen = draft.selected?.label;
    if (chosen && !items.some((model) => model.label === chosen)) {
      set({ providerDraft: { ...draft, selected: null } });
    }
  }

  /**
   * Have an answer for the draft's provider + endpoint before a commit validates
   * against it: wait for the probe already running, or start one.
   */
  async function ensureModels(draft) {
    const endpoint = String(draft?.values?.endpoint ?? "").trim();
    if (!endpoint) return null;
    const inFlight = discoveryInFlight;
    if (inFlight && inFlight.provider === draft.values.provider && inFlight.endpoint === endpoint) {
      await inFlight.promise;
    }
    const current = modelsForDraft(state.providerDraft);
    if (!current || current.state === "idle" || current.state === "loading") {
      await discoverModels({
        provider: state.providerDraft.values.provider,
        endpoint: String(state.providerDraft.values.endpoint ?? "").trim(),
        apiKey: state.providerDraft.values.apiKey,
      });
    }
    return modelsForDraft(state.providerDraft);
  }

  /**
   * Provider configuration is a real HTTP mutation (POST /provider/update) that
   * writes provider, endpoint, API key and model as one configuration. The
   * Settings view exposes it rather than claiming it is GUI-only. The draft is
   * prefilled from the persisted settings, the model comes from the provider's
   * own list (never typed), and every value is re-read after saving.
   */
  function openProviderSettings() {
    const saved = savedProviderIdentity();
    set({
      providerDraft: {
        // The overlay carries its own option list so the renderer stays pure.
        options: PROVIDER_OPTIONS,
        field: "provider",
        values: { provider: saved.provider, endpoint: saved.endpoint, apiKey: "" },
        cursors: { endpoint: saved.endpoint.length, apiKey: 0 },
        saved,
        // Chosen here; the stored model stays the stored model until a choice is
        // made, and choosing is what persists it (there is no separate save).
        selected: null,
        endpointEdited: false,
        error: null,
        busy: false,
      },
      overlay: { kind: "providerSettings" },
    });
    void discoverModels({ provider: saved.provider, endpoint: saved.endpoint, apiKey: "" });
  }

  function closeProviderEditor() {
    closeOverlay();
  }

  /** Back from the selector to the editor it belongs to — the draft survives. */
  function closeModelSelect() {
    if (state.providerDraft) set({ overlay: { kind: "providerSettings" } });
    else closeOverlay();
  }

  /**
   * Switching provider switches the model list with it: the previous selection is
   * dropped here and again if the answer for the new endpoint does not include it
   * (dropStaleSelection), and the new provider is queried for what it serves.
   * Nothing is persisted by highlighting a provider: a commit carries a
   * provider-reported model, so it is the model choice that writes both.
   */
  function applyProvider(provider) {
    const draft = state.providerDraft;
    if (!draft) return;
    const values = draft.values;
    const endpoint =
      values.endpoint === "" || !draft.endpointEdited
        ? PROVIDER_ENDPOINTS[provider] ?? values.endpoint
        : values.endpoint;
    set({
      providerDraft: {
        ...draft,
        values: { ...values, provider, endpoint },
        cursors: { ...draft.cursors, endpoint: endpoint.length },
        selected: null,
        error: null,
      },
    });
    void discoverModels({ provider, endpoint, apiKey: values.apiKey });
  }

  /** Tab/enter on the provider row: cycle to the next supported provider. */
  function cycleProviderField() {
    const draft = state.providerDraft;
    if (!draft) return;
    const index = PROVIDER_OPTIONS.indexOf(draft.values.provider);
    applyProvider(PROVIDER_OPTIONS[wrapStep(index, 1, PROVIDER_OPTIONS.length)]);
  }

  /** Re-read the endpoint without changing anything (the probe never mutates). */
  async function runProbeProvider() {
    const draft = state.providerDraft;
    if (!draft) return;
    const endpoint = draft.values.endpoint.trim();
    if (!endpoint) {
      overlayError("endpoint is required before probing");
      return;
    }
    await discoverModels({ provider: draft.values.provider, endpoint, apiKey: draft.values.apiKey });
    const models = state.models;
    if (models.state === "ready") notice(`discovered ${models.items.length} models`);
    else notice(`model discovery: ${models.message ?? models.status ?? "no models"}`, models.state === "empty" ? "warn" : "error");
  }

  /* ----------------------------- model selector ----------------------------- */

  /**
   * The selector lists the provider's own models and nothing else. It filters
   * the returned list only — there is no field that could name a model the
   * provider never reported.
   */
  function openModelSelect() {
    const draft = state.providerDraft;
    if (!draft) return;
    const items = state.models.items ?? [];
    const wanted = draft.selected?.label ?? draft.saved.model;
    const index = items.findIndex((model) => model.label === wanted || model.id === draft.selected?.id);
    set({ overlay: { kind: "modelSelect", cursor: index >= 0 ? index : 0, filter: "", filterActive: false } });
    if (state.models.state === "idle" || state.models.endpoint !== draft.values.endpoint) {
      void discoverModels({ provider: draft.values.provider, endpoint: draft.values.endpoint, apiKey: draft.values.apiKey });
    }
  }

  /** The provider models matching the selector's filter (a filter, never an input). */
  function visibleModels() {
    const items = state.models.items ?? [];
    const filter = state.overlay?.kind === "modelSelect" ? String(state.overlay.filter ?? "").trim().toLowerCase() : "";
    if (!filter) return items;
    return items.filter((model) => `${model.label} ${model.id ?? ""}`.toLowerCase().includes(filter));
  }

  /**
   * Choosing is committing: the selected model is written through
   * POST /provider/update together with the provider it belongs to, and the
   * authoritative values are re-read. Merely highlighting a row in the list
   * persists nothing.
   */
  function selectModel(model) {
    const draft = state.providerDraft;
    if (!draft || !model) return;
    set({
      providerDraft: { ...draft, selected: { id: model.id, label: model.label, quantization: model.quantization ?? null, warning: model.warning ?? null }, error: null },
      overlay: { kind: "providerSettings" },
    });
    void runUpdateProvider();
  }

  /**
   * Commit the provider configuration. POST /provider/update is the only write,
   * and it always carries a model this endpoint reported, so a provider change
   * can never be persisted as an invalid provider/model combination.
   */
  async function runUpdateProvider() {
    const draft = state.providerDraft;
    if (!draft || draft.busy) return;
    const endpoint = state.providerDraft.values.endpoint.trim();
    if (!endpoint) {
      overlayError("endpoint is required");
      return;
    }

    const models = await ensureModels(state.providerDraft);
    const current = state.providerDraft;
    if (!current) return;
    const model = committableModel(current);
    if (!model) {
      const reason = commitFailureReason(models);
      overlayError(reason);
      notice(`✗ provider not saved · ${reason}`, "error");
      return;
    }

    set({ providerDraft: { ...state.providerDraft, busy: true, error: null } });
    try {
      await client.updateProvider({
        provider: current.values.provider,
        base_url: endpoint,
        model: model.label,
        api_key: current.values.apiKey.trim() || "local",
      });
      closeProviderEditor();
      notice(`✓ provider updated · ${current.values.provider} · ${model.label}`);
      await loadProviderContext();
    } catch (error) {
      const active = state.providerDraft;
      if (active) set({ providerDraft: { ...active, busy: false, error: errorText(error) } });
      notice(`✗ save failed · provider · ${errorText(error)}`, "error");
    }
  }

  function overlayError(message) {
    const overlay = state.overlay;
    if (!overlay) return;
    if (overlay.kind === "providerSettings" && state.providerDraft) {
      set({ providerDraft: { ...state.providerDraft, error: message } });
      return;
    }
    set({ overlay: { ...overlay, error: message } });
  }

  /* ------------------------------- re-synthesis ------------------------------ */

  /** The package a re-synthesis would regenerate: the open viewer, else the catalog row. */
  function resynthesisSource() {
    if (state.overlay?.kind === "viewPackage" && state.overlay.package) return state.overlay.package;
    const row = selectedContextRow();
    if (!row || row.kind !== "package") return null;
    return state.packages.find((item) => item.id === row.id) ?? { id: row.id, name: row.label };
  }

  /** The registered repository a package belongs to, by id and then by name. */
  function repositoryForPackage(pkg) {
    const repositories = state.repositories ?? [];
    const byId = pkg?.repository_id ? repositories.find((repo) => repo.id === pkg.repository_id) : null;
    const byName = pkg?.repository_name ? repositories.find((repo) => repo.name === pkg.repository_name) : null;
    return byId ?? byName ?? null;
  }

  /**
   * Everything a regeneration needs, resolved and validated before it starts.
   *
   * The basis is the package's own stored definition — never the row that happens
   * to be selected in the context list. Generation options are the current
   * Context settings (token budget, AST graph), because the package record does
   * not store the configuration it was generated with; they are shown before the
   * run so the basis is never implicit.
   */
  function resynthesisPlan(pkg) {
    if (!pkg?.id) return { error: "select a saved package first" };
    const task = String(pkg.task || pkg.objective || "").trim();
    if (!task) return { error: `${pkg.name ?? pkg.id}: the package stores no task to regenerate` };
    const repo = repositoryForPackage(pkg);
    if (!repo) {
      return {
        error: `${pkg.name ?? pkg.id}: repository ${pkg.repository_name || pkg.repository_id || "unknown"} is not registered here`,
      };
    }
    return {
      packageId: pkg.id,
      name: pkg.name || pkg.id,
      task,
      repo,
      objective: pkg.objective ?? "",
      maxTokens: state.tokenBudget,
      includeStructuralGraph: state.includeGraph,
      repository: `${repo.name}${pkg.repository_branch ? ` · ${pkg.repository_branch}` : ""}`,
      storedTokens: pkg.token_estimate ?? null,
      storedUpdatedAt: pkg.updated_at ?? null,
    };
  }

  function requestResynthesize() {
    if (state.operation) {
      notice(
        state.operation.kind === "synthesis" ? "a synthesis is already running" : "another operation is in progress",
        "warn"
      );
      return;
    }
    const plan = resynthesisPlan(resynthesisSource());
    if (plan.error) {
      notice(plan.error, "warn");
      return;
    }
    // Only a run started from the viewer carries it: cancelling (and a failed
    // regeneration) returns to the package the reader was already reading,
    // while a run started from the catalog closes back onto the catalog.
    const source = state.overlay?.kind === "viewPackage" ? state.overlay.package : null;
    openOverlay({ kind: "resynthesize", plan, source, error: null, busy: false });
  }

  /**
   * Regenerate a package from its stored task and repository against the current
   * repository, evidence and configuration.
   *
   * Failure safety is the point of the order here: generation happens first, the
   * replacement is written only once a non-empty result exists, and the record is
   * re-read afterwards so the viewer shows what was actually persisted. A failure
   * at any step leaves the previously stored package exactly as it was, and no
   * second package is ever created.
   */
  async function runResynthesize(plan, source = null) {
    if (!plan) return;
    if (state.operation) {
      notice("another operation is in progress", "warn");
      return;
    }

    closeOverlay();
    set({
      operation: {
        kind: "synthesis",
        repoId: plan.repo.id,
        repoName: plan.repo.name,
        packageId: plan.packageId,
        packageName: plan.name,
        reSynthesis: true,
        startedAt: now(),
        runtimeState: "submitting",
      },
      contextError: null,
    });

    let stored = false;
    try {
      const response = await client.agentContext({
        taskPrompt: plan.task,
        repositoryPath: plan.repo.local_path,
        datasetName: plan.repo.name,
        maxTokens: plan.maxTokens,
        includeStructuralGraph: plan.includeStructuralGraph,
      });
      const markdown = typeof response?.context_markdown === "string" ? response.context_markdown : "";
      if (response?.success === false || markdown.trim() === "") {
        throw new Error("the regeneration returned no context");
      }

      await client.replaceContextPackage(plan.packageId, {
        markdown,
        objective: response.task_summary || undefined,
        token_estimate: response.estimated_tokens ?? undefined,
        total_time_ms: response.generation_time_ms ?? response.total_time_ms ?? undefined,
        repository_commit: plan.repo.commit_hash || undefined,
      });
      stored = true;

      // Re-read the stored record: the viewer then shows what the backend holds,
      // and the catalog is reconciled from the same authoritative read.
      const updated = await client.getContextPackage(plan.packageId);
      if (updated?.id) {
        state.packages = state.packages.map((pkg) => (pkg.id === updated.id ? updated : pkg));
        // The viewer the run was started from is reopened on the regenerated
        // record; its scroll offset is untouched, so the reader keeps their place.
        if (source) set({ overlay: { kind: "viewPackage", package: updated } });
      }
      notice(`✓ re-synthesized ${plan.name} · ${updated?.token_estimate ?? "unavailable"} tokens`);
      await loadSummary({ quiet: true });
    } catch (error) {
      notice(
        `✗ re-synthesis failed · ${errorText(error)} · ${
          stored ? `${plan.name} was updated but could not be reloaded` : `${plan.name} is unchanged`
        }`,
        "error"
      );
      // The stored package is unchanged: show it as it is, so a failed
      // regeneration leaves the reader where they were with a usable package.
      await reopenUnchanged(source, plan);
    } finally {
      set({ operation: null });
    }
  }

  /**
   * Re-read a package that survived a failed regeneration. Only a run started
   * from the viewer reopens it: a run started from the catalog leaves the reader
   * where they were, and either way the stored record is untouched.
   */
  async function reopenUnchanged(source, plan) {
    if (!source) return;
    try {
      const stored = await client.getContextPackage(plan.packageId);
      if (!stored) return;
      state.packages = state.packages.map((pkg) => (pkg.id === stored.id ? stored : pkg));
      openOverlay({ kind: "viewPackage", package: stored });
    } catch {
      // Reporting the failed regeneration is what matters; the catalog already
      // holds the untouched package.
    }
  }

  /* ------------------------------- operations ------------------------------- */

  async function runIndex(repo) {
    if (state.operation) {
      notice(
        state.operation.kind === "indexing"
          ? `indexing already in progress: ${state.operation.repoName ?? state.operation.repoId}`
          : "another operation is in progress",
        "warn"
      );
      return;
    }
    if (!repo) {
      notice("no repository selected", "warn");
      return;
    }

    const startedAt = now();
    set({
      operation: {
        kind: "indexing",
        repoId: repo.id,
        repoName: repo.name,
        startedAt,
        external: false,
        stage: "submitting",
        stageIndex: null,
        stageTotal: null,
        processedFiles: null,
        totalFiles: null,
        failedFiles: null,
        elapsedMs: 0,
      },
      progress: null,
      lastRun: null,
    });

    try {
      const result = await client.indexRepository({
        repositoryPath: repo.local_path,
        datasetName: repo.name,
        forceReindex: true,
      });
      const ok = Boolean(result?.success);
      set({
        lastRun: {
          kind: "indexing",
          repoId: repo.id,
          repoName: repo.name,
          status: ok ? "indexed" : "error",
          stage: result?.summary ?? (ok ? "completed" : "failed"),
          processedFiles: result?.processed_files ?? null,
          totalFiles: result?.total_files ?? null,
          failedFiles: result?.failed_files ?? null,
          elapsedMs: now() - startedAt,
          finishedAt: now(),
        },
      });
      const failed = result?.failed_files ?? 0;
      notice(
        ok
          ? `indexed ${repo.name} · ${result?.processed_files ?? 0}/${result?.total_files ?? 0} files${failed > 0 ? ` · ${failed} failed` : ""}`
          : `indexing failed: ${result?.summary ?? "unknown error"}`,
        ok ? "info" : "error"
      );
    } catch (error) {
      set({
        lastRun: {
          kind: "indexing",
          repoId: repo.id,
          repoName: repo.name,
          status: "error",
          stage: errorText(error),
          elapsedMs: now() - startedAt,
          finishedAt: now(),
        },
      });
      notice(`indexing failed: ${errorText(error)}`, "error");
    } finally {
      // Reconcile with the backend before dropping the operation state: the
      // refreshed repository record is the authority for the completion line.
      await loadSummary({ quiet: true });
      set({ operation: null, progress: null });
    }
  }

  async function runScan(repo) {
    if (!repo) {
      notice("no repository selected", "warn");
      return;
    }
    try {
      const result = await client.scanRepository(repo.id);
      notice(
        `scanned ${repo.name} · ${result?.file_count ?? "unavailable"} files · ${(result?.languages ?? []).join(", ") || "no languages detected"}`
      );
      await loadSummary({ quiet: true });
    } catch (error) {
      notice(`scan failed: ${errorText(error)}`, "error");
    }
  }

  async function runImport({ sourceType, target, name }) {
    try {
      const created = await client.createRepository({
        sourceType,
        ...(sourceType === "github" ? { sourceUrl: target } : { localPath: target }),
        // An empty name is omitted rather than sent as "": the backend already
        // derives a name from the path when none is provided.
        name: name || undefined,
      });
      closeOverlay();
      notice(`added ${created?.name ?? target}`);
      await loadSummary({ quiet: true });
      if (created?.id) selectRepositoryById(created.id);
      try {
        await client.scanRepository(created.id);
        await loadSummary({ quiet: true });
      } catch (error) {
        notice(`added ${created?.name ?? target} · scan failed: ${errorText(error)}`, "warn");
      }
    } catch (error) {
      overlayError(errorText(error));
      notice(`import failed: ${errorText(error)}`, "error");
    }
  }

  async function runDelete(target) {
    try {
      if (target.type === "deleteRepository") {
        await client.deleteRepository(target.id);
        closeOverlay();
        notice(`deleted ${target.label}`);
        await loadSummary({ quiet: true });
      } else {
        await client.deleteContextPackage(target.id);
        closeOverlay();
        notice(`package deleted: ${target.label}`);
        state.packages = state.packages.filter((pkg) => pkg.id !== target.id);
        set({});
      }
    } catch (error) {
      closeOverlay();
      notice(`delete failed: ${errorText(error)}`, "error");
    }
  }

  async function runSynthesis(task) {
    if (state.operation) {
      notice("another operation is in progress", "warn");
      return;
    }
    const repo = selectedRepository();
    if (!repo) {
      notice("no repository selected", "warn");
      return;
    }
    const prompt = String(task ?? "").trim();
    if (!prompt) {
      notice("task prompt is required", "warn");
      return;
    }

    closeOverlay();
    set({
      operation: { kind: "synthesis", repoId: repo.id, repoName: repo.name, startedAt: now(), runtimeState: "submitting" },
      contextError: null,
    });

    try {
      const response = await client.agentContext({
        taskPrompt: prompt,
        repositoryPath: repo.local_path,
        datasetName: repo.name,
        maxTokens: state.tokenBudget,
        includeStructuralGraph: state.includeGraph,
      });
      set({ context: response, contextError: response?.success === false ? "synthesis did not succeed" : null });
      if (response?.success === false) notice("synthesis did not succeed", "warn");
    } catch (error) {
      set({ context: null, contextError: errorText(error) });
      notice(`synthesis failed: ${errorText(error)}`, "error");
    } finally {
      set({ operation: null });
    }
  }

  async function runSavePackage(name) {
    const label = String(name ?? "").trim();
    if (!label) {
      overlayError("package name is required");
      return;
    }
    const repo = selectedRepository();
    const result = state.context;
    closeOverlay();
    try {
      const saved = await client.saveContextPackage({
        name: label,
        task: result.task_summary ?? "",
        objective: result.task_summary ?? "",
        repository_id: repo?.id ?? "",
        repository_name: repo?.name ?? "",
        repository_branch: repo?.branch ?? "",
        repository_commit: repo?.commit_hash ?? "",
        markdown: result.context_markdown ?? "",
        token_estimate: result.estimated_tokens ?? 0,
        total_time_ms: result.generation_time_ms ?? 0,
      });
      notice(`package saved: ${saved?.name ?? label}`);
      state.packages = [saved, ...state.packages.filter((pkg) => pkg.id !== saved?.id)];
      // The saved package becomes immediately selectable in the catalog.
      set({ packageScope: "packages", cursors: { ...state.cursors, context: 0 } });
    } catch (error) {
      notice(`save failed: ${errorText(error)}`, "error");
    }
  }

  async function runExportDiagnostics() {
    try {
      const result = await client.exportDiagnostics();
      notice(`diagnostics exported: ${result?.export_path ?? "unavailable"}`);
    } catch (error) {
      notice(`export failed: ${errorText(error)}`, "error");
    }
  }

  /* ------------------------------- dispatch -------------------------------- */

  function overlayEditorTarget() {
    const overlay = state.overlay;
    if (!overlay) return null;
    if (["newTask", "savePackage", "appendPackage", "exportPackage"].includes(overlay.kind)) {
      return { kind: "single", get: () => overlay, apply: (next) => set({ overlay: { ...overlay, ...next } }) };
    }
    if (overlay.kind === "providerSettings") {
      const draft = state.providerDraft;
      if (!draft) return null;
      const field = draft.field;
      // `provider` cycles and `model` opens the provider's list: neither is a
      // text field, so no typed model name can ever reach the backend.
      if (!field || field === "provider" || field === "model") return null;
      return {
        kind: "field",
        get: () => ({ value: draft.values[field], cursor: draft.cursors[field] }),
        apply: ({ value, cursor }) =>
          set({
            providerDraft: {
              ...state.providerDraft,
              // Once the endpoint is touched, cycling providers keeps it.
              endpointEdited: field === "endpoint" ? true : draft.endpointEdited,
              values: { ...draft.values, [field]: value },
              cursors: { ...draft.cursors, [field]: cursor },
            },
          }),
      };
    }
    if (overlay.kind === "addRepo") {
      const field = overlay.field;
      return {
        kind: "field",
        get: () => ({ value: overlay.values[field], cursor: overlay.cursors[field] }),
        apply: ({ value, cursor }) =>
          set({
            overlay: {
              ...overlay,
              values: { ...overlay.values, [field]: value },
              cursors: { ...overlay.cursors, [field]: cursor },
            },
          }),
      };
    }
    return null;
  }

  function dispatchEditorKey(intent, target) {
    // Rows that are not text fields (the provider's provider/model rows) have no
    // editor target: a keystroke there is a no-op, never an input.
    if (!target) return false;
    const names = {
      backspace: { type: "backspace" },
      left: { type: "left" },
      right: { type: "right" },
      home: { type: "home" },
      end: { type: "end" },
    };
    if (intent.name === "ctrl" && ["u", "w", "k", "a", "e"].includes(intent.char)) {
      const map = { u: { type: "clear" }, w: { type: "deleteWord" }, k: { type: "killToEnd" }, a: { type: "home" }, e: { type: "end" } };
      target.apply(applyEdit(target.get(), map[intent.char]));
      return true;
    }
    if (names[intent.name]) {
      target.apply(applyEdit(target.get(), names[intent.name]));
      return true;
    }
    if (intent.name === "char") {
      target.apply(applyEdit(target.get(), { type: "insert", text: intent.char }));
      return true;
    }
    if (intent.name === "space") {
      target.apply(applyEdit(target.get(), { type: "insert", text: " " }));
      return true;
    }
    return false;
  }

  function handleOverlayKey(intent) {
    const overlay = state.overlay;
    if (!overlay) return undefined;

    /**
     * Movement inside a region that also owns text fields: ↑↓ always move
     * between fields, while the j/k aliases are ordinary characters whenever a
     * field holds the keyboard.
     */
    const fieldDelta = (intent, editing) => {
      const alias = intent.name === "char" && (intent.char === "j" || intent.char === "k");
      return editing && alias ? 0 : moveDelta(intent);
    };


    if (overlay.kind === "help") {
      // The reference sheet scrolls with its own offset; every other key
      // dismisses it (Torlink). It is never clipped, only windowed.
      const max = state.viewport.helpMax;
      const page = state.viewport.helpPage;
      const delta = moveDelta(intent);
      if (delta !== 0) scrollRegion("help", delta, max);
      else if (intent.name === "pageUp") scrollRegion("help", -page, max);
      else if (intent.name === "pageDown") scrollRegion("help", page, max);
      else if (intent.name === "home") scrollRegion("help", -(state.scroll.help ?? 0), max);
      else if (intent.name === "end") scrollRegion("help", max, max);
      else if (intent.name !== "unknown") closeOverlay();
      return undefined;
    }

    if (overlay.kind === "confirm") {
      if (intent.name === "enter") {
        void runDelete(overlay.target);
        return undefined;
      }
      if (intent.name === "escape") closeOverlay();
      return undefined;
    }

    if (overlay.kind === "resetSettings") {
      // Reset is a real mutation of the stored configuration: it is confirmed
      // explicitly, and the overlay stays open while it runs.
      if (intent.name === "enter" && !overlay.busy) void runResetSettings();
      else if (intent.name === "escape" && !overlay.busy) closeOverlay();
      return undefined;
    }

    if (overlay.kind === "resynthesize") {
      // Regeneration replaces stored content, so it is confirmed with the basis
      // on screen (task, repository, generation options) before it runs.
      if (intent.name === "enter" && !overlay.busy) void runResynthesize(overlay.plan, overlay.source ?? null);
      else if (intent.name === "escape" && !overlay.busy) {
        // Cancelling returns to the package the confirmation was opened from.
        if (overlay.source) set({ overlay: { kind: "viewPackage", package: overlay.source } });
        else closeOverlay();
      }
      return undefined;
    }

    if (overlay.kind === "viewPackage") {
      // Reading a package is a pure scroll: no regeneration, no backend call,
      // and the offset survives the rendered/raw toggle. Copy hands over the
      // stored markdown verbatim; re-synthesis regenerates it.
      const max = state.viewport.viewerMax;
      const page = state.viewport.viewerPage;
      const delta = moveDelta(intent);
      if (intent.name === "escape") closeOverlay();
      else if (intent.name === "char" && intent.char === "m") toggleMarkdown();
      else if (intent.name === "char" && intent.char === "c") copyPackage();
      else if (intent.name === "char" && intent.char === "r") requestResynthesize();
      else if (intent.name === "char" && intent.char === "a") openAppendPackage();
      else if (intent.name === "char" && intent.char === "e") openExportPackage();
      else if (delta !== 0) scrollRegion("viewer", delta, max);
      else if (intent.name === "pageDown") scrollRegion("viewer", page, max);
      else if (intent.name === "pageUp") scrollRegion("viewer", -page, max);
      else if (intent.name === "home") scrollRegion("viewer", -(state.scroll.viewer ?? 0), max);
      else if (intent.name === "end") scrollRegion("viewer", max, max);
      return undefined;
    }

    if (overlay.kind === "modelSelect") {
      // The selector lists only models the provider returned. `/` filters that
      // list — it can never name a model the provider did not report.
      const models = visibleModels();
      const count = models.length;
      const page = Math.max(1, state.viewport.modelPage);
      const filter = String(overlay.filter ?? "");
      if (overlay.filterActive) {
        if (intent.name === "escape") set({ overlay: { ...overlay, filterActive: false, filter: "", cursor: 0 } });
        else if (intent.name === "enter") set({ overlay: { ...overlay, filterActive: false, cursor: 0 } });
        else if (intent.name === "down") set({ overlay: { ...overlay, filterActive: false } });
        else {
          dispatchEditorKey(intent, {
            kind: "field",
            get: () => ({ value: filter, cursor: overlay.filterCursor ?? filter.length }),
            apply: ({ value, cursor }) =>
              set({ overlay: { ...overlay, filter: value, filterCursor: cursor, cursor: 0 } }),
          });
        }
        return undefined;
      }
      const delta = moveDelta(intent);
      const cursor = clamp(overlay.cursor ?? 0, 0, Math.max(0, count - 1));
      // esc clears an applied filter first, then walks back to the editor — the
      // same rule the list filter follows.
      if (intent.name === "escape") {
        if (filter) set({ overlay: { ...overlay, filter: "", filterActive: false, cursor: 0 } });
        else closeModelSelect();
      }
      else if (intent.name === "char" && intent.char === "/") set({ overlay: { ...overlay, filterActive: true, filterCursor: filter.length } });
      else if (delta !== 0 && count > 0) set({ overlay: { ...overlay, cursor: wrapStep(cursor, delta, count) } });
      else if (intent.name === "pageUp") set({ overlay: { ...overlay, cursor: clamp(cursor - page, 0, Math.max(0, count - 1)) } });
      else if (intent.name === "pageDown") set({ overlay: { ...overlay, cursor: clamp(cursor + page, 0, Math.max(0, count - 1)) } });
      else if (intent.name === "home") set({ overlay: { ...overlay, cursor: 0 } });
      else if (intent.name === "end") set({ overlay: { ...overlay, cursor: Math.max(0, count - 1) } });
      else if (intent.name === "enter" && count > 0) selectModel(models[cursor]);
      return undefined;
    }

    if (overlay.kind === "providerSettings") {
      const draft = state.providerDraft;
      if (!draft) {
        closeOverlay();
        return undefined;
      }
      const busy = draft.busy;
      const delta = fieldDelta(intent, Boolean(overlayEditorTarget()));
      if (intent.name === "escape") {
        closeProviderEditor();
        return undefined;
      }
      if (delta !== 0) {
        const index = PROVIDER_FIELDS.indexOf(draft.field);
        const next = PROVIDER_FIELDS[wrapStep(index < 0 ? 0 : index, delta, PROVIDER_FIELDS.length)];
        set({ providerDraft: { ...draft, field: next } });
        return undefined;
      }
      if (intent.name === "tab") {
        cycleProviderField();
        return undefined;
      }
      if (intent.name === "ctrl" && intent.char === "p" && !busy) {
        void runProbeProvider();
        return undefined;
      }
      if (intent.name === "enter" && !busy) {
        // The model row opens the provider's own model list; every other row
        // submits the form.
        if (draft.field === "model") openModelSelect();
        else void runUpdateProvider();
        return undefined;
      }
      dispatchEditorKey(intent, overlayEditorTarget());
      return undefined;
    }

    if (overlay.kind === "pipelineSettings") {
      const count = PIPELINE_SETTINGS.length;
      const delta = moveDelta(intent);
      if (intent.name === "escape") {
        closeOverlay();
        return undefined;
      }
      if (delta !== 0) set({ overlay: { ...overlay, cursor: wrapStep(overlay.cursor ?? 0, delta, count) } });
      else if (intent.name === "enter" || intent.name === "space") {
        const setting = PIPELINE_SETTINGS[clamp(overlay.cursor ?? 0, 0, count - 1)];
        if (setting) void toggleSetting(setting.key);
      }
      return undefined;
    }

    // Form-like overlays own ↑↓ for their fields/items, so their content pages
    // with PgUp/PgDn — and with Home/End whenever no text field owns the caret.
    // The bound comes from the rendered overlay, so nothing is ever clipped.
    if (intent.name === "pageUp") {
      scrollRegion("overlay", -state.viewport.overlayPage, state.viewport.overlayMax);
      return undefined;
    }
    if (intent.name === "pageDown") {
      scrollRegion("overlay", state.viewport.overlayPage, state.viewport.overlayMax);
      return undefined;
    }
    if ((intent.name === "home" || intent.name === "end") && !overlayEditorTarget()) {
      scrollRegion(
        "overlay",
        intent.name === "home" ? -(state.scroll.overlay ?? 0) : state.viewport.overlayMax,
        state.viewport.overlayMax
      );
      return undefined;
    }

    if (overlay.kind === "addRepo") {
      if (intent.name === "escape") {
        closeOverlay();
        return undefined;
      }
      if (intent.name === "tab" || (intent.name === "char" && intent.char === "s")) {
        set({ overlay: { ...overlay, source: overlay.source === "local" ? "github" : "local" } });
        return undefined;
      }
      if (fieldDelta(intent, Boolean(overlayEditorTarget())) !== 0) {
        set({ overlay: { ...overlay, field: overlay.field === "path" ? "name" : "path" } });
        return undefined;
      }
      if (intent.name === "enter") {
        const target = overlay.values.path.trim();
        const name = overlay.values.name.trim();
        if (!target) {
          overlayError(overlay.source === "local" ? "local path is required" : "repository URL is required");
          return undefined;
        }
        void runImport({ sourceType: overlay.source, target, name });
        return undefined;
      }
      dispatchEditorKey(intent, overlayEditorTarget());
      return undefined;
    }

    if (intent.name === "escape") {
      closeOverlay();
      return undefined;
    }
    if (intent.name === "enter") {
      if (overlay.kind === "newTask") {
        const task = overlay.value.trim();
        if (!task) {
          overlayError("task prompt is required");
          return undefined;
        }
        void runSynthesis(task);
        return undefined;
      }
      if (overlay.kind === "savePackage") {
        void runSavePackage(overlay.value);
        return undefined;
      }
      if (overlay.kind === "appendPackage" && !overlay.busy) {
        void runAppendPackage(overlay.packageId, overlay.value);
        return undefined;
      }
      if (overlay.kind === "exportPackage" && !overlay.busy) {
        void runExportPackage(overlay.packageId, overlay.value);
        return undefined;
      }
    }
    dispatchEditorKey(intent, overlayEditorTarget());
    return undefined;
  }

  function handleFilterKey(intent) {
    if (intent.name === "escape") {
      cancelFilter();
      return;
    }
    if (intent.name === "enter") {
      set({ filterActive: false });
      return;
    }
    // Torlink's field semantics: ↓ leaves the field for the list, ↑ is swallowed
    // so a stray tap never moves the hidden list selection.
    if (intent.name === "down") {
      set({ filterActive: false });
      return;
    }
    if (intent.name === "up") return;

    const current = { value: state.filter, cursor: state.filterCursor ?? state.filter.length };
    const names = {
      backspace: { type: "backspace" },
      left: { type: "left" },
      right: { type: "right" },
      home: { type: "home" },
      end: { type: "end" },
    };
    const controlEdits = {
      u: { type: "clear" },
      w: { type: "deleteWord" },
      k: { type: "killToEnd" },
      a: { type: "home" },
      e: { type: "end" },
    };
    if (intent.name === "ctrl" && controlEdits[intent.char]) {
      const next = applyEdit(current, controlEdits[intent.char]);
      applyFilterText(next.value, next.cursor);
      return;
    }
    if (names[intent.name]) {
      const next = applyEdit(current, names[intent.name]);
      applyFilterText(next.value, next.cursor);
      return;
    }
    if (intent.name === "char" || intent.name === "space") {
      const next = applyEdit(current, { type: "insert", text: intent.name === "space" ? " " : intent.char });
      applyFilterText(next.value, next.cursor);
    }
  }

  function handleMoveKey(intent, pageSize) {
    const delta = moveDelta(intent);
    if (delta !== 0) stepCursor(delta);
    else if (intent.name === "pageUp") pageCursor(-1, pageSize);
    else if (intent.name === "pageDown") pageCursor(1, pageSize);
    else if (intent.name === "home") moveCursor(0);
    else if (intent.name === "end") moveCursor(Math.max(0, currentRows().length - 1));
  }

  function handleListAction(intent, pageSize) {
    if (state.view === "system") {
      const max = state.viewport.systemMax;
      const page = Math.max(1, state.viewport.systemPage);
      const delta = moveDelta(intent);
      if (delta !== 0) scrollRegion("system", delta, max);
      else if (intent.name === "pageUp") scrollRegion("system", -page, max);
      else if (intent.name === "pageDown") scrollRegion("system", page, max);
      else if (intent.name === "home") scrollRegion("system", -(state.scroll.system ?? 0), max);
      else if (intent.name === "end") scrollRegion("system", max, max);
      else if (intent.name === "char" && intent.char === "e") void runExportDiagnostics();
      return;
    }

    if (intent.name === "enter") {
      if (state.view === "repositories") {
        // Activation opens the detail and hands it the keyboard (Torlink:
        // enter opens, esc walks back).
        if (selectedRepository()) enterInspector();
        return;
      }
      if (state.view === "code") {
        enterInspector();
        return;
      }
      if (state.view === "settings") {
        enterInspector();
        return;
      }
      if (state.view === "context") {
        const row = selectedContextRow();
        if (row?.kind === "package") void openPackageViewer(row.id);
        else openNewTask();
        return;
      }
    }

    handleMoveKey(intent, pageSize);

    if (intent.name === "char") {
      switch (intent.char) {
        case "a":
          if (state.view === "repositories") openAddRepository();
          break;
        case "s":
          if (state.view === "repositories") void runScan(selectedRepository());
          break;
        case "i":
          if (state.view === "repositories") void runIndex(selectedRepository());
          break;
        case "d":
          if (state.view === "repositories") requestDeleteRepository();
          else if (state.view === "context") requestDeletePackage();
          break;
        case "n":
          if (state.view === "context") openNewTask();
          break;
        case "p":
          if (state.view === "context") togglePackageScope();
          break;
        case "A":
          if (state.view === "context") openAppendPackage();
          break;
        case "e":
          if (state.view === "context") openExportPackage();
          else if (state.view === "settings") openProviderSettings();
          break;
        case "t":
          if (state.view === "settings") openPipelineSettings();
          break;
        case "S":
          if (state.view === "context") openSavePackage();
          break;
        case "R":
          // Regeneration of an existing package (confirmed, then replaces it in
          // place) / restoring the mutable configuration to its defaults.
          if (state.view === "context") requestResynthesize();
          else if (state.view === "settings") requestResetSettings();
          break;
        case "m":
          if (state.view === "context") toggleMarkdown();
          break;
        case "b":
          if (state.view === "context") cycleBudget();
          break;
        case "g":
          if (state.view === "context") toggleGraph();
          break;
        default:
          break;
      }
    }
  }

  /** ↑ / ↓ with the Torlink movement aliases (j / k). */
  function moveDelta(intent) {
    if (intent.name === "up" || (intent.name === "char" && intent.char === "k")) return -1;
    if (intent.name === "down" || (intent.name === "char" && intent.char === "j")) return 1;
    return 0;
  }

  /**
   * Single input entry point with explicit precedence, mirroring the Torlink
   * model: termination → active overlay → active text edit → global keys →
   * focused region → ignored input.
   */
  function dispatch(intent) {
    if (intent.name === "ctrl" && intent.char === "c") return { quit: true };
    if (intent.name === "unknown") return {};

    if (state.overlay) {
      handleOverlayKey(intent);
      return {};
    }

    if (state.filterActive) {
      handleFilterKey(intent);
      return {};
    }

    if (intent.name === "char" && intent.char === "q") return { quit: true };
    if (intent.name === "char" && intent.char === "?") {
      openHelp();
      return {};
    }
    if (intent.name === "char" && intent.char === "r") {
      void refresh();
      return {};
    }
    if (intent.name === "char" && ["1", "2", "3", "4", "5"].includes(intent.char)) {
      switchView(VIEWS[Number(intent.char) - 1]);
      return {};
    }
    if (intent.name === "tab") {
      cycleFocus();
      return {};
    }
    if (intent.name === "escape") {
      back();
      return {};
    }
    if (intent.name === "left" || (intent.name === "char" && intent.char === "h")) {
      focusLeft();
      return {};
    }
    if (intent.name === "right" || (intent.name === "char" && intent.char === "l")) {
      focusRight();
      return {};
    }

    if (state.focus === "rail") {
      const delta = moveDelta(intent);
      if (delta !== 0) {
        moveRail(delta);
        return {};
      }
      if (intent.name === "enter") setFocus("list");
      return {};
    }

    const pageSize = Math.max(3, state.viewport.pageSize);

    if (state.focus === "inspector") {
      const max = state.viewport.detailMax;
      const page = Math.max(1, state.viewport.detailPage);
      const view = state.view;
      const delta = moveDelta(intent);
      if (delta !== 0) scrollRegion("detail", delta, max);
      else if (intent.name === "pageUp") scrollRegion("detail", -page, max);
      else if (intent.name === "pageDown") scrollRegion("detail", page, max);
      else if (intent.name === "home") scrollRegion("detail", -(state.scroll[state.view] ?? 0), max);
      else if (intent.name === "end") scrollRegion("detail", max, max);
      else if (intent.name === "char" && intent.char === "m" && view === "context") toggleMarkdown();
      else if (intent.name === "char" && intent.char === "c" && view === "context") copyContext();
      else if (intent.name === "char" && intent.char === "i" && view === "repositories") {
        void runIndex(selectedRepository());
      } else if (intent.name === "char" && intent.char === "d" && view === "repositories") {
        requestDeleteRepository();
      }
      return {};
    }

    if (intent.name === "char" && intent.char === "/") {
      startFilter();
      return {};
    }

    handleListAction(intent, pageSize);
    return {};
  }

  /* ---------------------------------- tick --------------------------------- */

  async function tick(nowMs) {
    state.nowMs = nowMs;

    if (state.notice && nowMs - state.notice.at > noticeTtlMs) {
      state.notice = null;
      emit();
    }

    if (state.operation?.kind === "indexing" && nowMs - timers.lastProgressPoll >= progressPollMs) {
      timers.lastProgressPoll = nowMs;
      const active = state.operation;
      try {
        const payload = await client.repositoryProgress(active.repoId);
        if (payload && state.operation?.kind === "indexing") {
          const reportedElapsed = typeof payload.elapsed_ms === "number" && payload.elapsed_ms > 0 ? payload.elapsed_ms : null;
          set({
            progress: payload,
            operation: {
              ...state.operation,
              stage: payload.stage ?? state.operation.stage,
              stageIndex: payload.stage_index ?? null,
              stageTotal: payload.stage_total ?? null,
              // File progress is only ever what the backend reports; absent
              // fields stay null and render as indeterminate.
              processedFiles: payload.processed_files ?? null,
              totalFiles: payload.total_files ?? null,
              failedFiles: payload.failed_files ?? null,
              elapsedMs: reportedElapsed ?? nowMs - state.operation.startedAt,
            },
          });
          // A run started elsewhere only ends when the backend says so: its
          // terminal status is published here, and the reconciling read clears
          // the operation (adoptExternalIndexingRun). A run this TUI started is
          // settled by its own response instead.
          if (active.external && (payload.status === "indexed" || payload.status === "error")) {
            set({
              lastRun: {
                kind: "indexing",
                repoId: active.repoId,
                repoName: active.repoName,
                status: payload.status,
                stage: payload.error ?? payload.stage ?? null,
                processedFiles: payload.processed_files ?? null,
                totalFiles: payload.total_files ?? null,
                failedFiles: payload.failed_files ?? null,
                elapsedMs: reportedElapsed,
                finishedAt: nowMs,
              },
            });
            await loadSummary({ quiet: true });
          }
        }
      } catch {
        // Transient poll failures leave the last known stage in place; the run
        // itself reports its own outcome.
      }
      return;
    }

    if (state.operation?.kind === "synthesis" && nowMs - timers.lastHealthPoll >= healthPollMs) {
      timers.lastHealthPoll = nowMs;
      try {
        const health = await client.health();
        const slots = health?.concurrency_available_slots;
        const queue = health?.concurrency_queue_depth;
        const runtimeState = queue > 0 ? "queued" : slots === 0 ? "executing" : "preparing";
        set({ health, operation: { ...state.operation, runtimeState } });
      } catch {
        set({ operation: { ...state.operation, runtimeState: "unreachable" } });
      }
      return;
    }

    // While the backend is unreachable, retry sooner than the idle cadence so a
    // TUI started before the backend finishes booting recovers on its own.
    const cadence = state.error ? errorRetryMs : summaryRefreshMs;
    if (!state.loading && !state.operation && nowMs - timers.lastSummaryRefresh >= cadence) {
      timers.lastSummaryRefresh = nowMs;
      await loadSummary({ quiet: true });
    }
  }

  return {
    getState: () => state,
    subscribe,
    dispatch,
    tick,
    load: loadSummary,
    refresh,
    loadSystem,
    loadSettings,
    switchView,
    setFocus,
    moveCursor,
    pageCursor,
    selectRepositoryById,
    openInspector,
    enterInspector,
    closeInspector,
    openHelp,
    openAddRepository,
    openNewTask,
    openSavePackage,
    requestDeleteRepository,
    requestDeletePackage,
    openPackageViewer,
    togglePackageScope,
    openAppendPackage,
    openExportPackage,
    openPipelineSettings,
    toggleSetting,
    requestResetSettings,
    resetSettings: runResetSettings,
    openProviderSettings,
    probeProvider: runProbeProvider,
    updateProviderSettings: runUpdateProvider,
    cycleProvider: cycleProviderField,
    openModelSelect,
    selectModel,
    closeModelSelect,
    copyContext,
    copyPackage,
    requestResynthesize,
    resynthesize: runResynthesize,
    resynthesisPlan,
    resynthesisSource,
    closeOverlay,
    toggleMarkdown,
    cycleBudget,
    toggleGraph,
    scrollRegion,
    startFilter,
    cancelFilter,
    applyFilterText,
    index: () => runIndex(selectedRepository()),
    scan: () => runScan(selectedRepository()),
    synthesize: runSynthesis,
    savePackage: runSavePackage,
    deletePackage: (id, label) => runDelete({ type: "deletePackage", id, label }),
    deleteRepository: (id, label) => runDelete({ type: "deleteRepository", id, label }),
    importRepository: runImport,
    exportDiagnostics: runExportDiagnostics,
    loadPrompts: (options) => loadPrompts(selectedRepository(), options),
    setViewport: (patch) => {
      Object.assign(state.viewport, patch);
    },

    // selectors (pure reads used by the renderer)
    visibleRepositories,
    selectedRepository,
    codeSymbols,
    contextRows,
    selectedContextRow,
    settingsRows,
    selectedSettingsSection,
    selectedPackage,
    visibleModels,
    currentRows,
  };
}

/** Convert a raw stdin chunk into intents, keeping partial sequences buffered. */
export function decodeInput(chunk, pending = "") {
  return decodeChunk(chunk, pending);
}
