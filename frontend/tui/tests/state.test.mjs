import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { createApp, TOKEN_BUDGETS } from "../state.mjs";
import { buildModel, composeLines, createPlainStyler } from "../render.mjs";
import { publishViewport, clipboardAdapter } from "./fixtures.mjs";

const plainView = createPlainStyler();

/** Build (and publish) a frame so state clamps against real geometry. */
function render(app, cols = 100, rows = 30) {
  const model = buildModel(app, { cols, rows, spinnerFrame: 0 });
  publishViewport(app, model);
  return model;
}

/** The frame's plain text — used where a test asserts what the user sees. */
function renderText(app, cols = 100, rows = 30) {
  return composeLines(render(app, cols, rows), plainView).join("\n");
}

/* --------------------------------- fixtures -------------------------------- */

const REPOS = [
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

const PACKAGES = [
  {
    id: "pkg-1",
    name: "Auth context",
    task: "Explain auth",
    objective: "Explain auth",
    repository_name: "alpha-service",
    repository_branch: "main",
    section_count: 3,
    markdown: "# Auth\n\n- session",
    token_estimate: 320,
    created_at: "2026-09-24T09:00:00Z",
    updated_at: "2026-09-24T09:00:00Z",
    tags: ["auth"],
  },
];

const SETTINGS = {
  data_root: "/home/u/.retrack",
  vector_db: "lancedb",
  graph_db: "kuzu",
  enable_kg_extraction: true,
  auto_link_entities: false,
  caching: true,
};

const CONTEXT_OK = {
  success: true,
  context_markdown: "# Task Context\n\n- `create_session`",
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

const PROGRESS = {
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

function makeClient(overrides = {}) {
  const calls = [];
  const record = (name, result) => async (...args) => {
    calls.push({ name, args });
    if (typeof result === "function") return result(...args);
    return result;
  };
  // Persisted settings and packages are per-client so a write + re-read is
  // observable (a toggle, a provider update, a reset, a re-synthesis).
  const settings = { ...SETTINGS };
  const packageStore = new Map(PACKAGES.map((pkg) => [pkg.id, { ...pkg }]));
  const base = {
    health: { status: "ok", provider_identity: "lmstudio", provider_reachable: true, concurrency_available_slots: 1, concurrency_queue_depth: 0, configured_model: "phi3:mini", active_model: null },
    status: { status: "ok", llm_provider: "lmstudio" },
    providerStatus: { success: true, provider: "lmstudio", is_reachable: true, health_state: "healthy", base_url: "http://127.0.0.1:1234/v1" },
    listRepositories: { success: true, repositories: REPOS, total_count: REPOS.length },
    listContextPackages: () => ({ success: true, packages: [...packageStore.values()], total_count: packageStore.size }),
    memoryStats: { success: true, dataset_count: 2, total_size_display: "1.2 MB", knowledge_graph_status: "extracted" },
    detailedHealth: { status: "ok", storage_paths: { canonical_root: "/home/u/.retrack" } },
    recentLogs: { status: "ok", count: 1, logs: [{ timestamp: "2026-09-25T10:00:00Z", level: "INFO", message: "boot" }] },
    repositoryPrompts: { success: true, prompts: [{ label: "Auth flow", prompt: "Explain the auth flow" }], source: "heuristic" },
    repositoryProgress: PROGRESS,
    indexRepository: { success: true, total_files: 10, processed_files: 10, failed_files: 0, summary: "Indexed 10/10 files" },
    createRepository: { id: "repo-new", name: "gamma-service", local_path: "/work/gamma", status: "registered" },
    scanRepository: { success: true, file_count: 7, languages: ["Go"] },
    deleteRepository: { success: true },
    getContextPackage: (id) => packageStore.get(id) ?? null,
    saveContextPackage: (payload) => {
      const saved = { id: "pkg-new", created_at: "2026-09-25T12:00:00Z", updated_at: "2026-09-25T12:00:00Z", ...payload };
      packageStore.set(saved.id, saved);
      return saved;
    },
    deleteContextPackage: (id) => {
      packageStore.delete(id);
      return { success: true, message: `Context package ${id} deleted` };
    },
    appendContextPackage: (id, payload) => {
      const pkg = { ...packageStore.get(id), id, task: payload.task, updated_at: "2026-09-25T13:00:00Z" };
      packageStore.set(id, pkg);
      return pkg;
    },
    replaceContextPackage: (id, payload) => {
      const previous = packageStore.get(id);
      if (!previous) throw new Error(`package ${id} not found`);
      const replacement = { ...previous, ...payload, id, updated_at: "2026-09-26T12:00:00Z" };
      packageStore.set(id, replacement);
      return replacement;
    },
    agentContext: CONTEXT_OK,
    exportDiagnostics: { status: "ok", export_path: "/tmp/re-track-diagnostics.json" },
    appSettings: () => ({ success: true, ...settings }),
    updateCogneeSettings: (payload) => {
      Object.assign(settings, payload);
      return { success: true, ...settings };
    },
    updateProvider: (payload) => {
      settings.llm_provider = payload.provider;
      settings.llm_endpoint = payload.base_url;
      settings.llm_model = payload.model;
      return { success: true, ...payload };
    },
    resetSettings: () => {
      Object.assign(settings, {
        llm_provider: "ollama",
        llm_endpoint: "http://localhost:11434/v1",
        llm_model: "phi3:mini-reset",
        enable_kg_extraction: true,
        auto_link_entities: false,
        caching: false,
      });
      return { success: true, ...settings };
    },
    discoverProvider: {
      success: true,
      provider: "lmstudio",
      base_url: "http://127.0.0.1:1234/v1",
      is_reachable: true,
      status: "available",
      models: [{ model_id: "qwen2.5-7b", name: "qwen2.5-7b", quantization: "Q4_K_M" }],
      message: "",
      error_details: null,
    },
  };
  const client = { calls };
  for (const [name, value] of Object.entries({ ...base, ...overrides })) {
    if (name === "calls") continue;
    client[name] = record(name, value);
  }
  return client;
}

const key = (name, extra = {}) => ({ name, ...extra });
const char = (value) => ({ name: "char", char: value });

async function settle(times = 4) {
  for (let index = 0; index < times; index += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

async function startApp(overrides = {}, options = {}) {
  const client = makeClient(overrides);
  const app = createApp({ client, now: () => Date.now(), ...options });
  await app.load();
  return { app, client };
}

function callNames(client) {
  return client.calls.map((call) => call.name);
}

/* ---------------------------------- tests ---------------------------------- */

describe("state: startup and loading", () => {
  it("loads every summary subsystem on startup", async () => {
    const { app, client } = await startApp();
    const state = app.getState();

    assert.equal(state.ready, true);
    assert.equal(state.error, null);
    assert.deepEqual(state.degraded, []);
    assert.equal(state.repositories.length, 2);
    assert.equal(state.packages.length, 1);
    assert.equal(state.health.status, "ok");
    assert.ok(callNames(client).includes("listRepositories"));
    assert.ok(state.lastRefreshAt);
  });

  it("reports a partially degraded backend without inventing data", async () => {
    const { app } = await startApp({ memoryStats: () => Promise.reject(new Error("503")) });
    const state = app.getState();

    assert.deepEqual(state.degraded, ["memoryStats"]);
    assert.equal(state.error, null);
    assert.equal(state.memoryStats, null);
    assert.equal(state.repositories.length, 2);
  });

  it("marks the backend unavailable when nothing answers", async () => {
    const failure = () => Promise.reject(new Error("connect ECONNREFUSED"));
    const { app } = await startApp({
      health: failure,
      status: failure,
      providerStatus: failure,
      listRepositories: failure,
      listContextPackages: failure,
      memoryStats: failure,
    });
    const state = app.getState();

    assert.equal(state.error, "backend unavailable");
    assert.deepEqual(state.repositories, []);
    assert.equal(state.health, null);
  });

  it("loads prompts for the selected repository", async () => {
    const { app, client } = await startApp();
    await app.loadPrompts();
    assert.deepEqual(client.calls.at(-1), { name: "repositoryPrompts", args: ["repo-a"] });
    assert.equal(app.getState().prompts.items.length, 1);
  });

  it("fetches suggested tasks when the Context workbench opens, once per repository", async () => {
    const { app, client } = await startApp();
    assert.equal(callNames(client).filter((name) => name === "repositoryPrompts").length, 0);

    app.switchView("context");
    await settle();
    assert.equal(callNames(client).filter((name) => name === "repositoryPrompts").length, 1);
    assert.equal(app.getState().prompts.repoId, "repo-a");

    // Re-entering the workbench keeps the loaded set; an explicit refresh re-reads it.
    app.switchView("repositories");
    app.switchView("context");
    await settle();
    assert.equal(callNames(client).filter((name) => name === "repositoryPrompts").length, 1);

    await app.refresh();
    assert.equal(callNames(client).filter((name) => name === "repositoryPrompts").length, 2);
  });

  it("bounds the Context catalog to the repository the suggestions belong to", async () => {
    const { app, client } = await startApp();
    app.switchView("context");
    await settle();
    assert.equal(app.getState().prompts.repoId, "repo-a");

    // Move to the other repository, then open the workbench again.
    app.switchView("repositories");
    app.dispatch(key("down"));
    app.switchView("context");
    await settle();
    assert.equal(client.calls.at(-1).args[0], "repo-b");
    assert.equal(app.getState().prompts.repoId, "repo-b");
  });
});

describe("state: navigation", () => {
  it("moves the repository cursor and keeps per-view cursors independent", async () => {
    const { app } = await startApp();

    app.dispatch(key("down"));
    assert.equal(app.getState().cursors.repositories, 1);

    app.dispatch(char("2"));
    assert.equal(app.getState().view, "code");
    const codeRows = app.currentRows().length;
    if (codeRows > 1) {
      app.dispatch(key("down"));
      assert.equal(app.getState().cursors.code, 1);
    }

    app.dispatch(char("1"));
    assert.equal(app.getState().cursors.repositories, 1, "repository cursor is preserved across views");
  });

  it("cycles focus through rail, list, and the open inspector", async () => {
    const { app } = await startApp();
    assert.equal(app.getState().focus, "list");

    app.dispatch(key("tab"));
    assert.equal(app.getState().focus, "rail");
    app.dispatch(key("tab"));
    assert.equal(app.getState().focus, "list");
    app.openInspector();
    app.dispatch(key("tab"));
    assert.equal(app.getState().focus, "inspector");
    app.dispatch(key("tab"));
    assert.equal(app.getState().focus, "rail");
  });

  it("captures typing while filtering and switches views with number keys after applying", async () => {
    const { app } = await startApp();
    app.dispatch(char("/"));
    app.dispatch(char("a"));
    app.dispatch(char("3"));
    // Text capture owns the keyboard: the digit is filter input, not navigation.
    assert.equal(app.getState().filter, "a3");
    assert.equal(app.getState().view, "repositories");

    app.dispatch(key("enter"));
    assert.equal(app.getState().filterActive, false);
    app.dispatch(char("3"));
    assert.equal(app.getState().view, "context");
  });

  it("filters repositories and restores the full list on escape", async () => {
    const { app } = await startApp();
    app.dispatch(char("/"));
    app.dispatch(char("b"));
    app.dispatch(char("e"));
    app.dispatch(char("t"));
    assert.equal(app.visibleRepositories().length, 1);
    assert.equal(app.selectedRepository().id, "repo-b");

    app.dispatch(key("escape"));
    assert.equal(app.getState().filter, "");
    assert.equal(app.visibleRepositories().length, 2);
  });

  it("jumps to the first and last row with home and end", async () => {
    const { app } = await startApp();
    app.dispatch(key("end"));
    assert.equal(app.getState().cursors.repositories, 1, "end goes to the last row directly");
    app.dispatch(key("home"));
    assert.equal(app.getState().cursors.repositories, 0, "home returns to the first row");

    // Absolute jumps and wrapping movement coexist.
    app.dispatch(key("up"));
    assert.equal(app.getState().cursors.repositories, 1, "↑ from the first row wraps to the last");
    app.dispatch(key("down"));
    assert.equal(app.getState().cursors.repositories, 0, "↓ from the last row wraps to the first");
  });

  it("uses escape to walk back from inspector to list", async () => {
    const { app } = await startApp();
    app.openInspector();
    app.dispatch(key("escape"));
    assert.equal(app.getState().inspectorOpen, false);
  });

  it("quits only on q or ctrl-c", async () => {
    const { app } = await startApp();
    assert.deepEqual(app.dispatch(char("j")), {});
    assert.deepEqual(app.dispatch(char("q")), { quit: true });
    assert.deepEqual(app.dispatch(key("ctrl", { char: "c" })), { quit: true });
  });

  it("opens the help overlay with ? and closes it on the next key", async () => {
    const { app } = await startApp();
    app.dispatch(char("?"));
    assert.equal(app.getState().overlay.kind, "help");
    app.dispatch(char("x"));
    assert.equal(app.getState().overlay, null);
  });
});

describe("state: operations", () => {
  it("indexes the selected repository and records the real result", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("i"));
    assert.equal(app.getState().operation.kind, "indexing");

    await settle();
    const state = app.getState();
    assert.equal(state.operation, null);
    assert.equal(state.lastRun.status, "indexed");
    assert.equal(state.lastRun.processedFiles, 10);
    assert.match(state.notice.message, /indexed alpha-service/);
    assert.deepEqual(client.calls.find((call) => call.name === "indexRepository").args, [
      { repositoryPath: "/work/alpha", datasetName: "alpha-service", forceReindex: true },
    ]);
  });

  it("polls progress and surfaces backend phases without percentages", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app } = await startApp({
      indexRepository: async () => {
        await pending;
        return { success: true, total_files: 10, processed_files: 10, failed_files: 0, summary: "done" };
      },
    });

    app.dispatch(char("i"));
    await settle(2);
    await app.tick(Date.now() + 1000);

    const operation = app.getState().operation;
    assert.equal(operation.stageIndex, 2);
    assert.equal(operation.stageTotal, 5);
    assert.equal(operation.stage, "Extracting AST call graphs and symbols...");
    assert.equal(operation.processedFiles, 0, "file counts come from the backend as reported");
    assert.equal(operation.totalFiles, 10);
    assert.equal(operation.elapsedMs, 800, "the backend-reported elapsed time is kept");
    assert.equal(app.getState().progress.status, "indexing");

    release();
    await settle();
    assert.equal(app.getState().operation, null);
  });

  it("prevents a duplicate indexing run while one is active", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app, client } = await startApp({
      indexRepository: async () => {
        await pending;
        return { success: true, total_files: 1, processed_files: 1, failed_files: 0, summary: "done" };
      },
    });

    app.dispatch(char("i"));
    await settle(2);
    app.dispatch(char("i"));
    assert.match(app.getState().notice.message, /already in progress/i);
    assert.equal(client.calls.filter((call) => call.name === "indexRepository").length, 1);

    release();
    await settle();
  });

  it("reports indexing failures and clears the operation", async () => {
    const { app } = await startApp({
      indexRepository: async () => {
        throw new Error("indexing failed: disk full");
      },
    });

    app.dispatch(char("i"));
    await settle();

    const state = app.getState();
    assert.equal(state.operation, null);
    assert.equal(state.lastRun.status, "error");
    assert.match(state.notice.message, /disk full/);
  });

  it("records failed files and measured elapsed time on completion", async () => {
    const { app } = await startApp({
      indexRepository: { success: true, total_files: 10, processed_files: 8, failed_files: 2, summary: "Indexed 8/10 files" },
    });

    app.dispatch(char("i"));
    await settle();

    const run = app.getState().lastRun;
    assert.equal(run.failedFiles, 2);
    assert.ok(typeof run.elapsedMs === "number" && run.elapsedMs >= 0);
    assert.match(app.getState().notice.message, /2 failed/);
  });

  it("scans the selected repository", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("s"));
    await settle();
    assert.ok(client.calls.some((call) => call.name === "scanRepository"));
    assert.match(app.getState().notice.message, /scanned alpha-service/);
  });

  it("imports a repository through the modal, then scans it", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("a"));
    assert.equal(app.getState().overlay.kind, "addRepo");

    app.dispatch(key("enter"));
    assert.match(app.getState().overlay.error, /path is required/);

    for (const value of "/work/gamma") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(6);

    const state = app.getState();
    assert.equal(state.overlay, null);
    assert.match(state.notice.message, /added gamma-service/);
    assert.deepEqual(client.calls.find((call) => call.name === "createRepository").args, [
      { sourceType: "local", localPath: "/work/gamma", name: undefined },
    ]);
    assert.ok(client.calls.some((call) => call.name === "scanRepository"));
  });

  it("deletes a repository only after confirmation", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("d"));
    assert.equal(app.getState().overlay.kind, "confirm");

    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay, null);
    assert.equal(client.calls.filter((call) => call.name === "deleteRepository").length, 0);

    app.dispatch(char("d"));
    app.dispatch(key("enter"));
    await settle(4);
    assert.deepEqual(client.calls.find((call) => call.name === "deleteRepository").args, ["repo-a"]);
    assert.match(app.getState().notice.message, /deleted alpha-service/);
  });

  it("synthesizes context with the configured budget and graph flag", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("b"));
    assert.equal(app.getState().tokenBudget, TOKEN_BUDGETS[2]);
    app.dispatch(char("g"));
    assert.equal(app.getState().includeGraph, false);

    app.dispatch(char("n"));
    assert.equal(app.getState().overlay.kind, "newTask");
    for (const value of "explain auth") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(4);

    const call = client.calls.find((entry) => entry.name === "agentContext");
    assert.deepEqual(call.args, [
      {
        taskPrompt: "explain auth",
        repositoryPath: "/work/alpha",
        datasetName: "alpha-service",
        maxTokens: TOKEN_BUDGETS[2],
        includeStructuralGraph: false,
      },
    ]);
    assert.equal(app.getState().context.task_summary, "Explain auth");
    assert.equal(app.getState().contextError, null);
  });

  it("tracks the runtime guard state while synthesis is in flight", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app } = await startApp({
      agentContext: async () => {
        await pending;
        return CONTEXT_OK;
      },
      health: { status: "ok", provider_identity: "lmstudio", concurrency_available_slots: 0, concurrency_queue_depth: 0 },
    });

    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "task") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(2);

    await app.tick(Date.now() + 3000);
    assert.equal(app.getState().operation.runtimeState, "executing");

    release();
    await settle();
    assert.equal(app.getState().operation, null);
  });

  it("keeps abstention and evidence telemetry verbatim", async () => {
    const { app } = await startApp({
      agentContext: {
        ...CONTEXT_OK,
        abstained: true,
        abstention_reason: "No repository evidence was found",
        evidence_confidence: 0,
        evidence_state: "insufficient",
      },
    });

    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "auth") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(4);

    const result = app.getState().context;
    assert.equal(result.abstained, true);
    assert.equal(result.abstention_reason, "No repository evidence was found");
    assert.equal(result.evidence_confidence, 0);
  });

  it("surfaces synthesis failures instead of an empty success", async () => {
    const { app } = await startApp({
      agentContext: async () => {
        throw new Error("provider unavailable");
      },
    });

    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "task") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(4);

    assert.equal(app.getState().context, null);
    assert.match(app.getState().contextError, /provider unavailable/);
    assert.match(app.getState().notice.message, /synthesis failed/);
  });
});

