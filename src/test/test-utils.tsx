import React, { ReactElement } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { MemoryRouter, MemoryRouterProps } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";

import { useRepositoryStore } from "@/stores/repository-store";
import { useContextStore } from "@/stores/context-store";
import { useContextPackageStore } from "@/stores/context-package-store";
import { useMemoryStore } from "@/stores/memory-store";
import { useHealthStore } from "@/stores/health-store";
import { useSettingsStore } from "@/stores/settings-store";

import type { Repository } from "@/types/repository";
import type {
  HealthResponse,
  DetailedHealthResponse,
  BackendStatusResponse,
  DashboardStats,
  ContextResponse,
  SavedContextPackage,
  AppSettingsResponse,
  BenchmarkSuiteResponse,
} from "@/lib/api";

// --- Standard Test Fixtures ---

export const mockHealthData: HealthResponse = {
  status: "ok",
  ollama_reachable: true,
  cognee_initialized: true,
  version: "0.1.0",
  ram_total_gb: 32,
  ram_used_gb: 12,
  ram_percent: 37.5,
  high_memory_pressure: false,
  cpu_percent: 15.2,
  gpu_presence: "NVIDIA",
  gpu_name: "RTX 4090",
  vram_total_gb: 24,
  vram_used_gb: 6,
  execution_device: "GPU",
  provider: "ollama",
  provider_identity: "ollama",
  provider_configured: true,
  provider_reachable: true,
  provider_health_state: "healthy",
  provider_base_url: "http://localhost:11434/v1",
  configured_model: "qwen2.5-coder:7b",
  active_model: "qwen2.5-coder:7b",
  active_model_state: "active",
  discovered_models: ["qwen2.5-coder:7b"],
  engine_state: "healthy",
  engine_reason: null,
  cognee_state: "healthy",
  cognee_reason: null,
  health_state: "healthy",
  storage_canonical_exists: true,
  storage_canonical_writable: true,
  legacy_storage_detected: false,
  repository_count: 1,
  context_package_count: 2,
  cache_files_count: 5,
  cache_total_bytes: 1048576,
  concurrency_queue_depth: 0,
  concurrency_queue_capacity: 4,
  concurrency_available_slots: 4,
  mcp_server_ready: true,
  recent_errors_count: 0,
};

export const mockDetailedHealthData: DetailedHealthResponse = {
  ...mockHealthData,
  diagnostics_log_entries: [
    {
      timestamp: "2026-08-23T12:00:00.000Z",
      level: "INFO",
      logger: "app.core.logging",
      message: "Application started successfully",
      correlation_id: "corr-123",
    },
  ],
  storage_paths: {
    canonical_root: "/home/user/.retrack",
    databases_dir: "/home/user/.retrack/databases",
    logs_dir: "/home/user/.retrack/logs",
  },
};

export const mockBackendStatus: BackendStatusResponse = {
  status: "ok",
  ollama_reachable: true,
  ollama_host: "http://localhost",
  ollama_port: 11434,
  llm_model: "qwen2.5-coder:7b",
  embedding_model: "nomic-embed-text",
  vector_db: "lancedb",
  graph_db: "kuzu",
  relational_db: "sqlite",
  data_root: "/home/user/.retrack/databases",
  system_root: "/home/user/.retrack",
  cognee_initialized: true,
  gpu_presence: "NVIDIA",
  execution_device: "GPU",
  provider_identity: "ollama",
  provider_configured: true,
  provider_reachable: true,
  provider_health_state: "healthy",
  configured_model: "qwen2.5-coder:7b",
  active_model: "qwen2.5-coder:7b",
  active_model_state: "active",
  discovered_models: ["qwen2.5-coder:7b"],
  engine_state: "healthy",
  engine_reason: null,
  cognee_state: "healthy",
  cognee_reason: null,
};

export const mockDashboardStats: DashboardStats = {
  success: true,
  indexed_repos: 1,
  total_files: 42,
  total_embeddings: 120,
  packages_generated: 4,
  avg_gen_time_ms: 250,
  last_indexed_repo: "re-track-core",
  last_indexed_time: "2026-08-20T10:00:00Z",
};

