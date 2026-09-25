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

export const VIEWS = Object.freeze(["repositories", "code", "context", "system"]);
export const VIEW_LABELS = Object.freeze({
  repositories: "Repositories",
  code: "Code",
  context: "Context",
  system: "System",
});

export const TOKEN_BUDGETS = Object.freeze([2048, 4096, 8192]);

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

    repositories: [],
    packages: [],
    prompts: { state: "idle", source: null, items: [], error: null },
    context: null,
    contextError: null,
    progress: null,
    lastRun: null,

    view: "repositories",
    focus: "list",
    inspectorOpen: false,
    overlay: null,
    filter: "",
    filterActive: false,
    markdownView: "rendered",
    tokenBudget: 4096,
    includeGraph: true,

    cursors: { repositories: 0, code: 0, context: 0, system: 0 },
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
    const suggestions = (state.prompts.items ?? []).map((item) => ({
      kind: "suggestion",
      label: item.label,
      prompt: item.prompt,
    }));
    const packages = (state.packages ?? []).map((pkg) => ({
      kind: "package",
      id: pkg.id,
      label: pkg.name,
      task: pkg.task,
      tokens: pkg.token_estimate,
    }));
    return [...suggestions, ...packages];
  }

  function selectedContextRow() {
    const rows = contextRows();
    if (rows.length === 0) return null;
    return rows[clamp(state.cursors.context, 0, rows.length - 1)];
  }

  function currentRows() {
    if (state.view === "repositories") return visibleRepositories();
    if (state.view === "code") return codeSymbols();
    if (state.view === "context") return contextRows();
    return [];
  }

  /* -------------------------------- loading -------------------------------- */

  async function loadPrompts(repo) {
    if (!repo?.id) {
      set({ prompts: { state: "idle", source: null, items: [], error: null } });
      return;
    }
    set({ prompts: { state: "loading", source: state.prompts.source, items: state.prompts.items, error: null } });
    try {
      const payload = await client.repositoryPrompts(repo.id);
      const items = Array.isArray(payload?.prompts) ? payload.prompts : [];
      set({ prompts: { state: "loaded", source: payload?.source ?? null, items, error: null } });
    } catch (error) {
      set({ prompts: { state: "error", source: null, items: [], error: errorText(error) } });
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
      };
    } else if (!running && state.operation?.kind === "indexing" && state.operation.external) {
      state.operation = null;
    }
  }

  async function refresh({ quiet = false } = {}) {
    await loadSummary({ quiet });
    if (state.view === "system") await loadSystem();
    const repo = selectedRepository();
    if (repo) await loadPrompts(repo);
    if (!quiet) notice("refreshed");
  }

  /* --------------------------------- actions -------------------------------- */

  function switchView(view) {
    if (!VIEWS.includes(view)) return;
    const patch = { view, overlay: null, filterActive: false, scroll: { ...state.scroll } };
    if (view === "system") {
      patch.scroll.system = 0;
    }
    set(patch);
    if (view === "system") void loadSystem();
  }

  function moveCursor(deltaOrTarget) {
    const rows = currentRows();
    if (rows.length === 0) return;
    if (typeof deltaOrTarget === "number") {
      state.cursors[state.view] = wrapStep(state.cursors[state.view], deltaOrTarget, rows.length);
    } else {
      state.cursors[state.view] = clamp(deltaOrTarget, 0, rows.length - 1);
    }
    state.scroll.inspector = 0;
    set({});
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

  function cycleFocus() {
    const order = state.inspectorOpen ? ["rail", "list", "inspector"] : ["rail", "list"];
    const current = order.indexOf(state.focus);
    set({ focus: order[wrapStep(current, 1, order.length)] });
  }

  function setFocus(focus) {
    set({ focus });
  }

  function openInspector() {
    set({ inspectorOpen: true, scroll: { ...state.scroll, inspector: 0 } });
  }

  function closeInspector() {
    set({ inspectorOpen: false, focus: state.focus === "inspector" ? "list" : state.focus });
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
    set({ filterActive: true, focus: "list" });
  }

  function cancelFilter() {
    set({ filterActive: false, filter: "", cursors: { ...state.cursors, [state.view]: 0 } });
  }

  function applyFilterText(text) {
    set({ filter: stripMouseSequences(text), cursors: { ...state.cursors, [state.view]: 0 } });
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

    set({
      operation: {
        kind: "indexing",
        repoId: repo.id,
        repoName: repo.name,
        startedAt: now(),
        external: false,
        stage: "submitting",
        stageIndex: null,
        stageTotal: null,
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
          finishedAt: now(),
        },
      });
      notice(
        ok
          ? `indexed ${repo.name} · ${result?.processed_files ?? 0}/${result?.total_files ?? 0} files`
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
          finishedAt: now(),
        },
      });
      notice(`indexing failed: ${errorText(error)}`, "error");
    } finally {
      set({ operation: null, progress: null });
      await loadSummary({ quiet: true });
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
      set({});
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
    if (overlay.kind === "newTask") return { kind: "single", get: () => overlay, apply: (next) => set({ overlay: { ...overlay, ...next } }) };
    if (overlay.kind === "savePackage") return { kind: "single", get: () => overlay, apply: (next) => set({ overlay: { ...overlay, ...next } }) };
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
      if (intent.name !== "unknown") closeOverlay();
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
      else if (intent.name === "down") scrollRegion("viewer", 1, state.viewport.viewerMax);
      else if (intent.name === "up") scrollRegion("viewer", -1, state.viewport.viewerMax);
      else if (intent.name === "pageDown") scrollRegion("viewer", 10, state.viewport.viewerMax);
      else if (intent.name === "pageUp") scrollRegion("viewer", -10, state.viewport.viewerMax);
      else if (intent.name === "home") scrollRegion("viewer", -(state.scroll.viewer ?? 0), state.viewport.viewerMax);
      else if (intent.name === "end") scrollRegion("viewer", state.viewport.viewerMax, state.viewport.viewerMax);
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
    const current = { value: state.filter, cursor: state.filter.length };
    const names = {
      backspace: { type: "backspace" },
      left: { type: "left" },
      right: { type: "right" },
      home: { type: "home" },
      end: { type: "end" },
    };
    if (intent.name === "ctrl" && intent.char === "u") {
      applyFilterText("");
      return;
    }
    if (names[intent.name]) {
      applyFilterText(applyEdit(current, names[intent.name]).value);
      return;
    }
    if (intent.name === "char") {
      applyFilterText(state.filter + intent.char);
      return;
    }
    if (intent.name === "space") {
      applyFilterText(`${state.filter} `);
    }
  }

  function handleMoveKey(intent, pageSize) {
    if (intent.name === "up") moveCursor(-1);
    else if (intent.name === "down") moveCursor(1);
    else if (intent.name === "pageUp") pageCursor(-1, pageSize);
    else if (intent.name === "pageDown") pageCursor(1, pageSize);
    else if (intent.name === "home") moveCursor(0);
    else if (intent.name === "end") moveCursor(Math.max(0, currentRows().length - 1));
  }

  function handleListAction(intent, pageSize) {
    if (state.view === "system") {
      const max = state.viewport.systemMax;
      if (intent.name === "up") scrollRegion("system", -1, max);
      else if (intent.name === "down") scrollRegion("system", 1, max);
      else if (intent.name === "pageUp") scrollRegion("system", -(pageSize - 1), max);
      else if (intent.name === "pageDown") scrollRegion("system", pageSize - 1, max);
      else if (intent.name === "home") scrollRegion("system", -(state.scroll.system ?? 0), max);
      else if (intent.name === "end") scrollRegion("system", max, max);
      else if (intent.name === "char" && intent.char === "e") void runExportDiagnostics();
      return;
    }

    if (intent.name === "enter") {
      if (state.view === "repositories") {
        const repo = selectedRepository();
        if (repo) {
          if (state.inspectorOpen) setFocus("inspector");
          else openInspector();
        }
        return;
      }
      if (state.view === "code") {
        openInspector();
        return;
      }
      if (state.view === "context") {
        const row = selectedContextRow();
        if (row?.kind === "package") void openPackageViewer(row.id);
        else if (row?.kind === "suggestion") openNewTask();
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

  /**
   * Single input entry point with explicit precedence:
   * ctrl-c → overlay owns input → filter capture → global keys → view keys.
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
    if (intent.name === "char" && ["1", "2", "3", "4"].includes(intent.char)) {
      switchView(VIEWS[Number(intent.char) - 1]);
      return {};
    }
    if (intent.name === "tab") {
      cycleFocus();
      return {};
    }
    if (intent.name === "escape") {
      if (state.inspectorOpen) {
        closeInspector();
        return {};
      }
      if (state.filter) {
        cancelFilter();
        return {};
      }
      setFocus("list");
      return {};
    }

    if (state.focus === "rail") {
      if (intent.name === "up" || intent.name === "down") {
        const current = VIEWS.indexOf(state.view);
        switchView(VIEWS[wrapStep(current, intent.name === "down" ? 1 : -1, VIEWS.length)]);
        return {};
      }
      if (intent.name === "enter") setFocus("list");
      return {};
    }

    const pageSize = Math.max(3, state.viewport.pageSize);

    if (state.focus === "inspector") {
      const max = state.viewport.inspectorMax;
      const view = state.view;
      if (intent.name === "up") scrollRegion("inspector", -1, max);
      else if (intent.name === "down") scrollRegion("inspector", 1, max);
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
      try {
        const payload = await client.repositoryProgress(state.operation.repoId);
        if (payload) {
          set({
            progress: payload,
            operation: {
              ...state.operation,
              stage: payload.stage ?? state.operation.stage,
              stageIndex: payload.stage_index ?? null,
              stageTotal: payload.stage_total ?? null,
            },
          });
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
    switchView,
    setFocus,
    moveCursor,
    pageCursor,
    selectRepositoryById,
    openInspector,
    closeInspector,
    openHelp,
    openAddRepository,
    openNewTask,
    openSavePackage,
    requestDeleteRepository,
    requestDeletePackage,
    openPackageViewer,
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
    loadPrompts: () => loadPrompts(selectedRepository()),
    setViewport: (patch) => {
      Object.assign(state.viewport, patch);
    },

    // selectors (pure reads used by the renderer)
    visibleRepositories,
    selectedRepository,
    codeSymbols,
    contextRows,
    selectedContextRow,
    currentRows,
  };
}

/** Convert a raw stdin chunk into intents, keeping partial sequences buffered. */
export function decodeInput(chunk, pending = "") {
  return decodeChunk(chunk, pending);
}