describe("state: packages", () => {
  it("saves the generated context as a package", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "task") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(4);

    app.dispatch(char("S"));
    assert.equal(app.getState().overlay.kind, "savePackage");
    app.dispatch(key("enter"));
    await settle(4);

    const payload = client.calls.find((call) => call.name === "saveContextPackage").args[0];
    assert.equal(payload.name, "Explain auth");
    assert.equal(payload.repository_id, "repo-a");
    assert.equal(payload.markdown, CONTEXT_OK.context_markdown);
    assert.equal(app.getState().packages.length, 2);
  });

  it("refuses to save without generated context", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("S"));
    assert.equal(app.getState().overlay, null);
    assert.match(app.getState().notice.message, /generate context before saving/);
    assert.equal(client.calls.filter((call) => call.name === "saveContextPackage").length, 0);
  });

  it("opens a saved package through the backend and toggles markdown presentation", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("3"));
    // Suggestions come first, saved packages last.
    app.dispatch(key("end"));
    assert.equal(app.selectedContextRow().kind, "package");

    app.openPackageViewer("pkg-1");
    await settle(3);
    assert.equal(app.getState().overlay.kind, "viewPackage");
    assert.deepEqual(client.calls.find((call) => call.name === "getContextPackage").args, ["pkg-1"]);

    app.toggleMarkdown();
    assert.equal(app.getState().markdownView, "raw");
    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay, null);
  });

  it("deletes a saved package after confirmation", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(key("end")); // last row is the package
    app.dispatch(char("d"));
    assert.equal(app.getState().overlay.kind, "confirm");
    app.dispatch(key("enter"));
    await settle(3);

    assert.deepEqual(client.calls.find((call) => call.name === "deleteContextPackage").args, ["pkg-1"]);
    assert.equal(app.getState().packages.length, 0);
  });
});