export const mockRepositories: Repository[] = [
  {
    id: "repo-1",
    name: "re-track-core",
    source_type: "local",
    source_url: null,
    local_path: "/home/user/re-track-core",
    branch: "main",
    commit_hash: "a1b2c3d",
    status: "indexed",
    languages: ["Python", "TypeScript"],
    frameworks: ["FastAPI", "React"],
    file_count: 42,
    size_bytes: 524288,
    indexed_at: "2026-08-20T10:00:00Z",
    error_message: null,
    summary: "RefinedEngine Track Context Engine core repository.",
    entry_points: ["backend/app/cli/main.py", "src/main.tsx"],
    architecture: "Hexagonal / Ports and Adapters",
    components: ["ContextEngine", "AstExtractor", "CogneeAdapter"],
    dependencies: ["fastapi", "cognee", "pydantic"],
    metadata: {},
    call_graph_status: "analyzed",
    call_graph_nodes: [
      { id: "node-1", label: "generate_context", file: "backend/app/services/context.py", kind: "function", line: 45 },
      { id: "node-2", label: "ContextService", file: "backend/app/services/context.py", kind: "class", line: 20 },
      { id: "node-3", label: "extract_ast", file: "backend/app/services/ast.py", kind: "function", line: 12 },
    ],
    call_graph_edges: [
      { source: "node-1", target: "node-2", kind: "calls" },
      { source: "node-2", target: "node-3", kind: "calls" },
    ],
  },
];

export const mockContextResponse: ContextResponse = {
  success: true,
  task: "Implement token budget pruning",
  objective: "Synthesize token-budgeted prompt context for LLM code generation",
  markdown: "## Goal\nImplement token budget pruning\n\n## Relevant Files\n- `backend/app/services/context.py`\n- `src/pages/ContextStudio.tsx`",
  section_count: 3,
  source_count: 2,
  token_estimate: 420,
  dataset: "repo-1",
  retrieved_memories: 3,
  deduplicated_memories: 3,
  compressed_memories: 3,
  compression_ratio: 0.88,
  retrieval_time_ms: 45,
  total_time_ms: 120,
  reference_count: 2,
  section_headings: ["Goal", "Relevant Files"],
};

export const mockSavedPackages: SavedContextPackage[] = [
  {
    id: "pkg-1",
    name: "Context Package - Token Budgeting",
    task: "Implement token budget pruning",
    objective: "Synthesize token-budgeted prompt context",
    repository_id: "repo-1",
    repository_name: "re-track-core",
    repository_branch: "main",
    repository_commit: "abcdef1",
    indexing_version: "0.1.0",
    markdown: "## Goal\nImplement token budget pruning",
    section_count: 2,
    token_estimate: 420,
    retrieved_memories: 3,
    deduplicated_memories: 3,
    compression_ratio: 0.88,
    total_time_ms: 120,
    created_at: "2026-08-21T14:30:00Z",
    updated_at: "2026-08-21T14:30:00Z",
    tags: ["context", "feature"],
  },
];

export const mockAppSettings: AppSettingsResponse = {
  success: true,
  vector_db: "lancedb",
  graph_db: "kuzu",
  relational_db: "sqlite",
  enable_kg_extraction: true,
  auto_link_entities: true,
  caching: true,
  data_root: "/home/user/.retrack/databases",
  system_root: "/home/user/.retrack",
  llm_provider: "ollama",
  llm_host: "http://localhost",
  llm_port: 11434,
  llm_model: "qwen2.5-coder:7b",
  embedding_model: "nomic-embed-text",
};

export const mockMemoryOverview = {
  success: true,
  datasets: [
    {
      id: "repo-1",
      name: "re-track-core",
      created_at: "2026-08-20T10:00:00Z",
      updated_at: "2026-08-20T10:00:00Z",
      document_count: 42,
      data_points_count: 120,
    },
  ],
  total_datasets: 1,
  total_documents: 42,
  total_data_points: 120,
};

export const mockBenchmarkResponse: BenchmarkSuiteResponse = {
  success: true,
  total_questions: 5,
  avg_retrieval_latency_ms: 120.5,
  avg_total_latency_ms: 245.5,
  avg_latency_ms: 245.5,
  avg_token_savings_percent: 94.2,
  avg_compression_ratio: 17.2,
  avg_tokens: 380,
  results: [
    {
      question: "How does the AST call graph extract module dependencies?",
      baseline_tokens: 25000,
      context_tokens: 380,
      token_count: 380,
      compression_ratio: 65.8,
      token_savings_percent: 98.5,
      retrieval_time_ms: 95.0,
      total_time_ms: 210.0,
      latency_ms: 210.0,
      section_count: 5,
      retrieved_memories: 8,
      passed: true,
    },
  ],
  run_metadata: {
    baseline_tokens: 25000,
    eligible_source_files: 42,
  },
};

import { setCustomMockHandler, setDefaultMockHandler } from "@/test/setup";

