import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// In-memory Storage mock
const createStorageMock = () => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => (key in store ? store[key] : null)),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = String(value);
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((i: number) => Object.keys(store)[i] || null),
  };
};

const storageMock = createStorageMock();
Object.defineProperty(window, "localStorage", { value: storageMock, writable: true });
Object.defineProperty(global, "localStorage", { value: storageMock, writable: true });
Object.defineProperty(window, "sessionStorage", { value: createStorageMock(), writable: true });

// Polyfill window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Polyfill ResizeObserver & IntersectionObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

global.IntersectionObserver = class IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
};

window.scrollTo = vi.fn();

Object.defineProperty(navigator, "clipboard", {
  configurable: true,
  writable: true,
  value: {
    writeText: vi.fn().mockResolvedValue(undefined),
    readText: vi.fn().mockResolvedValue(""),
  },
});

// Mock invoke
export type MockInvokeHandler = (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
let customHandler: MockInvokeHandler | null = null;

export function setMockInvoke(handler: MockInvokeHandler | null) {
  customHandler = handler;
}

const defaultMockHandler: MockInvokeHandler = async (cmd, _args) => {
  if (cmd === "list_repositories") {
    return {
      success: true,
      repositories: [
        {
          id: "repo-1",
          name: "retrack-test-repo",
          source_type: "local",
          local_path: "/workspace/retrack-test-repo",
          branch: "main",
          status: "indexed",
          file_count: 42,
          size_bytes: 1048576,
          languages: ["Python", "TypeScript"],
          frameworks: ["FastAPI", "React"],
          entry_points: ["app.main", "src/index.tsx"],
          call_graph_status: "analyzed",
          call_graph_nodes: [
            { id: "node-1", label: "start_engine", file: "engine.py", kind: "function", line: 10 },
            { id: "node-2", label: "load_config", file: "config.py", kind: "function", line: 5 },
          ],
          call_graph_edges: [
            { source: "node-1", target: "node-2", kind: "calls" },
          ],
        },
      ],
      total_count: 1,
    };
  }

  if (cmd === "health") {
    return {
      status: "ok",
      provider_identity: "lmstudio",
      provider_reachable: true,
      provider_health_state: "healthy",
      active_model: "qwen2.5:0.5b",
      configured_model: "qwen2.5:0.5b",
      cpu_percent: 18.5,
      ram_used_gb: 8.2,
      ram_total_gb: 32.0,
      ram_percent: 25,
      gpu_presence: "NVIDIA",
      gpu_name: "RTX 4090",
      vram_used_gb: 4.1,
      vram_total_gb: 24.0,
      execution_device: "GPU",
      cognee_initialized: true,
    };
  }

  if (cmd === "get_status") {
    return {
      status: "ok",
      llm_provider: "lmstudio",
      llm_model: "qwen2.5:0.5b",
      embedding_model: "nomic-embed-text:latest",
      vector_db: "lancedb",
      graph_db: "kuzu",
      relational_db: "sqlite",
      cognee_initialized: true,
    };
  }

  if (cmd === "get_agent_context") {
    return {
      success: true,
      context_markdown: "# Synthesized Context\n\n- File: `engine.py`\n- Symbol: `start_engine`",
      task_summary: "Authentication and Engine Startup",
      intent_category: "feature_implementation",
      extracted_symbols: ["start_engine", "load_config"],
      callers: [],
      callees: ["load_config"],
      related_files: ["engine.py", "config.py"],
      estimated_tokens: 520,
      generation_time_ms: 180,
      evidence_state: "verified",
      evidence_score: 0.95,
      evidence_confidence: 0.95,
      abstained: false,
    };
  }

  if (cmd === "list_datasets") {
    return {
      success: true,
      datasets: [
        {
          id: "ds-1",
          name: "retrack-test-repo",
          type: "repository",
          size_bytes: 1048576,
          file_count: 42,
          created_at: new Date().toISOString(),
          source_path: "/workspace/retrack-test-repo",
        },
      ],
      total_count: 1,
    };
  }

  if (cmd === "get_dataset_items") {
    return {
      success: true,
      dataset_id: "ds-1",
      dataset_name: "retrack-test-repo",
      items: [
        {
          id: "item-1",
          name: "engine.py",
          mime_type: "text/x-python",
          data_size: 4096,
          extension: "py",
          content_hash: "sha256-abcdef123456",
        },
      ],
      total_count: 1,
    };
  }

  if (cmd === "get_memory_stats") {
    return {
      success: true,
      total_size_display: "1.05 MB",
      dataset_count: 1,
      knowledge_graph_status: "extracted",
      graph_nodes: 12,
      graph_edges: 8,
    };
  }

  if (cmd === "get_memory_vectors") {
    return {
      success: true,
      vector_db_provider: "lancedb",
      embedding_model: "nomic-embed-text:latest",
      embedding_dimensions: 768,
      total_datasets: 1,
      total_files: 42,
      datasets: [
        {
          id: "ds-1",
          name: "retrack-test-repo",
          file_count: 42,
          size_bytes: 1048576,
          vector_status: "ready",
          chunk_count: 85,
        },
      ],
    };
  }

  if (cmd === "get_memory_graph") {
    return {
      success: true,
      status: "extracted",
      nodes: [
        { id: "e-1", label: "EngineService", kind: "class" },
        { id: "e-2", label: "DatabasePool", kind: "class" },
      ],
      edges: [
        { source: "EngineService", target: "DatabasePool", kind: "uses", relationship_type: "DEPENDS_ON" },
      ],
      total_nodes: 2,
      total_edges: 1,
      message: "Graph retrieved",
    };
  }

  if (cmd === "get_settings") {
    return {
      success: true,
      vector_db: "lancedb",
      graph_db: "kuzu",
      relational_db: "sqlite",
      enable_kg_extraction: true,
      auto_link_entities: false,
      caching: false,
      data_root: "/home/user/.retrack/data",
      system_root: "/home/user/.retrack/system",
      llm_provider: "lmstudio",
      llm_endpoint: "http://localhost:1234/v1",
      llm_host: "localhost",
      llm_port: 1234,
      llm_model: "qwen2.5:0.5b",
      embedding_model: "nomic-embed-text:latest",
    };
  }

  if (cmd === "get_provider_status") {
    return {
      success: true,
      provider: "lmstudio",
      base_url: "http://localhost:1234/v1",
      active_model: "qwen2.5:0.5b",
      is_reachable: true,
      health_state: "healthy",
      discovery_status: "available",
      loaded_models: [
        {
          model_id: "qwen2.5:0.5b",
          name: "qwen2.5:0.5b",
          quantization: "Q4_K_M",
          is_phi4_mini: false,
          is_q6_or_higher: false,
        },
      ],
      api_key_configured: false,
      api_key_masked: "local",
    };
  }

  if (cmd === "get_suggested_prompts") {
    return {
      success: true,
      prompts: [
        { label: "Engine Startup", prompt: "Explain how the engine starts up" },
      ],
      source: "heuristic",
    };
  }

  if (cmd === "list_context_packages") {
    return {
      success: true,
      packages: [],
      total_count: 0,
    };
  }

  return { success: true };
};

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string, args?: Record<string, unknown>) => {
    if (customHandler) {
      return customHandler(cmd, args);
    }
    return defaultMockHandler(cmd, args);
  }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  storageMock.clear();
  customHandler = null;
});