describe("state: settings", () => {
  it("loads the persisted settings and storage detail when the Settings view opens", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("5"));
    assert.equal(app.getState().view, "settings");
    await settle();

    assert.ok(client.calls.some((call) => call.name === "appSettings"));
    assert.ok(client.calls.some((call) => call.name === "detailedHealth"));
    assert.equal(app.getState().appSettings.vector_db, "lancedb");
    assert.equal(app.getState().settingsError, null);
  });

  it("keeps a failed settings read visible instead of rendering stale configuration", async () => {
    const { app } = await startApp({ appSettings: () => Promise.reject(new Error("settings unavailable")) });
    app.dispatch(char("5"));
    await settle();

    assert.match(app.getState().settingsError, /settings unavailable/);
    assert.equal(app.getState().appSettings, null);
  });

  it("persists a pipeline toggle through the backend and re-reads the stored value", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("5"));
    await settle();

    app.dispatch(char("t"));
    assert.equal(app.getState().overlay.kind, "pipelineSettings");
    assert.equal(app.getState().overlay.cursor, 0);

    app.dispatch(key("down")); // auto-link entities: currently disabled
    app.dispatch(key("enter"));
    await settle(8);

    assert.deepEqual(client.calls.find((call) => call.name === "updateCogneeSettings").args, [{ auto_link_entities: true }]);
    assert.equal(app.getState().appSettings.auto_link_entities, true, "the re-read reflects the backend value");
    assert.match(app.getState().notice.message, /✓ saved · Auto-link entities enabled/);
    assert.deepEqual(client.calls.find((call) => call.name === "appSettings").args, [], "the value shown is read back");
    assert.equal(app.getState().settingsBusy, false);
  });

  it("surfaces a settings write failure without changing the stored value", async () => {
    const { app } = await startApp({
      updateCogneeSettings: async () => {
        throw new Error("write denied");
      },
    });
    app.dispatch(char("5"));
    await settle();
    app.dispatch(char("t"));
    app.dispatch(key("enter")); // knowledge graph extraction: enabled -> disabled
    await settle();

    assert.match(app.getState().overlay.error, /write denied/, "the failure stays visible in the overlay");
    assert.match(app.getState().notice.message, /✗ save failed · Knowledge graph extraction · write denied/);
    assert.equal(app.getState().appSettings.enable_kg_extraction, true, "the failed write is not applied locally");
    assert.equal(app.getState().settingsBusy, false);
  });

  it("refuses to toggle a setting the HTTP contract cannot persist", async () => {
    const { app, client } = await startApp();
    await app.toggleSetting("vector_db");
    assert.match(app.getState().notice.message, /not editable from the TUI/);
    assert.equal(client.calls.filter((call) => call.name === "updateCogneeSettings").length, 0);
  });
});

