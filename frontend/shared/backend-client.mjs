/**
 * Interface-agnostic RE:Track backend client.
 *
 * This module is the ONLY integration point non-GUI interfaces (CLI, TUI) use to
 * reach the backend. It performs no presentation, holds no framework state, and
 * imports nothing from `frontend/gui` (no React, no Tauri, no terminal UI).
 *
 * It never invents data: absent fields stay absent and HTTP failures are raised
 * as errors for the caller to render.
 */

const DEFAULT_BASE_URL = process.env.RETRACK_BACKEND_URL || "http://127.0.0.1:8765";

export const ENDPOINTS = Object.freeze({
  health: "/health",
  detailedHealth: "/health/detailed",
  status: "/status",
  dashboardStats: "/dashboard/stats",
  diagnostics: "/diagnostics",
  diagnosticsExport: "/diagnostics/export",
  recentLogs: "/logs/recent",
  repositories: "/repos",
  repositorySummaries: "/repositories",
  contextPackages: "/packages",
  datasets: "/datasets",
  memoryStats: "/memory/stats",
  memoryVectors: "/memory/vectors",
  providerStatus: "/provider/status",
  providerUpdate: "/provider/update",
  providerDiscover: "/provider/discover",
  settings: "/settings",
  settingsCognee: "/settings/cognee",
  settingsReset: "/settings/reset",
  generateContext: "/context",
  agentContext: "/api/v1/context",
  index: "/index",
  benchmarkRun: "/benchmarks/run",
});

export class BackendRequestError extends Error {
  constructor(method, path, status, detail) {
    super(`${method} ${path} failed with HTTP ${status}${detail ? `: ${detail}` : ""}`);
    this.name = "BackendRequestError";
    this.method = method;
    this.path = path;
    this.status = status;
    this.detail = detail ?? null;
  }
}

export class BackendUnreachableError extends Error {
  constructor(baseUrl, cause) {
    super(`RE:Track backend unreachable at ${baseUrl}. Start it with: npm run tauri dev`);
    this.name = "BackendUnreachableError";
    this.baseUrl = baseUrl;
    this.cause = cause;
  }
}

function extractDetail(payload) {
  if (!payload || typeof payload !== "object") return null;
  const detail = payload.detail ?? payload.message ?? payload.error;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first && typeof first.msg === "string") return first.msg;
  }
  if (detail && typeof detail === "object" && typeof detail.message === "string") {
    return detail.message;
  }
  return null;
}

/**
 * Create a backend client bound to a specific origin.
 *
 * @param {{ baseUrl?: string, timeoutMs?: number }} [options]
 */
