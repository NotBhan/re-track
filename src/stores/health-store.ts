import { create } from "zustand";
import type { HealthResponse, BackendStatusResponse } from "@/lib/api";
import { health, getBackendStatus, getDashboardStats, type DashboardStats } from "@/lib/api";

interface HealthStore {
  health: HealthResponse | null;
  status: BackendStatusResponse | null;
  backendOnline: boolean;
  ollamaRunning: boolean;
  cogneeIdle: boolean;
  dashboardStats: DashboardStats | null;
  pollHealth: () => Promise<void>;
  fetchDashboardStats: () => Promise<void>;
}

export const useHealthStore = create<HealthStore>((set) => ({
  health: null,
  status: null,
  backendOnline: false,
  ollamaRunning: false,
  cogneeIdle: true,
  dashboardStats: null,

  pollHealth: async () => {
    try {
      const [h, s, ds] = await Promise.all([
        health(),
        getBackendStatus(),
        getDashboardStats(),
      ]);
      set({
        health: h,
        status: s,
        backendOnline: h.status === "ok" || h.status === "degraded",
        ollamaRunning: Boolean(h.ollama_reachable),
        cogneeIdle: Boolean(h.cognee_initialized),
        dashboardStats: ds,
      });
    } catch (err) {
      console.error("DEBUG pollHealth failed:", err);
      set({
        health: null,
        status: null,
        backendOnline: false,
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
