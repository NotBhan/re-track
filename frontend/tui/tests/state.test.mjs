import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { createApp, TOKEN_BUDGETS } from "../state.mjs";

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
    markdown: "# Auth\n\n- session",
    token_estimate: 320,
    created_at: "2026-09-24T09:00:00Z",
  },
];

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
  const base = {
    health: { status: "ok", provider_identity: "lmstudio", provider_reachable: true, concurrency_available_slots: 1, concurrency_queue_depth: 0, configured_model: "phi3:mini", active_model: null },
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

const key = (name, extra = {}) => ({ name, ...extra });
const char = (value) => ({ name: "char", char: value });

async function settle(times = 4) {
  for (let index = 0; index < times; index += 1) {
    await new Promise((resolve) => setImmediate(resolve));
  }
}

async function startApp(overrides = {}) {
  const client = makeClient(overrides);
  const app = createApp({ client, now: () => Date.now() });
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

  it("accepts viewport metrics used for paging and scrolling bounds", async () => {
    const { app } = await startApp();
    app.setViewport({ pageSize: 2, inspectorMax: 5, systemMax: 3, viewerMax: 4 });
    assert.equal(app.getState().viewport.pageSize, 2);

    app.dispatch(key("pageDown"));
    assert.equal(app.getState().cursors.repositories, 1);
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
});
