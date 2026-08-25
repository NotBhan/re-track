import { create } from "zustand";
import type { HealthResponse, BackendStatusResponse } from "@/lib/api";
import { health, getBackendStatus, getDashboardStats, type DashboardStats } from "@/lib/api";

export interface HealthStore {
  health: HealthResponse | null;
  status: BackendStatusResponse | null;
  backendOnline: boolean;
  providerIdentity: string;
  providerConfigured: boolean;
  providerReachable: boolean;
  providerHealthState: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  activeModel: string | null;
  configuredModel: string | null;
  activeModelState: string;
  discoveredModels: string[];
  engineState: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  engineReason: string | null;
  cogneeState: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  cogneeReason: string | null;
  cogneeInitialized: boolean;
  ollamaRunning: boolean; // Legacy alias for providerReachable
  cogneeIdle: boolean; // Legacy alias for cogneeInitialized
  dashboardStats: DashboardStats | null;
  pollHealth: () => Promise<void>;
  fetchDashboardStats: () => Promise<void>;
}

export const useHealthStore = create<HealthStore>((set) => ({
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

  pollHealth: async () => {
    try {
      const [hRes, sRes, dsRes] = await Promise.allSettled([
        health(),
        getBackendStatus(),
        getDashboardStats(),
      ]);

      const h = hRes.status === "fulfilled" ? hRes.value : null;
      const s = sRes.status === "fulfilled" ? sRes.value : null;
      const ds = dsRes.status === "fulfilled" ? dsRes.value : null;

      const isOnline = Boolean(h || s);

      const provIdentity =
        h?.provider_identity ||
        h?.provider ||
        s?.provider_identity ||
        s?.llm_provider ||
        "ollama";

      const provReachable = Boolean(
        h?.provider_reachable ??
          h?.ollama_reachable ??
          s?.provider_reachable ??
          s?.ollama_reachable ??
          false
      );

      const provConfigured = Boolean(
        h?.provider_configured ?? s?.provider_configured ?? true
      );

      const provHealthState =
        h?.provider_health_state ||
        s?.provider_health_state ||
        (provReachable ? "healthy" : "unavailable");

      const actModel = h?.active_model ?? s?.active_model ?? null;
      const cfgModel =
        h?.configured_model ?? s?.configured_model ?? s?.llm_model ?? null;
      const actModelState =
        h?.active_model_state ||
        s?.active_model_state ||
        (actModel ? "active" : "unknown");
      const discModels = h?.discovered_models || s?.discovered_models || [];

      const engState =
        h?.engine_state ||
        s?.engine_state ||
        (isOnline ? (provReachable ? "healthy" : "unavailable") : "unavailable");
      const engReason = h?.engine_reason ?? s?.engine_reason ?? null;

      const cogState =
        h?.cognee_state ||
        s?.cognee_state ||
        (h?.cognee_initialized || s?.cognee_initialized
          ? "healthy"
          : "unavailable");
      const cogReason = h?.cognee_reason ?? s?.cognee_reason ?? null;
      const cogInit = Boolean(
        h?.cognee_initialized ?? s?.cognee_initialized ?? false
      );

      set({
        health: h,
        status: s,
        dashboardStats: ds,
        backendOnline: isOnline,
        providerIdentity: provIdentity,
        providerConfigured: provConfigured,
        providerReachable: provReachable,
        providerHealthState: provHealthState,
        activeModel: actModel,
        configuredModel: cfgModel,
        activeModelState: actModelState,
        discoveredModels: discModels,
        engineState: engState,
        engineReason: engReason,
        cogneeState: cogState,
        cogneeReason: cogReason,
        cogneeInitialized: cogInit,
        ollamaRunning: provReachable,
        cogneeIdle: cogInit,
      });
    } catch (err) {
      console.error("DEBUG pollHealth failed:", err);
      set({
        health: null,
        status: null,
        backendOnline: false,
        providerIdentity: "unknown",
        providerConfigured: false,
        providerReachable: false,
        providerHealthState: "unavailable",
        activeModel: null,
        configuredModel: null,
        activeModelState: "unknown",
        discoveredModels: [],
        engineState: "unavailable",
        engineReason: "Backend is unreachable",
        cogneeState: "unavailable",
        cogneeReason: "Backend is unreachable",
        cogneeInitialized: false,
        ollamaRunning: false,
        cogneeIdle: false,
        dashboardStats: null,
      });
    }
  },

  fetchDashboardStats: async () => {
    try {
      const resp = await getDashboardStats();
      set({ dashboardStats: resp });
    } catch {
      set({ dashboardStats: null });
    }
  },
}));