describe("state: settings reset", () => {
  const openReset = async (overrides = {}) => {
    const started = await startApp(overrides);
    started.app.dispatch(char("5"));
    await settle();
    started.app.dispatch(char("R"));
    return started;
  };

  it("offers a confirmed reset from the Settings view", async () => {
    const { app, client } = await openReset();

    assert.equal(app.getState().overlay.kind, "resetSettings");
    assert.equal(client.calls.filter((call) => call.name === "resetSettings").length, 0, "opening the dialog writes nothing");

    app.dispatch(key("enter"));
    await settle(8);

    assert.equal(client.calls.filter((call) => call.name === "resetSettings").length, 1);
    assert.equal(app.getState().overlay, null);
    assert.match(app.getState().notice.message, /✓ settings reset to application defaults/);
    assert.equal(app.getState().appSettings.llm_model, "phi3:mini-reset", "the values shown are the read-back");
    assert.equal(app.getState().appSettings.auto_link_entities, false);
  });

  it("cancels without touching the backend", async () => {
    const { app, client } = await openReset();
    const before = { ...app.getState().appSettings };

    app.dispatch(key("escape"));

    assert.equal(app.getState().overlay, null);
    assert.equal(client.calls.filter((call) => call.name === "resetSettings").length, 0);
    assert.deepEqual(app.getState().appSettings, before, "cancelling leaves the stored settings alone");
  });

  it("reports a failed reset, keeps the dialog open and re-reads the stored values", async () => {
    const { app, client } = await openReset({
      resetSettings: async () => {
        throw new Error("settings store is read-only");
      },
      updateProvider: async () => {
        throw new Error("unused");
      },
    });
    const before = { ...app.getState().appSettings };

    app.dispatch(key("enter"));
    await settle(8);

    assert.equal(app.getState().overlay.kind, "resetSettings");
    assert.match(app.getState().overlay.error, /read-only/);
    assert.match(app.getState().notice.message, /✗ reset failed/);
    assert.deepEqual(app.getState().appSettings, before, "no partial reset is shown as applied");
    assert.ok(client.calls.some((call) => call.name === "appSettings"), "the authoritative values are re-read");
    assert.equal(app.getState().settingsBusy, false);
  });

  it("is configuration-only: no repository, package or memory data is deleted", async () => {
    const { app, client } = await openReset();
    const packages = app.getState().packages.length;
    const repositories = app.getState().repositories.length;

    app.dispatch(key("enter"));
    await settle(10);

    for (const name of ["deleteRepository", "deleteContextPackage", "forget", "cognify"]) {
      assert.equal(client.calls.filter((call) => call.name === name).length, 0, `${name} must not be called`);
    }
    assert.equal(app.getState().packages.length, packages);
    assert.equal(app.getState().repositories.length, repositories);
  });

  it("keeps the reset action discoverable in the footer and the capability matrix", async () => {
    const { app } = await startApp();
    app.dispatch(char("5"));
    await settle();

    const footer = render(app, 120, 34).footer.hints.map((hint) => hint.keys);
    assert.ok(footer.includes("R"), "the reset control is advertised");
    const detail = renderText(app, 120, 34);
    assert.match(detail, /restore|default/i, "the settings detail explains what reset does");
  });
});