export type MockInvokeHandler = (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;

export function setMockInvokeHandler(handler: MockInvokeHandler | null) {
  setCustomMockHandler(handler);
}

export function createDefaultMockHandler(): MockInvokeHandler {
  return async (cmd: string, args?: Record<string, unknown>) => {
    switch (cmd) {
      case "health":
      case "get_health":
        return mockHealthData;
      case "get_status":
        return mockBackendStatus;
      case "get_dashboard_stats":
        return mockDashboardStats;
      case "detailed_health":
        return mockDetailedHealthData;
      case "list_repositories":
        return { success: true, repositories: mockRepositories, total_count: mockRepositories.length };
      case "create_repository": {
        const req = args?.request as Record<string, unknown>;
        const newRepo: Repository = {
          id: `repo-${Date.now()}`,
          name: (req?.name as string) || "new-repo",
          source_type: "local",
          source_url: null,
          local_path: (req?.local_path as string) || "/path/to/repo",
          branch: "main",
          commit_hash: "1234567",
          status: "registered",
          languages: ["Python"],
          frameworks: ["FastAPI"],
          file_count: 10,
          size_bytes: 10000,
          indexed_at: null,
          error_message: null,
          summary: "Newly registered test repository",
          entry_points: [],
          architecture: "Standard",
          components: [],
          dependencies: [],
          metadata: {},
          call_graph_status: "not_analyzed",
        };
        return newRepo;
      }
      case "index_repository":
        return {
          success: true,
          repository_path: "/path/to/repo",
          dataset_name: "test-dataset",
          total_files: 42,
          processed_files: 42,
          failed_files: 0,
          total_batches: 1,
          failed_paths: [],
          summary: "Indexed successfully",
        };
      case "delete_repository":
        return { success: true };
      case "generate_context":
        return mockContextResponse;
      case "list_context_packages":
        return { success: true, packages: mockSavedPackages, total_count: mockSavedPackages.length };
      case "save_context_package":
        return mockSavedPackages[0];
      case "delete_context_package":
        return { success: true };
      case "list_datasets":
        return {
          success: true,
          datasets: [
            {
              id: "ds-1",
              name: "re-track-core",
              type: "codebase",
              size_bytes: 1048576,
              created_at: "2026-08-20T10:00:00Z",
              file_count: 42,
              source_path: "/home/user/re-track",
            },
          ],
          total_count: 1,
        };
      case "get_memory_stats":
        return {
          success: true,
          total_size_display: "1.0 MB",
          dataset_count: 1,
          knowledge_graph_status: "extracted",
          graph_nodes: 45,
          graph_edges: 32,
        };
      case "get_memory_graph":
        return {
          success: true,
          status: "extracted",
          nodes: [
            { id: "node-1", label: "ContextService", kind: "class" },
            { id: "node-2", label: "generate_context", kind: "function" },
          ],
          edges: [
            { source: "node-1", target: "node-2", kind: "calls" },
          ],
          total_nodes: 2,
          total_edges: 1,
          message: "Graph loaded",
        };
      case "get_memory_vectors":
        return {
          success: true,
          vector_db_provider: "lancedb",
          embedding_model: "text-embedding-3-small",
          embedding_dimensions: 1536,
          total_datasets: 1,
          total_files: 42,
          total_vectors: 250,
          datasets: [
            {
              id: "ds-1",
              name: "re-track-core",
              file_count: 42,
              size_bytes: 1048576,
              vector_status: "ready",
              chunk_count: 250,
            },
          ],
        };
      case "get_dataset_items":
        return {
          success: true,
          dataset_id: "ds-1",
          dataset_name: "re-track-core",
          items: [],
          total_count: 0,
        };
      case "cognify_dataset":
        return {
          success: true,
          dataset_name: "re-track-core",
          total_vectors: 250,
          total_nodes: 45,
          total_edges: 32,
          message: "Dataset cognified",
        };
      case "forget_dataset":
        return { success: true, message: "Dataset forgotten" };
      case "get_memory_overview":
        return mockMemoryOverview;
      case "run_benchmark":
        return mockBenchmarkResponse;
      case "get_settings":
        return mockAppSettings;
      case "get_provider_status":
        return {
          success: true,
          provider: "ollama",
          base_url: "http://127.0.0.1:11434/v1",
          active_model: "phi4-mini:q6_k",
          is_reachable: true,
          health_state: "healthy",
          discovery_status: "available",
          loaded_models: [
            {
              model_id: "phi4-mini:q6_k",
              name: "phi4-mini",
              quantization: "q6_k",
              is_phi4_mini: true,
              is_q6_or_higher: true,
              warning: null,
            },
          ],
          quantization_warning: null,
          api_key_configured: false,
          api_key_masked: "local",
        };
      case "discover_provider":
        return {
          success: true,
          provider: "ollama",
          base_url: "http://127.0.0.1:11434/v1",
          is_reachable: true,
          status: "available",
          models: [
            {
              model_id: "phi4-mini:q6_k",
              name: "phi4-mini",
              quantization: "q6_k",
              is_phi4_mini: true,
              is_q6_or_higher: true,
              warning: null,
            },
          ],
          message: "Discovered 1 model(s) from ollama.",
          error_details: null,
        };
      case "update_provider":
        return {
          success: true,
          provider: "ollama",
          base_url: "http://127.0.0.1:11434/v1",
          model: "phi4-mini:q6_k",
          reachable: true,
          health_state: "healthy",
          loaded_models: ["phi4-mini:q6_k"],
          quantization_warning: null,
          api_key_configured: false,
          api_key_masked: "local",
        };
      case "update_cognee_settings":
        return mockAppSettings;
      case "get_diagnostics":
        return { status: "healthy", version: "0.1.0", queue_depth: 0 };
      case "export_diagnostics":
        return { status: "ok", export_path: "/home/user/.retrack/diagnostics/retrack-diag-20260823.json" };
      case "get_suggested_prompts":
        return {
          success: true,
          prompts: [
            { label: "Understand Architecture", prompt: "Explain the architecture of this repository" },
            { label: "Find Key Endpoints", prompt: "Where are the main API endpoints defined?" },
          ],
          source: "ai",
        };
      default:
        return { success: true };
    }
  };
}


// Initialize default mock handler
setDefaultMockHandler(createDefaultMockHandler());

import { queryCache } from "@/lib/query-cache";

// --- Reset Store State Utility ---

export function resetAllStores() {
  queryCache.invalidate();

  useRepositoryStore.setState({
    repositories: [],
    selectedId: null,
    selected: undefined,
    searchQuery: "",
    loading: false,
    indexing: false,
    scanning: false,
    error: null,
    lastScan: null,
    progress: null,
    pollInterval: null,
  });

  useContextStore.setState({
    objective: "",
    selectedRepo: "",
    selectedRepoId: null,
    topK: 10,
    advancedOptions: {
      dedup: true,
      resolveRefs: true,
      aggressiveCompress: false,
    },
    result: null,
    loading: false,
    error: null,
    history: [],
    recommendedPrompts: [],
    promptSource: "heuristic",
    loadingPrompts: false,
    promptsInitialized: false,
  });

  useContextPackageStore.setState({
    packages: [],
    loading: false,
    error: null,
  });

  useMemoryStore.setState({
    datasets: [],
    stats: null,
    vectors: null,
    graph: null,
    selectedDatasetItems: [],
    activeTab: "datasets",
    selectedDatasetId: null,
    selectedNodeId: null,
    searchQuery: "",
    sortBy: "date",
    loading: false,
    loadingGraph: false,
    loadingVectors: false,
    loadingItems: false,
    cognifying: false,
    cognifyingDataset: null,
    cognifyError: null,
    reindexingDatasetId: null,
    reindexError: null,
  });

  useHealthStore.setState({
    health: null,
    status: null,
    backendOnline: false,
    providerIdentity: "ollama",
    providerConfigured: true,
    providerReachable: false,
    providerHealthState: "unavailable",
    activeModel: null,
    configuredModel: null,
    activeModelState: "unknown",
    discoveredModels: [],
    engineState: "unavailable",
    engineReason: null,
    cogneeState: "unavailable",
    cogneeReason: null,
    cogneeInitialized: false,
    ollamaRunning: false,
    cogneeIdle: true,
    dashboardStats: null,
  });

  useSettingsStore.setState({
    activeTab: "backend",
    provider: "ollama",
    endpoint: "http://localhost:11434/v1",
    model: "phi4-mini",
    apiKey: "",
    apiKeyConfigured: false,
    apiKeyMasked: "local",
    providerReachable: true,
    providerHealthState: "healthy",
    quantizationWarning: null,
    availableModels: [],
    discovering: false,
    discoveryStatus: "idle",
    discoveryMessage: "",
    discoveryError: null,
    vectorDb: "lancedb",
    graphDb: "kuzu",
    relationalDb: "sqlite",
    enableKgExtraction: true,
    autoLinkEntities: true,
    caching: true,
    dataRoot: "",
    systemRoot: "",
    loading: false,
    saving: false,
    saveSuccess: null,
    statusMessage: null,
    error: null,
  });

}

import { LayoutProvider } from "@/components/layout/LayoutContext";

// --- Custom Render Wrapper ---

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  initialEntries?: MemoryRouterProps["initialEntries"];
  withRouter?: boolean;
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { initialEntries = ["/"], withRouter = true, ...renderOptions } = options;

  function Wrapper({ children }: { children: React.ReactNode }) {
    const inner = (
      <LayoutProvider>
        <TooltipProvider>{children}</TooltipProvider>
      </LayoutProvider>
    );

    if (!withRouter) {
      return inner;
    }
    return (
      <MemoryRouter initialEntries={initialEntries}>
        {inner}
      </MemoryRouter>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
