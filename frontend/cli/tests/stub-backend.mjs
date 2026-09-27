/**
 * Minimal RE:Track backend for CLI command tests.
 *
 * Serves the real HTTP contract shapes the CLI consumes and records every
 * request, so tests can assert both the rendered output and the exact calls the
 * command made. Nothing here is imported by the CLI itself.
 */

import { createServer } from "node:http";

export function defaultRepositories() {
  return [
    {
      id: "repo-a",
      name: "alpha",
      local_path: "/work/alpha",
      status: "indexed",
      file_count: 12,
      languages: ["Python", "Markdown"],
      indexed_at: "2026-09-20T10:00:00+00:00",
    },
    {
      id: "repo-b",
      name: "beta",
      local_path: "/work/beta",
      status: "registered",
      file_count: 0,
      languages: [],
      indexed_at: null,
    },
  ];
}

export function defaultPackages() {
  return [
    {
      id: "pkg-1",
      name: "Auth context",
      task: "Explain auth",
      objective: "Auth",
      repository_id: "repo-a",
      repository_name: "alpha",
      markdown: "# Auth context\n\n- `create_session`\n",
      token_estimate: 256,
      section_count: 3,
      created_at: "2026-09-25T10:00:00+00:00",
      updated_at: "2026-09-25T10:00:00+00:00",
    },
  ];
}

export function defaultIndexResult() {
  return {
    success: true,
    repository_path: "/work/alpha",
    dataset_name: "alpha",
    total_files: 12,
    processed_files: 12,
    failed_files: 0,
    total_batches: 2,
    failed_paths: [],
    summary: "Indexed 12/12 files",
  };
}

export function defaultContext() {
  return {
    success: true,
    context_markdown: "# Task Context\n\n- `create_session`\n",
    task_summary: "Explain auth",
    intent_category: "architecture",
    estimated_tokens: 120,
    evidence_state: "sufficient",
    evidence_score: 0.5,
    evidence_confidence: 0.5,
    abstained: false,
  };
}

function readBody(request) {
  return new Promise((resolve) => {
    let raw = "";
    request.on("data", (chunk) => {
      raw += chunk;
    });
    request.on("end", () => {
      if (!raw) return resolve(null);
      try {
        resolve(JSON.parse(raw));
      } catch {
        resolve(raw);
      }
    });
  });
}

