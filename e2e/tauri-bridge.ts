/**
 * Real runtime IPC bridge for browser smoke tests.
 * Injects window.__TAURI_INTERNALS__ to route frontend IPC commands directly
 * to the real Python FastAPI backend running at http://127.0.0.1:8765.
 */

export const TAURI_BRIDGE_INIT_SCRIPT = `
(function() {
  const BACKEND_URL = "http://127.0.0.1:8765";

  window.__RETRACK_FAULT_INJECTION__ = {
    failNextContext: false,
    failProvider: false,
  };

  window.__TAURI_INTERNALS__ = {
    invoke: async function(cmd, args) {
      // Allow fault injection for failure recovery testing
      if (cmd === "get_agent_context" && window.__RETRACK_FAULT_INJECTION__.failNextContext) {
        window.__RETRACK_FAULT_INJECTION__.failNextContext = false;
        throw new Error("Simulated LLM provider timeout (504 Gateway Timeout)");
      }
      if (cmd === "update_provider" && window.__RETRACK_FAULT_INJECTION__.failProvider) {
        throw new Error("Connection refused: Provider endpoint http://invalid-host:11434 is unreachable");
      }

      const get = async (path) => {
        const res = await fetch(BACKEND_URL + path);
        const data = await res.json();
        if (!res.ok) {
          const msg = data.detail?.message || data.detail || "Request failed";
          throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
        }
        return data;
      };

      const post = async (path, body) => {
        const res = await fetch(BACKEND_URL + path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body || {}),
        });
        const data = await res.json();
        if (!res.ok) {
          const msg = data.detail?.message || data.detail || "Request failed";
          throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
        }
        return data;
      };

      const del = async (path) => {
        const res = await fetch(BACKEND_URL + path, { method: "DELETE" });
        const data = await res.json();
        if (!res.ok) {
          const msg = data.detail?.message || data.detail || "Request failed";
          throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
        }
        return data;
      };

      switch (cmd) {
        case "health":
          return await get("/health");
        case "detailed_health":
          return await get("/health/detailed");
        case "get_status":
          return await get("/status");
        case "list_repositories":
        case "get_repository_summaries":
          return await get("/repos");
        case "create_repository":
          return await post("/repos", args?.request || args);
        case "scan_repository": {
          const id = args?.repoId || args?.repo_id || args?.id;
          return await post("/repos/" + id + "/scan", {});
        }
        case "get_repository_progress": {
          const id = args?.repoId || args?.repo_id || args?.id;
          return await get("/repos/" + id + "/progress");
        }
        case "delete_repository": {
          const id = args?.repoId || args?.repo_id || args?.id;
          return await del("/repos/" + id);
        }
        case "get_suggested_prompts": {
          const id = args?.repoId || args?.repo_id || args?.id;
          return await get("/repos/" + id + "/prompts");
        }
        case "get_agent_context":
          return await post("/api/v1/context", args?.request || args);
        case "generate_context":
          return await post("/context", args?.request || args);
        case "get_memory_stats":
          return await get("/memory/stats");
        case "get_memory_graph": {
          const d = args?.dataset ? "?dataset=" + encodeURIComponent(args.dataset) : "";
          return await get("/memory/graph" + d);
        }
        case "get_memory_vectors":
          return await get("/memory/vectors");
        case "list_datasets":
          return await get("/datasets");
        case "get_dataset_items": {
          const id = args?.datasetId || args?.dataset_id || args?.id;
          return await get("/datasets/" + id + "/items");
        }
        case "cognify_dataset":
          return await post("/memory/cognify", args?.request || args);
        case "forget_dataset":
          return await post("/forget", args?.request || args);
        case "list_context_packages":
          return await get("/packages");
        case "save_context_package":
          return await post("/packages", args?.request || args);
        case "get_context_package": {
          const id = args?.packageId || args?.package_id || args?.id;
          return await get("/packages/" + id);
        }
        case "delete_context_package": {
          const id = args?.packageId || args?.package_id || args?.id;
          return await del("/packages/" + id);
        }
        case "append_context_package": {
          const id = args?.packageId || args?.package_id || args?.id;
          return await post("/packages/" + id + "/append", args?.request || args);
        }
        case "get_diagnostics":
          return await get("/diagnostics");
        case "export_diagnostics":
          return await post("/diagnostics/export", {});
        case "get_provider_status":
          return await get("/provider/status");
        case "discover_provider":
          return await post("/provider/discover", args?.request || args);
        case "update_provider":
          return await post("/provider/update", args?.request || args);
        case "update_cognee_settings":
          return await post("/settings/cognee", args?.request || args);
        case "get_settings":
          return await get("/settings");
        case "get_dashboard_stats":
          return await get("/dashboard/stats");
        case "run_benchmark":
          return await post("/benchmarks/run", {});

        default:
          console.warn("Unhandled Tauri command in browser bridge:", cmd, args);
          return { success: true };
      }
    }
  };
})();
`;
