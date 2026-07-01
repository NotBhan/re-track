import { create } from "zustand";
import type { HealthResponse, BackendStatusResponse } from "@/types";

interface HealthStore {
  health: HealthResponse | null;
  status: BackendStatusResponse | null;
  backendOnline: boolean;
  ollamaRunning: boolean;
  cogneeIdle: boolean;
  pollHealth: () => Promise<void>;
}

export const useHealthStore = create<HealthStore>((set) => ({
  health: null,
  status: null,
  backendOnline: false,
  ollamaRunning: false,
  cogneeIdle: true,

  pollHealth: async () => {
    try {
      const { health, getBackendStatus } = await import("@/lib/api");
      const [h, s] = await Promise.all([health(), getBackendStatus()]);
      set({
        health: h,
        status: s,
        backendOnline: h.status === "ok",
        ollamaRunning: h.ollama_reachable,
        cogneeIdle: h.cognee_initialized,
      });
    } catch {
      set({
        health: null,
        status: null,
        backendOnline: false,
        ollamaRunning: false,
        cogneeIdle: false,
      });
    }
  },
}));