describe("state: provider editing", () => {
  const MODELS = [
    { model_id: "qwen2.5-7b", name: "qwen2.5-7b", quantization: "Q4_K_M" },
    { model_id: "phi-4-mini", name: "phi-4-mini", quantization: "Q6_K" },
    { model_id: "llama3.2", name: "llama3.2", quantization: "unknown" },
  ];

  const openEditor = async (overrides = {}) => {
    const started = await startApp(overrides);
    started.app.dispatch(char("5"));
    await settle();
    started.app.dispatch(char("e"));
    await settle();
    return started;
  };

  it("opens the editor prefilled from the persisted settings and reads the endpoint", async () => {
    const { app, client } = await openEditor();
    const draft = app.getState().providerDraft;
    const state = app.getState();

    assert.equal(state.overlay.kind, "providerSettings");
    assert.equal(draft.values.provider, "lmstudio");
    assert.equal(draft.values.endpoint, "http://127.0.0.1:1234/v1");
    assert.equal(draft.saved.model, "phi3:mini", "the saved model comes from the verified configuration");
    assert.equal(draft.selected, null, "nothing is chosen until the user chooses: opening saves nothing");
    assert.deepEqual(draft.options, ["lmstudio", "ollama", "openai_compatible"]);

    // Opening the editor is what reads the endpoint; nothing is mutated by it.
    assert.deepEqual(client.calls.find((call) => call.name === "discoverProvider").args, [
      { provider: "lmstudio", base_url: "http://127.0.0.1:1234/v1", api_key: "local" },
    ]);
    assert.equal(state.models.state, "ready");
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0);
  });

  it("saves the whole configuration when a model is chosen, with no separate save step", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: MODELS, message: "" },
    });

    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    assert.equal(app.getState().providerDraft.field, "model");
    app.dispatch(key("enter")); // open the provider's list
    app.dispatch(key("enter")); // choose the highlighted model
    await settle(10);

    assert.deepEqual(client.calls.find((call) => call.name === "updateProvider").args, [
      { provider: "lmstudio", base_url: "http://127.0.0.1:1234/v1", model: "qwen2.5-7b", api_key: "local" },
    ]);
    assert.match(app.getState().notice.message, /✓ provider updated · lmstudio · qwen2\.5-7b/);
    assert.equal(app.getState().overlay, null, "the editor closes once the configuration is saved");
    assert.equal(app.getState().appSettings.llm_model, "qwen2.5-7b", "the values shown are the read-back");
  });

  it("carries the stored model into a provider change only when the new provider reports it", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: [{ model_id: "phi3:mini", name: "phi3:mini" }, ...MODELS], message: "" },
    });

    app.dispatch(key("tab")); // lmstudio -> ollama: the endpoint changes with it
    await settle();
    app.dispatch(key("enter"));
    await settle(10);

    const call = client.calls.find((entry) => entry.name === "updateProvider");
    assert.equal(call.args[0].provider, "ollama");
    assert.equal(call.args[0].base_url, "http://localhost:11434/v1");
    assert.equal(call.args[0].model, "phi3:mini", "the stored model is kept because the provider reported it");
    assert.match(app.getState().notice.message, /✓ provider updated/);
  });

  it("refuses to save while the stored model is not offered by the endpoint", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: MODELS, message: "" },
    });

    app.dispatch(key("enter"));
    await settle(10);

    assert.match(app.getState().providerDraft.error, /select a model from the provider's list/);
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0, "nothing invalid is saved");
    assert.equal(app.getState().overlay.kind, "providerSettings", "the editor stays open");
  });

  it("does not persist a provider merely because it is highlighted", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: MODELS, message: "" },
    });

    app.dispatch(key("tab")); // lmstudio -> ollama (highlighted, not saved)
    app.dispatch(key("tab")); // ollama -> openai_compatible
    await settle();

    assert.equal(app.getState().providerDraft.values.provider, "openai_compatible");
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0, "cycling saves nothing");
  });

  it("waits for the provider's answer before judging a commit", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app, client } = await openEditor({
      discoverProvider: async ({ provider, base_url }) => {
        await pending;
        return { success: true, status: "available", models: MODELS, message: "", provider, base_url };
      },
    });
    assert.equal(app.getState().models.state, "loading");

    app.dispatch(key("enter")); // commit while discovery is still in flight
    await settle(2);
    release();
    await settle(12);

    assert.equal(app.getState().models.state, "ready");
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0);
    assert.match(app.getState().providerDraft.error, /select a model from the provider's list/);
  });

  it("shows the discovery state while the models are still loading", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app } = await openEditor({
      discoverProvider: async () => {
        await pending;
        return { success: true, status: "available", models: MODELS, message: "", error_details: null };
      },
    });

    assert.equal(app.getState().models.state, "loading");
    assert.deepEqual(app.visibleModels(), [], "no model is offered before the provider answers");
    release();
    await settle();
    assert.equal(app.getState().models.state, "ready");
    assert.deepEqual(app.visibleModels().map((model) => model.label), ["qwen2.5-7b", "phi-4-mini", "llama3.2"]);
  });

  it("reports a reachable but empty model list as unavailable", async () => {
    const { app } = await openEditor({
      discoverProvider: {
        success: true,
        status: "reachable_but_empty",
        models: [],
        message: "Provider is reachable at http://127.0.0.1:1234/v1, but no models are currently loaded or available.",
        error_details: null,
      },
    });

    assert.equal(app.getState().models.state, "empty");
    assert.deepEqual(app.visibleModels(), []);
    assert.match(renderText(app), /no models available/, "the editor says why selection is unavailable");
  });

  it("keeps the backend's own reason when discovery fails and saves nothing", async () => {
    const { app, client } = await openEditor({
      discoverProvider: {
        success: true,
        status: "unreachable",
        models: [],
        message: "Provider endpoint 'http://127.0.0.1:1234/v1' is unreachable. Verify host and port.",
        error_details: "connection refused",
      },
    });

    assert.equal(app.getState().models.state, "failed");
    assert.equal(app.getState().models.status, "unreachable");
    assert.match(app.getState().models.message, /unreachable/);

    // The failed read offers nothing new, and choosing is impossible.
    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    app.dispatch(key("enter"));
    assert.equal(app.getState().overlay.kind, "modelSelect");
    assert.deepEqual(app.visibleModels(), [], "a failed discovery offers no models");
    app.dispatch(key("enter"));
    assert.equal(app.getState().overlay.kind, "modelSelect", "there is nothing to select");
    assert.equal(app.getState().providerDraft.selected, null);
    assert.match(renderText(app, 90, 24), /model selection: unavailable/, "the reason is on screen");
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0);
  });

  it("reports a network failure of the discovery probe as an unavailable model list", async () => {
    const { app } = await openEditor({
      discoverProvider: async () => {
        throw new Error("ECONNREFUSED http://127.0.0.1:1234/v1");
      },
    });

    assert.equal(app.getState().models.state, "failed");
    assert.match(app.getState().models.message, /ECONNREFUSED/);
    assert.deepEqual(app.visibleModels(), [], "a failed probe offers no models");
    assert.match(renderText(app, 100, 30), /model selection: unavailable/);
  });

  it("drops the old model and reads the new provider when the provider changes", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: MODELS, message: "" },
    });
    assert.equal(app.getState().providerDraft.selected, null);

    app.dispatch(key("tab")); // lmstudio -> ollama
    await settle();

    const draft = app.getState().providerDraft;
    assert.equal(draft.values.provider, "ollama");
    assert.equal(draft.values.endpoint, "http://localhost:11434/v1", "the provider's default endpoint comes with it");
    assert.equal(draft.selected, null, "a model discovered for another provider is not this provider's model");
    assert.deepEqual(client.calls.filter((call) => call.name === "discoverProvider").at(-1).args, [
      { provider: "ollama", base_url: "http://localhost:11434/v1", api_key: "local" },
    ]);
  });

  it("clears a chosen model the new endpoint does not report", async () => {
    const { app } = await openEditor({
      discoverProvider: async ({ base_url }) => ({
        success: true,
        status: "available",
        models: base_url.includes("11434") ? [{ model_id: "llama3.2", name: "llama3.2" }] : MODELS,
        message: "",
      }),
      // The commit is refused, so the editor stays open with the choice visible.
      updateProvider: async () => {
        throw new Error("provider offline");
      },
    });

    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    app.dispatch(key("enter"));
    app.dispatch(key("enter")); // choose qwen2.5-7b
    await settle(10);
    assert.equal(app.getState().overlay.kind, "providerSettings");
    assert.equal(app.getState().providerDraft.selected.label, "qwen2.5-7b");

    app.dispatch(key("tab")); // -> ollama, whose list is llama3.2 only
    await settle(10);

    assert.equal(app.getState().providerDraft.selected, null, "the stale choice is cleared, never carried over");
    assert.deepEqual(app.getState().models.items.map((model) => model.label), ["llama3.2"]);
  });

  it("keeps a custom endpoint when cycling providers", async () => {
    const { app } = await openEditor();
    app.dispatch(key("down")); // endpoint
    app.dispatch(key("ctrl", { char: "u" }));
    for (const value of "http://box:9999/v1") app.dispatch(char(value));
    app.dispatch(key("down")); // api key
    app.dispatch(key("down")); // model
    app.dispatch(key("down")); // wraps to provider
    assert.equal(app.getState().providerDraft.field, "provider");

    app.dispatch(key("tab"));
    assert.equal(app.getState().providerDraft.values.endpoint, "http://box:9999/v1");
  });

  it("opens the provider's model list, and only choosing persists anything", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: MODELS, message: "" },
      updateProvider: async () => {
        throw new Error("provider offline");
      },
    });

    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    assert.equal(app.getState().providerDraft.field, "model");

    app.dispatch(key("enter"));
    assert.equal(app.getState().overlay.kind, "modelSelect");
    assert.deepEqual(app.visibleModels().map((model) => model.label), ["qwen2.5-7b", "phi-4-mini", "llama3.2"]);

    // Highlighting two rows down persists nothing.
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0, "highlighting saves nothing");

    app.dispatch(key("enter")); // choose: this is the commit
    await settle(10);

    assert.equal(app.getState().providerDraft.selected.label, "llama3.2", "the chosen model is the one persisted");
    assert.equal(
      client.calls.filter((call) => call.name === "updateProvider").length,
      1,
      "choosing saves through the backend exactly once"
    );
    assert.match(app.getState().notice.message, /✗ save failed · provider · provider offline/);
    assert.equal(app.getState().overlay.kind, "providerSettings", "a refused save keeps the editor open");
  });

  it("closes the model list with esc without choosing or saving", async () => {
    const { app, client } = await openEditor({ discoverProvider: { success: true, status: "available", models: MODELS, message: "" } });
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    app.dispatch(key("down")); // model
    app.dispatch(key("enter"));
    app.dispatch(key("down"));
    app.dispatch(key("escape"));

    assert.equal(app.getState().overlay.kind, "providerSettings");
    assert.equal(app.getState().providerDraft.selected, null, "esc cancels the highlight");
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0);
  });

  it("filters the provider's models and never names one itself", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: MODELS, message: "" },
      updateProvider: async () => {
        throw new Error("provider offline");
      },
    });
    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    app.dispatch(key("enter"));

    app.dispatch(char("/"));
    for (const value of "phi") app.dispatch(char(value));
    assert.deepEqual(app.visibleModels().map((model) => model.label), ["phi-4-mini"], "the filter narrows the returned list");

    // A filter that matches nothing offers nothing — it cannot invent a model.
    for (const _ of ["q", "w", "e", "n", "9"]) app.dispatch(char(_));
    assert.deepEqual(app.visibleModels(), []);
    app.dispatch(key("enter"));
    assert.equal(app.getState().overlay.kind, "modelSelect");
    assert.equal(app.getState().providerDraft.selected, null, "an empty filter cannot select anything");
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0);

    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay.filter, "", "esc clears the filter first");
    assert.equal(app.getState().overlay.kind, "modelSelect");
    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay.kind, "providerSettings", "a second esc walks back to the editor");
  });

  it("scrolls a long model list and only ever selects a reported model", async () => {
    const many = Array.from({ length: 40 }, (_, index) => ({ model_id: `model-${index}`, name: `model-${index}`, quantization: "unknown" }));
    const { app } = await openEditor({
      discoverProvider: { success: true, status: "available", models: many, message: "" },
      updateProvider: async () => {
        throw new Error("provider offline");
      },
    });
    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    app.dispatch(key("enter"));
    render(app, 90, 24);

    app.dispatch(key("pageDown"));
    app.dispatch(key("end"));
    assert.equal(app.getState().overlay.cursor, 39);
    const selected = app.visibleModels()[app.getState().overlay.cursor];
    assert.equal(selected.label, "model-39");

    app.dispatch(key("enter"));
    const chosen = app.getState().providerDraft.selected.label;
    assert.equal(chosen, "model-39");
    assert.ok(
      many.some((model) => (model.name ?? model.model_id) === chosen),
      "the chosen model is one the provider actually reported"
    );
  });

  it("saves the chosen model with the choice, then re-reads the authoritative values", async () => {
    const { app, client } = await openEditor({ discoverProvider: { success: true, status: "available", models: MODELS, message: "" } });
    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    app.dispatch(key("enter")); // open the list (the saved model is not in it)
    assert.equal(app.visibleModels()[app.getState().overlay.cursor].label, "qwen2.5-7b");
    app.dispatch(key("enter")); // choose it — no separate save step
    await settle(10);

    assert.deepEqual(client.calls.find((call) => call.name === "updateProvider").args, [
      { provider: "lmstudio", base_url: "http://127.0.0.1:1234/v1", model: "qwen2.5-7b", api_key: "local" },
    ]);
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 1, "exactly one write");
    assert.equal(app.getState().overlay, null);
    assert.equal(app.getState().providerDraft, null);
    assert.match(app.getState().notice.message, /✓ provider updated · lmstudio · qwen2\.5-7b/);
    assert.equal(app.getState().appSettings.llm_model, "qwen2.5-7b", "the re-read reflects the backend");
  });

  it("refuses to save without an acceptable model and keeps backend failures visible", async () => {
    const { app, client } = await openEditor({
      discoverProvider: { success: true, status: "available", models: MODELS, message: "" },
      updateProvider: async () => {
        throw new Error("switch refused");
      },
    });
    app.dispatch(key("tab")); // changing provider clears the selection
    await settle();
    assert.equal(app.getState().providerDraft.selected, null);
    app.dispatch(key("enter"));
    await settle(10);
    assert.match(app.getState().providerDraft.error, /select a model from the provider's list/);
    assert.equal(client.calls.filter((call) => call.name === "updateProvider").length, 0);

    for (const _ of ["endpoint", "apiKey", "model"]) app.dispatch(key("down"));
    app.dispatch(key("enter"));
    app.dispatch(key("enter")); // choose the highlighted model: this saves
    await settle(10);

    assert.equal(app.getState().overlay.kind, "providerSettings", "a failed save keeps the form open");
    assert.match(app.getState().providerDraft.error, /switch refused/);
    assert.match(app.getState().notice.message, /✗ save failed · provider · switch refused/);
  });

  it("has no model text field: typing on the model row changes nothing", async () => {
    const { app } = await openEditor({ discoverProvider: { success: true, status: "available", models: MODELS, message: "" } });
    for (const _ of ["provider", "endpoint", "apiKey"]) app.dispatch(key("down"));
    assert.equal(app.getState().providerDraft.field, "model");

    for (const value of "not-a-real-model") app.dispatch(char(value));
    assert.equal(app.getState().providerDraft.selected, null, "the selection is untouched by typing");
    assert.equal(app.getState().overlay.kind, "providerSettings");
    assert.equal(app.getState().models.items.some((model) => model.label === "not-a-real-model"), false);
  });
});

