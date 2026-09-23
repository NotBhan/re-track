import { describe, it, expect, beforeEach } from "vitest";
import {
  health,
  getMemoryStats,
  getMemoryGraph,
  listRepositories,
  getDetailedHealth,
  type MemoryStatsResponse,
  type MemoryGraphResponse,
  type DetailedHealthResponse,
} from "@/lib/api";
import {
  resetAllStores,
  setMockInvokeHandler,
  createDefaultMockHandler,
  mockRepositories,
} from "@/test/test-utils";

describe("API Contract & Truth Boundary Guarantees", () => {
  beforeEach(() => {
    resetAllStores();
    setMockInvokeHandler(null);
  });

  it("truth boundary: maintains strict data fidelity with backend MemoryStats API contract", async () => {
    const authoritativeStats: MemoryStatsResponse = {
      success: true,
      total_size_display: "1.4 MB",
      dataset_count: 7,
      knowledge_graph_status: "extracted",
      graph_nodes: 89,
      graph_edges: 142,
    };

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_memory_stats") {
        return authoritativeStats;
      }
      return defaultMock(cmd, args);
    });

    const result = await getMemoryStats();

    // Verify exact backend field preservation without mutation or synthetic defaults
    expect(result.dataset_count).toBe(7);
    expect(result.total_size_display).toBe("1.4 MB");
    expect(result.knowledge_graph_status).toBe("extracted");
    expect(result.graph_nodes).toBe(89);
    expect(result.graph_edges).toBe(142);
  });

  it("truth boundary: Memory Graph preserves exact node IDs and caller/callee relationships", async () => {
    const authoritativeGraph: MemoryGraphResponse = {
      success: true,
      status: "extracted",
      total_nodes: 3,
      total_edges: 2,
      message: "Extracted memory graph",
      nodes: [
        { id: "app.main:init_app", label: "init_app", kind: "function", type: "Function" },
        { id: "app.db:connect", label: "connect", kind: "function", type: "Function" },
        { id: "app.db:Engine", label: "Engine", kind: "class", type: "Class" },
      ],
      edges: [
        { source: "app.main:init_app", target: "app.db:connect", kind: "calls", relationship_type: "calls" },
        { source: "app.db:connect", target: "app.db:Engine", kind: "instantiates", relationship_type: "instantiates" },
      ],
    };

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "get_memory_graph") {
        return authoritativeGraph;
      }
      return defaultMock(cmd, args);
    });

    const result = await getMemoryGraph("re-track-core");

    expect(result.nodes).toHaveLength(3);
    expect(result.edges).toHaveLength(2);
    expect(result.edges[0].source).toBe("app.main:init_app");
    expect(result.edges[0].target).toBe("app.db:connect");
    expect(result.edges[1].relationship_type).toBe("instantiates");
  });

  it("truth boundary: Repository list preserves deterministic AST call graph topologies", async () => {
    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "list_repositories") {
        return {
          success: true,
          repositories: mockRepositories,
          total_count: mockRepositories.length,
        };
      }
      return defaultMock(cmd, args);
    });

    const result = await listRepositories();

    expect(result.success).toBe(true);
    expect(result.repositories).toHaveLength(mockRepositories.length);
    expect(result.repositories[0].call_graph_nodes).toBeDefined();
    expect(result.repositories[0].call_graph_edges).toBeDefined();
    expect(result.repositories[0].call_graph_nodes!.length).toBeGreaterThan(0);
    expect(result.repositories[0].call_graph_edges!.length).toBeGreaterThan(0);
  });

  it("truth boundary: Detailed Health preserves hardware telemetry and queue capacity", async () => {
    const authoritativeHealth: DetailedHealthResponse = {
      status: "ok",
      version: "0.1.0",
      health_state: "healthy",
      ollama_reachable: true,
      cognee_initialized: true,
      ram_total_gb: 32.0,
      ram_used_gb: 12.4,
      ram_percent: 38.75,
      high_memory_pressure: false,
      gpu_presence: "NVIDIA",
      gpu_name: "NVIDIA RTX 4090",
      execution_device: "GPU",
      concurrency_queue_depth: 0,
      concurrency_queue_capacity: 5,
      concurrency_available_slots: 3,
      storage_canonical_exists: true,
      storage_canonical_writable: true,
    };

    const defaultMock = createDefaultMockHandler();
    setMockInvokeHandler(async (cmd: string, args) => {
      if (cmd === "detailed_health") {
        return authoritativeHealth;
      }
      return defaultMock(cmd, args);
    });

    const result = await getDetailedHealth();

    expect(result.health_state).toBe("healthy");
    expect(result.gpu_presence).toBe("NVIDIA");
    expect(result.gpu_name).toBe("NVIDIA RTX 4090");
    expect(result.execution_device).toBe("GPU");
    expect(result.concurrency_available_slots).toBe(3);
    expect(result.storage_canonical_writable).toBe(true);
  });

  it("propagates backend exceptions with descriptive error message", async () => {
    setMockInvokeHandler(async (cmd: string) => {
      if (cmd === "health") {
        throw new Error("Tauri IPC Backend Connection Refused");
      }
      throw new Error(`Unhandled command ${cmd}`);
    });

    await expect(health()).rejects.toThrow("Tauri IPC Backend Connection Refused");
  });
});