export async function startStubBackend(overrides = {}) {
  const state = {
    repositories: overrides.repositories ?? defaultRepositories(),
    packages: overrides.packages ?? defaultPackages(),
    indexResult: overrides.indexResult ?? defaultIndexResult(),
    context: overrides.context ?? defaultContext(),
    progress: overrides.progress ?? {
      success: true,
      status: "indexing",
      stage: "Indexing repository files",
      stage_index: 3,
      stage_total: 5,
      processed_files: 0,
      total_files: 0,
      elapsed_ms: 1500,
    },
    providerStatus: overrides.providerStatus ?? {
      success: true,
      provider: "lmstudio",
      base_url: "http://127.0.0.1:1234/v1",
      active_model: "phi3:mini",
      is_reachable: true,
      health_state: "healthy",
      discovery_status: "available",
      loaded_models: [{ model_id: "phi3:mini", name: "phi3:mini", quantization: "unknown" }],
    },
    discovery: overrides.discovery ?? {
      success: true,
      provider: "lmstudio",
      base_url: "http://127.0.0.1:1234/v1",
      is_reachable: true,
      status: "available",
      models: [
        { model_id: "phi3:mini", name: "phi3:mini", quantization: "unknown" },
        { model_id: "qwen2.5-7b", name: "qwen2.5-7b", quantization: "Q4_K_M" },
      ],
      message: "",
    },
    settings: overrides.settings ?? {
      success: true,
      llm_provider: "lmstudio",
      llm_endpoint: "http://127.0.0.1:1234/v1",
      llm_model: "phi3:mini",
      embedding_model: "nomic-embed-text:latest",
      semantic_memory_provider: "lmstudio",
      memory_model: "phi3:mini",
      vector_db: "lancedb",
      graph_db: "kuzu",
      relational_db: "sqlite",
      enable_kg_extraction: true,
      auto_link_entities: false,
      caching: false,
      data_root: "/home/u/.retrack",
      system_root: "/home/u/.retrack/system",
      api_key_configured: false,
    },
    memory: overrides.memory ?? { success: true, total_size_display: "1.2 MB", dataset_count: 2, knowledge_graph_status: "extracted" },
    benchmark: overrides.benchmark ?? {
      success: true,
      results: [{ question: "How does auth work?", context_tokens: 900, compression_ratio: 0.4, token_savings_percent: 60, total_time_ms: 1200 }],
    },
    status: overrides.status ?? {
      status: "ok",
      llm_endpoint: "http://127.0.0.1:1234/v1",
      llm_model: "phi3:mini",
      embedding_model: "nomic-embed-text:latest",
      vector_db: "lancedb",
      graph_db: "kuzu",
      relational_db: "sqlite",
      data_root: "/home/u/.retrack",
      system_root: "/home/u/.retrack/system",
      cognee_initialized: true,
    },
    health: overrides.health ?? { status: "ok", provider_identity: "lmstudio", provider_health_state: "healthy", cognee_state: "healthy" },
  };

  const requests = [];
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    const route = `${request.method} ${url.pathname}`;
    const body = request.method === "GET" || request.method === "DELETE" ? null : await readBody(request);
    requests.push({ method: request.method, path: url.pathname, route, body });

    const send = (status, payload) => {
      response.statusCode = status;
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify(payload));
    };
    const notFound = (what) => send(404, { detail: `${what} not found` });

    const repoMatch = /^\/repos\/([^/]+)(?:\/(scan|progress))?$/.exec(url.pathname);
    const packageMatch = /^\/packages\/([^/]+)(?:\/(append))?$/.exec(url.pathname);

    if (route === "GET /health") return send(200, state.health);
    if (route === "GET /status") return send(200, state.status);
    if (route === "GET /repos") return send(200, { success: true, repositories: state.repositories, total_count: state.repositories.length });
    if (route === "POST /repos") {
      const repo = {
        id: "repo-new",
        name: body?.name ?? String(body?.local_path ?? "").split("/").filter(Boolean).pop() ?? "new",
        local_path: body?.local_path ?? "",
        status: "registered",
        file_count: 0,
        languages: [],
        indexed_at: null,
      };
      state.repositories.push(repo);
      return send(200, repo);
    }
    if (repoMatch) {
      const [, repoId, action] = repoMatch;
      const repo = state.repositories.find((item) => item.id === repoId);
      if (!repo) return notFound("repository");
      if (action === "scan") {
        Object.assign(repo, {
          languages: ["Python"],
          frameworks: ["FastAPI"],
          file_count: 42,
          size_bytes: 2048,
          status: repo.status === "indexed" ? "indexed" : "registered",
        });
        return send(200, { success: true, languages: repo.languages, frameworks: repo.frameworks, file_count: repo.file_count, size_bytes: repo.size_bytes });
      }
      if (action === "progress") return send(200, { success: true, repo_id: repoId, ...state.progress });
      if (request.method === "DELETE") {
        state.repositories = state.repositories.filter((item) => item.id !== repoId);
        return send(200, { success: true, message: `Repository ${repoId} deleted` });
      }
    }
    if (route === "GET /packages") return send(200, { success: true, packages: state.packages, total_count: state.packages.length });
    if (packageMatch) {
      const [, packageId, action] = packageMatch;
      const pkg = state.packages.find((item) => item.id === packageId);
      if (!pkg) return notFound("package");
      if (action === "append") {
        // Mirrors JsonContextPackageRepository.append: the additional task
        // replaces the stored task, the additional markdown extends the stored
        // content after a separator, and nothing else moves.
        pkg.markdown += `\n\n---\n\n${body?.additional_markdown ?? ""}`;
        pkg.task = body?.additional_task ?? pkg.task;
        if (body?.additional_objective) pkg.objective = body.additional_objective;
        return send(200, pkg);
      }
      if (request.method === "GET") return send(200, pkg);
      if (request.method === "PUT") {
        Object.assign(pkg, { markdown: body.markdown, updated_at: "2026-09-27T10:00:00+00:00" });
        if (body.objective !== undefined) pkg.objective = body.objective;
        if (body.token_estimate !== undefined) pkg.token_estimate = body.token_estimate;
        return send(200, pkg);
      }
      if (request.method === "DELETE") {
        state.packages = state.packages.filter((item) => item.id !== packageId);
        return send(200, { success: true });
      }
    }
    if (route === "POST /index") return send(200, state.indexResult);
    if (route === "POST /api/v1/context") return send(200, state.context);
    if (route === "GET /provider/status") return send(200, state.providerStatus);
    if (route === "POST /provider/discover") return send(200, state.discovery);
    if (route === "GET /settings") return send(200, state.settings);
    if (route === "GET /memory/stats") return send(200, state.memory);
    if (route === "POST /benchmarks/run") return send(200, state.benchmark);
    return notFound(url.pathname);
  });

  await new Promise((resolve, reject) => {
    server.on("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const { port } = server.address();

  return {
    state,
    requests,
    baseUrl: `http://127.0.0.1:${port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}