describe("state: re-synthesis", () => {
  const openPackage = async (overrides = {}) => {
    const started = await startApp(overrides);
    started.app.dispatch(char("3"));
    started.app.dispatch(char("p")); // packages-only catalog: the saved package leads
    started.app.dispatch(key("enter"));
    await settle();
    return started;
  };

  it("offers re-synthesis from the viewer with the package's own basis", async () => {
    const { app, client } = await openPackage();
    app.dispatch(char("r"));

    const plan = app.getState().overlay.plan;
    assert.equal(app.getState().overlay.kind, "resynthesize");
    assert.equal(plan.packageId, "pkg-1");
    assert.equal(plan.task, "Explain auth", "the stored task is the basis, never the selected row");
    assert.equal(plan.repo.id, "repo-a", "the repository comes from the package's stored identity");
    assert.equal(client.calls.filter((call) => call.name === "agentContext").length, 0, "nothing runs before confirmation");

    app.dispatch(key("escape"));
    assert.equal(app.getState().overlay.kind, "viewPackage", "esc returns to the package");
    assert.equal(client.calls.filter((call) => call.name === "agentContext").length, 0);
  });

  it("regenerates in place: one generation, one replacement, no second package", async () => {
    const { app, client } = await openPackage();
    const before = app.getState().overlay.package.markdown;

    app.dispatch(char("r"));
    app.dispatch(key("enter"));
    await settle(14);

    const generation = client.calls.filter((call) => call.name === "agentContext");
    assert.equal(generation.length, 1, "the model is called exactly once");
    assert.deepEqual(generation[0].args, [
      {
        taskPrompt: "Explain auth",
        repositoryPath: "/work/alpha",
        datasetName: "alpha-service",
        maxTokens: app.getState().tokenBudget,
        includeStructuralGraph: true,
      },
    ]);

    const replacement = client.calls.filter((call) => call.name === "replaceContextPackage");
    assert.equal(replacement.length, 1, "one replacement, addressed by id");
    assert.equal(replacement[0].args[0], "pkg-1");
    assert.equal(replacement[0].args[1].markdown, CONTEXT_OK.context_markdown, "the generated markdown is stored verbatim");
    assert.equal(replacement[0].args[1].repository_commit, "abcdef1234567890");

    assert.equal(client.calls.filter((call) => call.name === "saveContextPackage").length, 0, "no second package is created");
    assert.equal(app.getState().packages.length, 1);
    assert.notEqual(app.getState().overlay.package.markdown, before, "the viewer shows the regenerated content");
    assert.equal(app.getState().overlay.package.markdown, CONTEXT_OK.context_markdown);
    assert.equal(app.getState().overlay.kind, "viewPackage", "the regenerated package stays open");
    assert.equal(app.getState().operation, null);
    assert.match(app.getState().notice.message, /✓ re-synthesized Auth context/);
  });

  it("preserves the reader's scroll position through the replacement", async () => {
    const { app } = await openPackage();
    app.setViewport({ viewerMax: 40, viewerPage: 8 });
    app.dispatch(key("down"));
    app.dispatch(key("down"));
    const offset = app.getState().scroll.viewer;
    assert.ok(offset > 0);

    app.dispatch(char("r"));
    app.dispatch(key("enter"));
    await settle(14);

    assert.equal(app.getState().scroll.viewer, offset);
  });

  it("keeps the stored package intact when generation fails", async () => {
    const { app, client } = await openPackage({
      agentContext: async () => {
        throw new Error("provider exploded");
      },
    });
    const before = app.getState().overlay.package.markdown;

    app.dispatch(char("r"));
    app.dispatch(key("enter"));
    await settle(14);

    assert.match(app.getState().notice.message, /✗ re-synthesis failed · provider exploded · Auth context is unchanged/);
    assert.equal(client.calls.filter((call) => call.name === "replaceContextPackage").length, 0);
    assert.equal(app.getState().overlay.package.markdown, before);
    assert.equal(app.getState().packages[0].markdown, before);
    assert.equal(app.getState().operation, null);
  });

  it("never overwrites the package with an empty regeneration", async () => {
    const { app, client } = await openPackage({
      agentContext: { success: true, context_markdown: "", task_summary: "Explain auth" },
    });
    const before = app.getState().overlay.package.markdown;

    app.dispatch(char("r"));
    app.dispatch(key("enter"));
    await settle(14);

    assert.equal(client.calls.filter((call) => call.name === "replaceContextPackage").length, 0);
    assert.match(app.getState().notice.message, /returned no context/);
    assert.equal(app.getState().overlay.package.markdown, before);
  });

  it("keeps the stored package intact when persistence fails", async () => {
    const { app, client } = await openPackage({
      replaceContextPackage: async () => {
        throw new Error("package store is read-only");
      },
    });
    const before = app.getState().overlay.package.markdown;

    app.dispatch(char("r"));
    app.dispatch(key("enter"));
    await settle(14);

    assert.equal(client.calls.filter((call) => call.name === "replaceContextPackage").length, 1);
    assert.match(app.getState().notice.message, /✗ re-synthesis failed · package store is read-only · Auth context is unchanged/);
    assert.equal(app.getState().overlay.package.markdown, before, "the previous package stays usable");
    assert.equal(app.getState().packages[0].markdown, before);
  });

  it("re-synthesizes the package selected in the catalog with R", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("p"));

    app.dispatch(char("R"));
    assert.equal(app.getState().overlay.kind, "resynthesize");
    app.dispatch(key("enter"));
    await settle(14);

    assert.equal(client.calls.filter((call) => call.name === "agentContext").length, 1);
    assert.equal(client.calls.filter((call) => call.name === "replaceContextPackage").length, 1);
    assert.equal(app.getState().overlay, null, "no viewer was open, so none is reopened");
  });

  it("refuses when the package's repository is no longer registered", async () => {
    const { app, client } = await startApp({
      getContextPackage: () => ({ ...PACKAGES[0], repository_id: "repo-gone", repository_name: "gone-service" }),
    });
    app.dispatch(char("3"));
    app.dispatch(char("p"));
    app.dispatch(key("enter"));
    await settle();

    app.dispatch(char("r"));

    assert.equal(app.getState().overlay.kind, "viewPackage", "no confirmation is offered for an impossible run");
    assert.match(app.getState().notice.message, /repository gone-service is not registered/);
    assert.equal(client.calls.filter((call) => call.name === "agentContext").length, 0);
  });

  it("blocks re-synthesis while a synthesis is already running", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const { app, client } = await startApp({
      agentContext: async () => {
        await pending;
        return CONTEXT_OK;
      },
    });
    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "explain auth") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(2);
    assert.equal(app.getState().operation.kind, "synthesis");

    app.dispatch(char("p"));
    app.dispatch(key("enter"));
    await settle(2);
    app.dispatch(char("r"));

    assert.equal(app.getState().overlay.kind, "viewPackage", "re-synthesis is not offered while one runs");
    assert.match(app.getState().notice.message, /synthesis is already running/);
    assert.equal(client.calls.filter((call) => call.name === "agentContext").length, 1);

    release();
    await settle(14);
    assert.equal(client.calls.filter((call) => call.name === "replaceContextPackage").length, 0);
  });

  it("keeps append distinct from re-synthesis", async () => {
    const { app, client } = await openPackage();

    app.dispatch(char("a")); // append, from the viewer
    assert.equal(app.getState().overlay.kind, "appendPackage");
    for (const value of "add tests") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(12);

    assert.equal(client.calls.filter((call) => call.name === "appendContextPackage").length, 1);
    assert.equal(client.calls.filter((call) => call.name === "replaceContextPackage").length, 0);
    assert.equal(client.calls.filter((call) => call.name === "agentContext").length, 0);
    assert.match(app.getState().notice.message, /appended to/);
  });
});