export function createBackendClient(options = {}) {
  const baseUrl = (options.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
  const defaultTimeoutMs = options.timeoutMs ?? 30_000;

  async function request(method, path, { body, timeoutMs, signal } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs ?? defaultTimeoutMs);
    const onExternalAbort = () => controller.abort();
    if (signal) signal.addEventListener("abort", onExternalAbort, { once: true });

    try {
      const init = { method, signal: controller.signal };
      if (body !== undefined) {
        init.headers = { "Content-Type": "application/json" };
        init.body = JSON.stringify(body);
      }
      const response = await fetch(`${baseUrl}${path}`, init);

      const text = await response.text();
      let payload = null;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = text;
        }
      }

      if (!response.ok) {
        throw new BackendRequestError(method, path, response.status, extractDetail(payload));
      }
      return payload;
    } catch (error) {
      if (error instanceof BackendRequestError) throw error;
      throw new BackendUnreachableError(baseUrl, error);
    } finally {
      clearTimeout(timer);
      if (signal) signal.removeEventListener("abort", onExternalAbort);
    }
  }

  return {
    baseUrl,

    health: () => request("GET", ENDPOINTS.health, { timeoutMs: 5_000 }),
    detailedHealth: () => request("GET", ENDPOINTS.detailedHealth, { timeoutMs: 10_000 }),
    status: () => request("GET", ENDPOINTS.status, { timeoutMs: 10_000 }),
    dashboardStats: () => request("GET", ENDPOINTS.dashboardStats, { timeoutMs: 10_000 }),
    diagnostics: () => request("GET", ENDPOINTS.diagnostics, { timeoutMs: 15_000 }),
    exportDiagnostics: () =>
      request("POST", ENDPOINTS.diagnosticsExport, { body: {}, timeoutMs: 30_000 }),
    recentLogs: (limit = 20) =>
      request("GET", `${ENDPOINTS.recentLogs}?limit=${encodeURIComponent(limit)}`, {
        timeoutMs: 15_000,
      }),

    listRepositories: () => request("GET", ENDPOINTS.repositories, { timeoutMs: 15_000 }),
    createRepository: ({ sourceType, sourceUrl, localPath, name }) =>
      request("POST", ENDPOINTS.repositories, {
        body: {
          source_type: sourceType,
          source_url: sourceUrl,
          local_path: localPath,
          name,
        },
        timeoutMs: 60_000,
      }),
    scanRepository: (repoId) =>
      request("POST", `${ENDPOINTS.repositories}/${encodeURIComponent(repoId)}/scan`, {
        body: {},
        timeoutMs: 60_000,
      }),
    repositoryProgress: (repoId) =>
      request("GET", `${ENDPOINTS.repositories}/${encodeURIComponent(repoId)}/progress`, {
        timeoutMs: 15_000,
      }),
    deleteRepository: (repoId) =>
      request("DELETE", `${ENDPOINTS.repositories}/${encodeURIComponent(repoId)}`, {
        timeoutMs: 60_000,
      }),
    repositoryPrompts: (repoId) =>
      request("GET", `${ENDPOINTS.repositories}/${encodeURIComponent(repoId)}/prompts`, {
        timeoutMs: 30_000,
      }),

    listRepositorySummaries: () => request("GET", ENDPOINTS.repositorySummaries, { timeoutMs: 30_000 }),
    listContextPackages: () => request("GET", ENDPOINTS.contextPackages, { timeoutMs: 15_000 }),
    getContextPackage: (packageId) =>
      request("GET", `${ENDPOINTS.contextPackages}/${encodeURIComponent(packageId)}`, {
        timeoutMs: 15_000,
      }),
    saveContextPackage: (payload) =>
      request("POST", ENDPOINTS.contextPackages, { body: payload, timeoutMs: 15_000 }),
    /** Append an iterative task/note to an existing package (mirrors ContextPackageAppendRequest). */
    appendContextPackage: (packageId, { task, markdown = "", objective = "" }) =>
      request("POST", `${ENDPOINTS.contextPackages}/${encodeURIComponent(packageId)}/append`, {
        body: {
          additional_task: task,
          additional_markdown: markdown,
          additional_objective: objective,
        },
        timeoutMs: 15_000,
      }),
    /**
     * Replace an existing package's generated content (mirrors
     * ContextPackageReplaceRequest). Re-synthesis, not append: the addressed
     * package is superseded, so no second package is created.
     */
    replaceContextPackage: (packageId, payload) =>
      request("PUT", `${ENDPOINTS.contextPackages}/${encodeURIComponent(packageId)}`, {
        body: payload,
        timeoutMs: 15_000,
      }),
    deleteContextPackage: (packageId) =>
      request("DELETE", `${ENDPOINTS.contextPackages}/${encodeURIComponent(packageId)}`, {
        timeoutMs: 15_000,
      }),
    listDatasets: () => request("GET", ENDPOINTS.datasets, { timeoutMs: 30_000 }),
    memoryStats: () => request("GET", ENDPOINTS.memoryStats, { timeoutMs: 15_000 }),
    memoryVectors: () => request("GET", ENDPOINTS.memoryVectors, { timeoutMs: 15_000 }),
    providerStatus: () => request("GET", ENDPOINTS.providerStatus, { timeoutMs: 10_000 }),

    /** Hot-reload and persist the active inference provider (UpdateProviderRequest). */
    updateProvider: ({ provider, base_url, model, api_key = "local" }) =>
      request("POST", ENDPOINTS.providerUpdate, {
        body: { provider, base_url, model, api_key },
        timeoutMs: 30_000,
      }),

    /** Non-mutating model discovery probe for a candidate or active endpoint. */
    discoverProvider: ({ provider, base_url, api_key = "local" }) =>
      request("POST", ENDPOINTS.providerDiscover, {
        body: { provider, base_url, api_key },
        timeoutMs: 20_000,
      }),

    /** Persistent application settings (AppSettingsResponse). */
    appSettings: () => request("GET", ENDPOINTS.settings, { timeoutMs: 10_000 }),

    /** Persist Cognee pipeline parameters (POST /settings/cognee). */
    updateCogneeSettings: (payload) =>
      request("POST", ENDPOINTS.settingsCognee, { body: payload, timeoutMs: 20_000 }),

    /**
     * Restore mutable configuration to the application defaults (POST
     * /settings/reset). Configuration only — repositories, packages, memory and
     * indexed data are untouched — and the response is the authoritative
     * read-back of the stored settings.
     */
    resetSettings: () => request("POST", ENDPOINTS.settingsReset, { body: {}, timeoutMs: 30_000 }),

    /** Active-repository Context Package synthesis (the GUI's generate_context path). */
    generateContext: ({ task, datasets, top_k }) =>
      request("POST", ENDPOINTS.generateContext, {
        body: { task, datasets, top_k },
        timeoutMs: 300_000,
      }),

    /** External-agent middleware: task prompt + repository path. */
    agentContext: ({ taskPrompt, repositoryPath, datasetName, maxTokens, includeStructuralGraph = true }) =>
      request("POST", ENDPOINTS.agentContext, {
        body: {
          task_prompt: taskPrompt,
          repository_path: repositoryPath,
          dataset_name: datasetName,
          max_tokens: maxTokens,
          include_structural_graph: includeStructuralGraph,
        },
        timeoutMs: 300_000,
      }),

    indexRepository: ({ repositoryPath, datasetName, batchSize, forceReindex = false }) =>
      request("POST", ENDPOINTS.index, {
        body: {
          repository_path: repositoryPath,
          dataset_name: datasetName,
          batch_size: batchSize,
          force_reindex: forceReindex,
        },
        timeoutMs: 600_000,
      }),

    runBenchmark: () => request("POST", ENDPOINTS.benchmarkRun, { body: {}, timeoutMs: 600_000 }),
  };
}
