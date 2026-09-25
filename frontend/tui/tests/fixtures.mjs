/**
 * Shared fixtures for the TUI test suites: a fake backend client that records
 * calls, and small helpers for driving the app.
 */

import { createApp } from "../state.mjs";
import { createPlainStyler } from "../render.mjs";

export const REPOS = [
  {
    id: "repo-a",
    name: "alpha-service",
    source_type: "local",
    local_path: "/work/alpha",
    branch: "main",
    commit_hash: "abcdef1234567890",
    status: "indexed",
    languages: ["Python", "TypeScript"],
    frameworks: ["FastAPI"],
    file_count: 42,
    size_bytes: 2048,
    indexed_at: "2026-09-20T10:00:00Z",
    error_message: null,
    summary: "Alpha service summary",
    entry_points: ["main.py"],
    architecture: "modular",
    components: ["api", "core"],
    dependencies: ["fastapi"],
    metadata: {},
    call_graph_status: "analyzed",
    call_graph_nodes: [
      { id: "n1", label: "create_session", file: "auth.py", kind: "function", line: 10 },
      { id: "n2", label: "main", file: "main.py", kind: "function", line: 4 },
    ],
    call_graph_edges: [{ source: "n2", target: "n1", kind: "calls" }],
  },
  {
    id: "repo-b",
    name: "beta-service",
    source_type: "github",
    source_url: "https://example.com/beta.git",
    local_path: "/work/beta",
    branch: "develop",
    status: "registered",
    languages: [],
    frameworks: [],
    file_count: 0,
    size_bytes: 0,
    indexed_at: null,
    error_message: null,
    summary: "",
    entry_points: [],
    architecture: "",
    components: [],
    dependencies: [],
    metadata: {},
    call_graph_status: "not_analyzed",
    call_graph_nodes: [],
    call_graph_edges: [],
  },
];

export const PACKAGES = [
  {
    id: "pkg-1",
    name: "Auth context",
    task: "Explain auth",
    markdown: "# Auth\n\n- session",
    token_estimate: 320,
    created_at: "2026-09-24T09:00:00Z",
  },
];

export const CONTEXT_OK = {
  success: true,
  context_markdown: "# Task Context\n\n- `create_session`\n\n```python\ncreate_session()\n```",
  task_summary: "Explain auth",
  intent_category: "architecture",
  extracted_symbols: ["create_session"],
  callers: ["main"],
  callees: [],
  related_files: ["auth.py"],
  estimated_tokens: 120,
  generation_time_ms: 400,
  retrieval_time_ms: 20,
  evidence_state: "partial",
  evidence_score: 0.42,
  evidence_confidence: 0.5,
  model_invoked: false,
  model_name: "phi3:mini",
  inference_status: "model_not_available",
  fallback_used: true,
  missing_evidence: ["no tests"],
  abstained: false,
};

export const PROGRESS = {
  success: true,
  status: "indexing",
  stage: "Extracting AST call graphs and symbols...",
  stage_index: 2,
  stage_total: 5,
  processed_files: 0,
  total_files: 10,
  elapsed_ms: 800,
  error: null,
};

export const HEALTH = {
  status: "ok",
  provider_identity: "lmstudio",
  provider_reachable: true,
  concurrency_available_slots: 1,
  concurrency_queue_depth: 0,
  configured_model: "phi3:mini",
  active_model: null,
  version: "0.1.0",
};

export function makeClient(overrides = {}) {
  const calls = [];
  const record = (name, result) => async (...args) => {
    calls.push({ name, args });
    if (typeof result === "function") return result(...args);
    return result;
  };
  const base = {
    health: HEALTH,
    status: { status: "ok", llm_provider: "lmstudio" },
    providerStatus: { success: true, provider: "lmstudio", is_reachable: true, health_state: "healthy", base_url: "http://127.0.0.1:1234/v1" },
    listRepositories: { success: true, repositories: REPOS, total_count: REPOS.length },
    listContextPackages: { success: true, packages: PACKAGES, total_count: PACKAGES.length },
    memoryStats: { success: true, dataset_count: 2, total_size_display: "1.2 MB", knowledge_graph_status: "extracted" },
    detailedHealth: { status: "ok", storage_paths: { canonical_root: "/home/u/.retrack" } },
    recentLogs: { status: "ok", count: 1, logs: [{ timestamp: "2026-09-25T10:00:00Z", level: "INFO", message: "boot" }] },
    repositoryPrompts: { success: true, prompts: [{ label: "Auth flow", prompt: "Explain the auth flow" }], source: "heuristic" },
    repositoryProgress: PROGRESS,
    indexRepository: { success: true, total_files: 10, processed_files: 10, failed_files: 0, summary: "Indexed 10/10 files" },
    createRepository: { id: "repo-new", name: "gamma-service", local_path: "/work/gamma", status: "registered" },
    scanRepository: { success: true, file_count: 7, languages: ["Go"] },
    deleteRepository: { success: true },
    getContextPackage: (id) => PACKAGES.find((pkg) => pkg.id === id),
    saveContextPackage: (payload) => ({ id: "pkg-new", created_at: "2026-09-25T12:00:00Z", ...payload }),
    deleteContextPackage: { success: true },
    agentContext: CONTEXT_OK,
    exportDiagnostics: { status: "ok", export_path: "/tmp/re-track-diagnostics.json" },
  };
  const client = { calls };
  for (const [name, value] of Object.entries({ ...base, ...overrides })) {
    if (name === "calls") continue;
    client[name] = record(name, value);
  }
  return client;
}

export const key = (name, extra = {}) => ({ name, ...extra });
export const char = (value) => ({ name: "char", char: value });

export async function settle(times = 4) {
  for (let index = 0; index < times; index += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

export async function startApp(overrides = {}) {
  const client = makeClient(overrides);
  const app = createApp({ client, now: () => Date.now() });
  await app.load();
  return { app, client };
}

export const plain = createPlainStyler();