describe("state: clipboard", () => {
  const CONTEXT_WITH_MARKDOWN = CONTEXT_OK.context_markdown;

  /** Generate context so the output view has something to copy. */
  const generate = async (overrides = {}, options = {}) => {
    const started = await startApp(overrides, options);
    started.app.dispatch(char("3"));
    started.app.dispatch(char("n"));
    for (const value of "explain auth") started.app.dispatch(char(value));
    started.app.dispatch(key("enter"));
    await settle(12);
    started.app.setFocus("inspector");
    return started;
  };

  it("copies the generated Markdown exactly, without escape sequences", async () => {
    const copyText = clipboardAdapter();
    const { app, client } = await generate({}, { copyText });

    app.dispatch(char("c"));
    await settle(4);

    assert.equal(copyText.copies.length, 1);
    assert.equal(copyText.copies[0].text, CONTEXT_WITH_MARKDOWN, "byte-for-byte the backend markdown");
    assert.equal(copyText.copies[0].text.includes("\u001b"), false, "no terminal escapes are copied");
    assert.match(app.getState().notice.message, /✓ copied the generated markdown to the clipboard/);
    assert.equal(client.calls.filter((call) => call.name === "agentContext").length, 1, "copying never regenerates");
  });

  it("copies the underlying Markdown whether the view is rendered or raw", async () => {
    const copyText = clipboardAdapter();
    const { app } = await generate({}, { copyText });

    assert.equal(app.getState().markdownView, "rendered");
    app.dispatch(char("c"));
    await settle(4);
    app.dispatch(char("m")); // switch to raw
    assert.equal(app.getState().markdownView, "raw");
    app.dispatch(char("c"));
    await settle(4);

    assert.equal(copyText.copies.length, 2);
    assert.equal(copyText.copies[0].text, CONTEXT_WITH_MARKDOWN);
    assert.equal(copyText.copies[1].text, CONTEXT_WITH_MARKDOWN, "rendering never changes what is copied");
  });

  it("copies the stored Markdown from the package viewer", async () => {
    const copyText = clipboardAdapter();
    const { app, client } = await startApp({}, { copyText });
    app.dispatch(char("3"));
    app.dispatch(char("p"));
    app.dispatch(key("enter"));
    await settle();

    app.dispatch(char("c"));
    await settle(4);

    assert.equal(copyText.copies[0].text, PACKAGES[0].markdown);
    assert.match(app.getState().notice.message, /✓ copied “Auth context”/);
    assert.equal(client.calls.filter((call) => call.name === "getContextPackage").length, 1, "the open package is not re-fetched");
  });

  it("has nothing to copy before a generation ran", async () => {
    const copyText = clipboardAdapter();
    const { app } = await startApp({}, { copyText });
    app.dispatch(char("3"));
    app.setFocus("inspector");

    app.dispatch(char("c"));
    await settle(2);

    assert.equal(copyText.copies.length, 0);
    assert.match(app.getState().notice.message, /nothing to copy: generate context first/);
  });

  it("reports a clipboard failure truthfully instead of claiming a copy", async () => {
    const copyText = clipboardAdapter({ ok: false, mechanism: "none", reason: "no clipboard utility is installed" });
    const { app } = await generate({}, { copyText });

    app.dispatch(char("c"));
    await settle(4);

    assert.match(app.getState().notice.message, /✗ clipboard unavailable · no clipboard utility is installed/);
    assert.equal(app.getState().notice.level, "error");
  });

  it("states that the session has no clipboard adapter", async () => {
    const { app } = await generate();

    app.dispatch(char("c"));
    await settle(2);

    assert.match(app.getState().notice.message, /✗ clipboard unavailable · this session has no clipboard adapter/);
  });

  it("reports an adapter that throws as unavailable", async () => {
    const copyText = async () => {
      throw new Error("ENOTTY: not a terminal");
    };
    const { app } = await generate({}, { copyText });

    app.dispatch(char("c"));
    await settle(4);

    assert.match(app.getState().notice.message, /✗ clipboard unavailable · ENOTTY/);
  });

  it("refuses to copy while a synthesis is running", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    const copyText = clipboardAdapter();
    const { app } = await startApp(
      {
        agentContext: async () => {
          await pending;
          return CONTEXT_OK;
        },
      },
      { copyText }
    );
    app.dispatch(char("3"));
    app.dispatch(char("n"));
    for (const value of "explain auth") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(2);
    app.setFocus("inspector");

    app.dispatch(char("c"));
    await settle(2);
    assert.equal(copyText.copies.length, 0);
    assert.match(app.getState().notice.message, /synthesis is running · copy is available when it finishes/);

    release();
    await settle(12);
    app.setFocus("inspector");
    app.dispatch(char("c"));
    await settle(4);
    assert.equal(copyText.copies.length, 1, "copy is available as soon as the output exists");
  });

  it("copies the regenerated markdown after a re-synthesis", async () => {
    const copyText = clipboardAdapter();
    const { app } = await startApp({}, { copyText });
    app.dispatch(char("3"));
    app.dispatch(char("p"));
    app.dispatch(key("enter"));
    await settle();

    app.dispatch(char("r"));
    app.dispatch(key("enter"));
    await settle(14);

    app.dispatch(char("c"));
    await settle(4);

    assert.equal(copyText.copies[0].text, CONTEXT_OK.context_markdown, "the viewer copies what is now stored");
  });
});

