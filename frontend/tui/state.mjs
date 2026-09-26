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

/** Field order of the provider editor; `provider` cycles, the rest are text. */
const PROVIDER_FIELDS = Object.freeze(["provider", "endpoint", "model", "apiKey"]);

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
    scroll: { inspector: 0, system: 0, viewer: 0 },

    notice: null,
    operation: null,
    viewport: { pageSize: 8, inspectorMax: 0, systemMax: 0, viewerMax: 0 },
    nowMs: 0,
  };
}

const errorText = (error) => (error instanceof Error ? error.message : String(error));

export function createApp(options = {}) {
  const client = options.client;
  if (!client) throw new Error("createApp requires a client");
  const exportMarkdown = options.exportMarkdown ?? null;
  const exportFileName = options.exportFileName ?? ((name) => `${String(name ?? "").trim() || "context-package"}.md`);

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
    return [...suggestions, ...packages];
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
    const patch = { view, overlay: null, filterActive: false, scroll: { ...state.scroll } };
    // Below the side-by-side breakpoint the inspector is a mode, and Torlink's
    // rule is that a region's mode resets once focus leaves it: switching
    // destinations from the menu must not leave the previous detail covering
    // the new list.
    if (!state.viewport.sideBySide) patch.inspectorOpen = false;
    if (view === "system") {
      patch.scroll.system = 0;
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
    state.scroll.inspector = 0;
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
    state.scroll.inspector = 0;
    set({ view: "repositories" });
    void loadPrompts(selectedRepository());
  }

  /**
   * Cycle focus between the applicable regions (Torlink's tab). A detail mode
   * that loses focus closes, so focus never rests on a hidden region.
   */
  function cycleFocus() {
    const order = state.inspectorOpen ? ["rail", "list", "inspector"] : ["rail", "list"];
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
    set({ inspectorOpen: true, scroll: { ...state.scroll, inspector: 0 } });
  }

  /** Open the detail and hand it the keyboard — the menu's activation target. */
  function enterInspector() {
    set({ inspectorOpen: true, focus: "inspector", scroll: { ...state.scroll, inspector: 0 } });
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
    else if (state.focus === "list" && state.inspectorOpen && state.viewport.sideBySide) setFocus("inspector");
  }

  function scrollRegion(region, delta, size) {
    const key = region === "system" ? "system" : region === "viewer" ? "viewer" : "inspector";
    const current = state.scroll[key] ?? 0;
    const max = Math.max(0, size);
    state.scroll[key] = clamp(current + delta, 0, max);
    set({});
  }

  function toggleMarkdown() {
    set({ markdownView: state.markdownView === "rendered" ? "raw" : "rendered", scroll: { ...state.scroll, viewer: 0 } });
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
    set({ overlay, scroll: { ...state.scroll, viewer: 0 } });
  }

  function closeOverlay() {
    set({ overlay: null });
  }

  function openHelp() {
    openOverlay({ kind: "help" });
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
      openOverlay({ kind: "viewPackage", package: pkg });
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
      scroll: { ...state.scroll, inspector: 0 },
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

  /** Persist one pipeline boolean through POST /settings/cognee, then re-read it. */
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
      notice(`${settingLabel(key)} ${current ? "disabled" : "enabled"}`);
    } catch (error) {
      set({ settingsError: errorText(error) });
      notice(`settings update failed: ${errorText(error)}`, "error");
    } finally {
      set({ settingsBusy: false });
    }
  }

  /**
   * Provider configuration is a real HTTP mutation (POST /provider/update), so
   * the Settings view exposes it rather than claiming it is GUI-only. The form
   * is prefilled from the persisted settings and every value is re-read after
   * saving; a custom endpoint is never overwritten by a provider switch.
   */
  function openProviderSettings() {
    const settings = state.appSettings ?? {};
    const provider =
      settings.llm_provider ?? state.providerStatus?.provider ?? state.health?.provider_identity ?? PROVIDER_OPTIONS[1];
    const endpoint =
      settings.llm_endpoint ?? state.providerStatus?.base_url ?? PROVIDER_ENDPOINTS[provider] ?? "";
    const model = settings.llm_model ?? state.health?.configured_model ?? state.status?.configured_model ?? "";
    openOverlay({
      kind: "providerSettings",
      // The overlay carries its own option list so the renderer stays pure.
      options: PROVIDER_OPTIONS,
      field: "provider",
      values: { provider, endpoint: String(endpoint), model: String(model), apiKey: "" },
      cursors: { endpoint: String(endpoint).length, model: String(model).length, apiKey: 0 },
      endpointEdited: false,
      discovered: null,
      probeError: null,
      error: null,
      busy: false,
    });
  }

  /**
   * Tab cycles the provider (carrying its default endpoint, unless the user has
   * edited the endpoint in this form) or a discovered model.
   */
  function cycleProviderField(overlay) {
    const values = overlay.values;
    if (overlay.field === "provider") {
      const index = PROVIDER_OPTIONS.indexOf(values.provider);
      const provider = PROVIDER_OPTIONS[wrapStep(index, 1, PROVIDER_OPTIONS.length)];
      const endpoint =
        values.endpoint === "" || !overlay.endpointEdited
          ? PROVIDER_ENDPOINTS[provider] ?? values.endpoint
          : values.endpoint;
      set({
        overlay: {
          ...overlay,
          values: { ...values, provider, endpoint },
          cursors: { ...overlay.cursors, endpoint: endpoint.length },
        },
      });
      return;
    }
    if (overlay.field === "model" && Array.isArray(overlay.discovered) && overlay.discovered.length > 0) {
      const names = overlay.discovered.map((model) => model.label);
      const index = names.indexOf(values.model);
      const model = names[(index + 1) % names.length];
      set({ overlay: { ...overlay, values: { ...values, model }, cursors: { ...overlay.cursors, model: model.length } } });
    }
  }

  /** Non-mutating discovery probe: it never changes the active provider. */
  async function runProbeProvider() {
    const overlay = state.overlay;
    const base_url = overlay.values.endpoint.trim();
    if (!base_url) {
      overlayError("endpoint is required before probing");
      return;
    }
    set({ overlay: { ...overlay, busy: true, probeError: null } });
    try {
      const result = await client.discoverProvider({
        provider: overlay.values.provider,
        base_url,
        api_key: overlay.values.apiKey.trim() || "local",
      });
      const discovered = (Array.isArray(result?.models) ? result.models : [])
        .map((model) => ({
          id: model?.model_id ?? model?.name ?? null,
          label: model?.name || model?.model_id || null,
          quantization: model?.quantization ?? null,
        }))
        .filter((model) => model.label);
      const status = String(result?.status ?? "");
      const probeError = ["unreachable", "discovery_failed", "not_configured"].includes(status)
        ? result?.error_details ?? result?.message ?? status
        : null;
      set({ overlay: { ...state.overlay, busy: false, discovered, probeError } });
      notice(probeError ? `probe failed: ${probeError}` : `discovered ${discovered.length} models`, probeError ? "error" : "info");
    } catch (error) {
      set({ overlay: { ...state.overlay, busy: false, probeError: errorText(error) } });
      notice(`probe failed: ${errorText(error)}`, "error");
    }
  }

  async function runUpdateProvider() {
    const overlay = state.overlay;
    const endpoint = overlay.values.endpoint.trim();
    const model = overlay.values.model.trim();
    if (!endpoint) {
      overlayError("endpoint is required");
      return;
    }
    if (!model) {
      overlayError("model is required");
      return;
    }
    set({ overlay: { ...overlay, busy: true, error: null } });
    try {
      await client.updateProvider({
        provider: overlay.values.provider,
        base_url: endpoint,
        model,
        api_key: overlay.values.apiKey.trim() || "local",
      });
      set({ overlay: null });
      notice(`provider switched to ${overlay.values.provider} · ${model}`);
      await loadProviderContext();
    } catch (error) {
      set({ overlay: { ...state.overlay, busy: false, error: errorText(error) } });
      notice(`provider update failed: ${errorText(error)}`, "error");
    }
  }

  function overlayError(message) {
    if (!state.overlay) return;
    set({ overlay: { ...state.overlay, error: message } });
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
      const field = overlay.field;
      // `provider` is a cycle field, never a text field.
      if (!field || field === "provider") return null;
      return {
        kind: "field",
        get: () => ({ value: overlay.values[field], cursor: overlay.cursors[field] }),
        apply: ({ value, cursor }) =>
          set({
            overlay: {
              ...overlay,
              // Once the endpoint is touched, cycling providers keeps it.
              endpointEdited: field === "endpoint" ? true : overlay.endpointEdited,
              values: { ...overlay.values, [field]: value },
              cursors: { ...overlay.cursors, [field]: cursor },
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

    if (overlay.kind === "help") {
      // The reference sheet scrolls; every other key dismisses it (Torlink).
      const max = state.viewport.viewerMax;
      if (intent.name === "up") scrollRegion("viewer", -1, max);
      else if (intent.name === "down") scrollRegion("viewer", 1, max);
      else if (intent.name === "pageUp") scrollRegion("viewer", -10, max);
      else if (intent.name === "pageDown") scrollRegion("viewer", 10, max);
      else if (intent.name === "home") scrollRegion("viewer", -(state.scroll.viewer ?? 0), max);
      else if (intent.name === "end") scrollRegion("viewer", max, max);
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

    if (overlay.kind === "viewPackage") {
      if (intent.name === "escape") closeOverlay();
      else if (intent.name === "char" && intent.char === "m") toggleMarkdown();
      else if (intent.name === "char" && intent.char === "a") openAppendPackage();
      else if (intent.name === "char" && intent.char === "e") openExportPackage();
      else if (intent.name === "down") scrollRegion("viewer", 1, state.viewport.viewerMax);
      else if (intent.name === "up") scrollRegion("viewer", -1, state.viewport.viewerMax);
      else if (intent.name === "pageDown") scrollRegion("viewer", 10, state.viewport.viewerMax);
      else if (intent.name === "pageUp") scrollRegion("viewer", -10, state.viewport.viewerMax);
      else if (intent.name === "home") scrollRegion("viewer", -(state.scroll.viewer ?? 0), state.viewport.viewerMax);
      else if (intent.name === "end") scrollRegion("viewer", state.viewport.viewerMax, state.viewport.viewerMax);
      return undefined;
    }

    if (overlay.kind === "providerSettings") {
      if (intent.name === "escape") {
        closeOverlay();
        return undefined;
      }
      if (intent.name === "up" || intent.name === "down") {
        const step = intent.name === "down" ? 1 : -1;
        const index = PROVIDER_FIELDS.indexOf(overlay.field);
        const next = PROVIDER_FIELDS[wrapStep(index < 0 ? 0 : index, step, PROVIDER_FIELDS.length)];
        set({ overlay: { ...overlay, field: next } });
        return undefined;
      }
      if (intent.name === "tab") {
        cycleProviderField(overlay);
        return undefined;
      }
      if (intent.name === "ctrl" && intent.char === "p" && !overlay.busy) {
        void runProbeProvider();
        return undefined;
      }
      if (intent.name === "enter" && !overlay.busy) {
        void runUpdateProvider();
        return undefined;
      }
      dispatchEditorKey(intent, overlayEditorTarget());
      return undefined;
    }

    if (overlay.kind === "pipelineSettings") {
      const count = PIPELINE_SETTINGS.length;
      if (intent.name === "escape") {
        closeOverlay();
        return undefined;
      }
      if (intent.name === "up") set({ overlay: { ...overlay, cursor: wrapStep(overlay.cursor ?? 0, -1, count) } });
      else if (intent.name === "down") set({ overlay: { ...overlay, cursor: wrapStep(overlay.cursor ?? 0, 1, count) } });
      else if (intent.name === "enter" || intent.name === "space") {
        const setting = PIPELINE_SETTINGS[clamp(overlay.cursor ?? 0, 0, count - 1)];
        if (setting) void toggleSetting(setting.key);
      }
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
      if (intent.name === "up" || intent.name === "down") {
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
      const delta = moveDelta(intent);
      if (delta !== 0) scrollRegion("system", delta, max);
      else if (intent.name === "pageUp") scrollRegion("system", -(pageSize - 1), max);
      else if (intent.name === "pageDown") scrollRegion("system", pageSize - 1, max);
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
      const max = state.viewport.inspectorMax;
      const view = state.view;
      const delta = moveDelta(intent);
      if (delta !== 0) scrollRegion("inspector", delta, max);
      else if (intent.name === "pageUp") scrollRegion("inspector", -(pageSize - 1), max);
      else if (intent.name === "pageDown") scrollRegion("inspector", pageSize - 1, max);
      else if (intent.name === "home") scrollRegion("inspector", -(state.scroll.inspector ?? 0), max);
      else if (intent.name === "end") scrollRegion("inspector", max, max);
      else if (intent.name === "char" && intent.char === "m" && view === "context") toggleMarkdown();
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
    openProviderSettings,
    probeProvider: runProbeProvider,
    updateProviderSettings: runUpdateProvider,
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
    currentRows,
  };
}

/** Convert a raw stdin chunk into intents, keeping partial sequences buffered. */
export function decodeInput(chunk, pending = "") {
  return decodeChunk(chunk, pending);
}