describe("state: package catalog, append and export", () => {
  it("scopes the catalog to saved packages on p", async () => {
    const { app } = await startApp();
    await app.loadPrompts();
    app.dispatch(char("3"));
    assert.ok(app.contextRows().some((row) => row.kind === "suggestion"));

    app.dispatch(char("p"));
    assert.equal(app.getState().packageScope, "packages");
    assert.ok(app.contextRows().every((row) => row.kind === "package"));
    assert.equal(app.getState().cursors.context, 0, "the cursor is reset for the new scope");

    app.dispatch(char("p"));
    assert.equal(app.getState().packageScope, "all");
  });

  it("appends an iterative task to the selected package and shows the updated version", async () => {
    const { app, client } = await startApp();
    app.dispatch(char("3"));
    app.dispatch(char("p")); // packages only: the saved package is the first row
    app.dispatch(char("A"));
    assert.equal(app.getState().overlay.kind, "appendPackage");

    app.dispatch(key("enter"));
    assert.match(app.getState().overlay.error, /required/);
    assert.equal(client.calls.filter((call) => call.name === "appendContextPackage").length, 0);

    for (const value of "add tests") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle(8);

    assert.deepEqual(client.calls.find((call) => call.name === "appendContextPackage").args, ["pkg-1", { task: "add tests" }]);
    assert.equal(app.getState().overlay.kind, "viewPackage", "the updated package is shown after appending");
    assert.match(app.getState().notice.message, /appended to Auth context/);
  });

  it("keeps the append dialog open with the backend error when the append fails", async () => {
    const { app } = await startApp({
      appendContextPackage: async () => {
        throw new Error("package is locked");
      },
    });
    app.dispatch(char("3"));
    app.dispatch(char("p"));
    app.dispatch(char("A"));
    for (const value of "note") app.dispatch(char(value));
    app.dispatch(key("enter"));
    await settle();

    assert.equal(app.getState().overlay.kind, "appendPackage");
    assert.match(app.getState().overlay.error, /package is locked/);
    assert.match(app.getState().notice.message, /append failed/);
  });

  it("writes the stored markdown through the local export capability", async () => {
    const writes = [];
    const { app, client } = await startApp(
      {},
      {
        exportMarkdown: async ({ target, markdown }) => {
          writes.push({ target, markdown });
          return { path: "/tmp/auth-context.md", bytes: markdown.length };
        },
        exportFileName: (name) => `${String(name).toLowerCase().replace(/\s+/g, "-")}.md`,
      }
    );

    app.dispatch(char("3"));
    app.dispatch(char("p"));
    app.dispatch(char("e"));
    assert.equal(app.getState().overlay.kind, "exportPackage");
    assert.equal(app.getState().overlay.value, "auth-context.md", "the dialog is prefilled with a readable name");

    app.dispatch(key("enter"));
    await settle();

    assert.deepEqual(client.calls.find((call) => call.name === "getContextPackage").args, ["pkg-1"]);
    assert.equal(writes.length, 1);
    assert.equal(writes[0].markdown, PACKAGES[0].markdown, "the stored markdown is written unchanged");
    assert.match(app.getState().notice.message, /exported Auth context to \/tmp\/auth-context\.md/);
    assert.equal(app.getState().overlay, null);
  });

  it("states that export is unavailable and reports write failures honestly", async () => {
    const withoutCapability = await startApp();
    withoutCapability.app.dispatch(char("3"));
    withoutCapability.app.dispatch(char("p"));
    withoutCapability.app.dispatch(char("e"));
    assert.equal(withoutCapability.app.getState().overlay, null);
    assert.match(withoutCapability.app.getState().notice.message, /export is unavailable/);

    const failing = await startApp(
      {},
      {
        exportMarkdown: async () => {
          throw new Error("EACCES: permission denied");
        },
        exportFileName: () => "auth.md",
      }
    );
    failing.app.dispatch(char("3"));
    failing.app.dispatch(char("p"));
    failing.app.dispatch(char("e"));
    failing.app.dispatch(key("enter"));
    await settle();

    assert.equal(failing.app.getState().overlay.kind, "exportPackage");
    assert.match(failing.app.getState().overlay.error, /EACCES/);
    assert.match(failing.app.getState().notice.message, /export failed/);

    // A package the backend cannot return is an error, not an empty export.
    const missing = await startApp(
      { getContextPackage: () => null },
      { exportMarkdown: async () => ({ path: "/tmp/x.md" }), exportFileName: () => "x.md" }
    );
    missing.app.dispatch(char("3"));
    missing.app.dispatch(char("p"));
    missing.app.dispatch(char("e"));
    missing.app.dispatch(key("enter"));
    await settle();

    assert.match(missing.app.getState().overlay.error, /package not found/);
    assert.match(missing.app.getState().notice.message, /export failed/);
  });
});

describe("state: notices and viewport", () => {
  it("expires transient notices on tick", async () => {
    const { app } = await startApp();
    app.dispatch(char("s"));
    await settle();
    assert.ok(app.getState().notice);

    await app.tick(Date.now() + 10_000);
    assert.equal(app.getState().notice, null);
  });

  it("retries a failed backend sooner than the idle refresh cadence", async () => {
    const failure = () => Promise.reject(new Error("ECONNREFUSED"));
    const client = makeClient({
      health: failure,
      status: failure,
      providerStatus: failure,
      listRepositories: failure,
      listContextPackages: failure,
      memoryStats: failure,
    });
    const app = createApp({ client, now: () => Date.now(), summaryRefreshMs: 60_000, errorRetryMs: 1000 });
    await app.load();
    assert.equal(app.getState().error, "backend unavailable");

    const callsBefore = client.calls.length;
    // 2s is well below the idle cadence but above the error retry interval.
    await app.tick(Date.now() + 2000);
    assert.ok(client.calls.length > callsBefore, "a retry was issued while unreachable");
  });

  it("accepts the viewport metrics the frame publishes for paging and bounds", async () => {
    const { app } = await startApp();
    app.setViewport({ pageSize: 2, detailMax: 5, systemMax: 3, viewerMax: 4, helpMax: 1, overlayMax: 2 });
    assert.equal(app.getState().viewport.pageSize, 2);
    assert.equal(app.getState().viewport.detailMax, 5);

    app.dispatch(key("pageDown"));
    assert.equal(app.getState().cursors.repositories, 1);

    app.dispatch(key("enter")); // focus the detail, then clamp against its bound
    app.dispatch(key("end"));
    assert.equal(app.getState().scroll.repositories, 5, "the detail clamps at the published bound");
  });

  it("aggregates external indexing runs without starting a new one", async () => {
    const running = [{ ...REPOS[1], status: "indexing" }];
    const { app, client } = await startApp({
      listRepositories: { success: true, repositories: running, total_count: 1 },
    });

    assert.equal(app.getState().operation.kind, "indexing");
    assert.equal(app.getState().operation.external, true);
    assert.equal(client.calls.filter((call) => call.name === "indexRepository").length, 0);
  });

  it("completes an adopted external run from the backend's terminal progress", async () => {
    let lists = 0;
    const { app } = await startApp({
      listRepositories: () => {
        lists += 1;
        const status = lists <= 1 ? "indexing" : "indexed";
        return { success: true, repositories: [{ ...REPOS[1], status, file_count: 10 }], total_count: 1 };
      },
      repositoryProgress: {
        success: true,
        status: "indexed",
        stage: "Indexing completed",
        processed_files: 10,
        total_files: 10,
        failed_files: 0,
        elapsed_ms: 4200,
        error: null,
      },
    });
    assert.equal(app.getState().operation.external, true);

    await app.tick(Date.now() + 1000);

    assert.equal(app.getState().operation, null, "the operation line must not spin after the run is over");
    assert.equal(app.getState().lastRun.status, "indexed");
    assert.equal(app.getState().lastRun.processedFiles, 10);
    assert.equal(app.getState().lastRun.totalFiles, 10);
    assert.equal(app.getState().lastRun.elapsedMs, 4200);
  });

  it("fails an adopted external run with the backend's own error text", async () => {
    let lists = 0;
    const { app } = await startApp({
      listRepositories: () => {
        lists += 1;
        const status = lists <= 1 ? "indexing" : "error";
        return { success: true, repositories: [{ ...REPOS[1], status }], total_count: 1 };
      },
      repositoryProgress: {
        success: true,
        status: "error",
        stage: "Indexing failed",
        processed_files: 0,
        total_files: 0,
        elapsed_ms: 900,
        error: "embedding endpoint refused the connection",
      },
    });

    await app.tick(Date.now() + 1000);

    assert.equal(app.getState().operation, null);
    assert.equal(app.getState().lastRun.status, "error");
    assert.equal(app.getState().lastRun.stage, "embedding endpoint refused the connection");
  });

  it("keeps an adopted external run while the backend still reports indexing", async () => {
    const { app } = await startApp({
      listRepositories: { success: true, repositories: [{ ...REPOS[1], status: "indexing" }], total_count: 1 },
      repositoryProgress: { success: true, status: "indexing", stage: "Extracting AST call graphs and symbols...", stage_index: 2, stage_total: 5, elapsed_ms: 800 },
    });

    await app.tick(Date.now() + 1000);

    assert.equal(app.getState().operation.kind, "indexing");
    assert.equal(app.getState().operation.stage, "Extracting AST call graphs and symbols...");
    assert.equal(app.getState().operation.stageIndex, 2);
    assert.equal(app.getState().lastRun, null);
  });
});
