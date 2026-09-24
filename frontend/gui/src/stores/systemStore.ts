import { create } from "zustand";
import type {
  HealthResponse,
  BackendStatusResponse,
  DetailedHealthResponse,
  ProviderStatusResponse,
  DiscoveredModel,
  AppSettingsResponse,
  BenchmarkSuiteResponse,
  CogneeSettingsRequest,
} from "../types/api";
import {
  getHealth,
  getBackendStatus,
  getDetailedHealth,
  getProviderStatus,
  discoverProvider,
  updateProvider,
  getAppSettings,
  updateCogneeSettings,
  runBenchmark,
  exportDiagnostics,
  getDiagnostics,
} from "../lib/api";

export type SystemTab = "providers" | "telemetry" | "storage" | "diagnostics" | "benchmarks" | "display";

interface SystemStore {
  activeTab: SystemTab;
  backendOnline: boolean;

  health: HealthResponse | null;
  status: BackendStatusResponse | null;
  detailedHealth: DetailedHealthResponse | null;

  // Provider & Runtime Configuration
  providerStatus: ProviderStatusResponse | null;
  discoveredModels: DiscoveredModel[];
  discovering: boolean;
  discoveryStatus: string;
  discoveryError: string | null;

  // Active / Verified / Configured identities
  activeProvider: string;
  activeEndpoint: string;
  activeModel: string | null;
  configuredModel: string | null;
  providerReachable: boolean;
  providerHealthState: string;
  quantizationWarning: string | null;

  // Storage / Engine settings
  appSettings: AppSettingsResponse | null;
  savingSettings: boolean;
  settingsMessage: string | null;
  settingsError: string | null;

  // Diagnostics
  diagnosticsData: Record<string, unknown> | null;
  exportPath: string | null;
  exportingDiagnostics: boolean;

  // Benchmarks
  benchmarkResults: BenchmarkSuiteResponse | null;
  runningBenchmark: boolean;
  benchmarkError: string | null;

  setActiveTab: (tab: SystemTab) => void;
  pollHealth: () => Promise<void>;
  fetchProviderStatus: () => Promise<void>;
  probeProvider: (provider: string, endpoint: string, apiKey?: string) => Promise<void>;
  saveProvider: (provider: string, endpoint: string, model: string, apiKey?: string) => Promise<boolean>;
  fetchSettings: () => Promise<void>;
  saveStorageSettings: (req: CogneeSettingsRequest) => Promise<boolean>;
  fetchDiagnostics: () => Promise<void>;
  exportDiagnosticsBundle: () => Promise<string | null>;
  executeBenchmark: () => Promise<void>;
}

export const useSystemStore = create<SystemStore>((set, get) => ({
  activeTab: "providers",
  backendOnline: false,

  health: null,
  status: null,
  detailedHealth: null,

  providerStatus: null,
  discoveredModels: [],
  discovering: false,
  discoveryStatus: "idle",
  discoveryError: null,

  activeProvider: "ollama",
  activeEndpoint: "http://localhost:11434/v1",
  activeModel: null,
  configuredModel: null,
  providerReachable: false,
  providerHealthState: "unavailable",
  quantizationWarning: null,

  appSettings: null,
  savingSettings: false,
  settingsMessage: null,
  settingsError: null,

  diagnosticsData: null,
  exportPath: null,
  exportingDiagnostics: false,

  benchmarkResults: null,
  runningBenchmark: false,
  benchmarkError: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  pollHealth: async () => {
    try {
      const [hRes, sRes] = await Promise.allSettled([
        getHealth(),
        getBackendStatus(),
      ]);

      const h = hRes.status === "fulfilled" ? hRes.value : null;
      const s = sRes.status === "fulfilled" ? sRes.value : null;
      const isOnline = Boolean(h || s);

      const prov = h?.provider_identity || h?.provider || s?.provider_identity || s?.llm_provider || "ollama";
      const provReachable = Boolean(
        h?.provider_reachable ?? h?.ollama_reachable ?? s?.provider_reachable ?? s?.ollama_reachable ?? false
      );
      const actModel = h?.active_model ?? s?.active_model ?? null;
      const cfgModel = h?.configured_model ?? s?.configured_model ?? null;
      const provHealth = h?.provider_health_state || s?.provider_health_state || (provReachable ? "healthy" : "unavailable");

      set({
        backendOnline: isOnline,
        health: h,
        status: s,
        activeProvider: prov,
        providerReachable: provReachable,
        providerHealthState: provHealth,
        activeModel: actModel,
        configuredModel: cfgModel,
        quantizationWarning: null,
      });
    } catch {
      set({
        backendOnline: false,
        health: null,
        status: null,
        providerReachable: false,
        providerHealthState: "unavailable",
      });
    }
  },

  fetchProviderStatus: async () => {
    try {
      const res = await getProviderStatus();
      set({
        providerStatus: res,
        activeProvider: res.provider,
        activeEndpoint: res.base_url,
        activeModel: res.active_model || null,
        providerReachable: res.is_reachable,
        providerHealthState: res.health_state,
        discoveredModels: res.loaded_models || [],
        quantizationWarning: res.quantization_warning || null,
      });
    } catch {
      // Ignored non-critical failure
    }
  },

  probeProvider: async (provider, endpoint, apiKey) => {
    set({ discovering: true, discoveryError: null, discoveryStatus: "probing" });
    try {
      const res = await discoverProvider({
        provider,
        base_url: endpoint,
        api_key: apiKey || "local",
      });

      set({
        discovering: false,
        discoveredModels: res.models || [],
        discoveryStatus: res.status,
        providerReachable: res.is_reachable,
        discoveryError: res.error_details || null,
      });
    } catch (err) {
      set({
        discovering: false,
        discoveryStatus: "discovery_failed",
        discoveryError: err instanceof Error ? err.message : String(err),
      });
    }
  },

  saveProvider: async (provider, endpoint, model, apiKey) => {
    set({ savingSettings: true, settingsError: null, settingsMessage: null });
    try {
      const res = await updateProvider({
        provider,
        base_url: endpoint,
        model,
        api_key: apiKey || "local",
      });

      set({
        savingSettings: false,
        activeProvider: res.provider,
        activeEndpoint: res.base_url,
        activeModel: res.model,
        providerReachable: res.reachable,
        providerHealthState: res.health_state || "healthy",
        quantizationWarning: res.quantization_warning || null,
        settingsMessage: `Active provider updated: ${res.provider} (${res.model})`,
      });

      get().pollHealth();
      return true;
    } catch (err) {
      set({
        savingSettings: false,
        settingsError: err instanceof Error ? err.message : "Failed to update provider",
      });
      return false;
    }
  },

  fetchSettings: async () => {
    try {
      const [app, detailed] = await Promise.all([
        getAppSettings(),
        getDetailedHealth().catch(() => null),
      ]);
      set({ appSettings: app, detailedHealth: detailed });
    } catch (err) {
      set({ settingsError: err instanceof Error ? err.message : "Failed to load settings" });
    }
  },

  saveStorageSettings: async (req) => {
    set({ savingSettings: true, settingsError: null });
    try {
      const res = await updateCogneeSettings(req);
      set({
        appSettings: res,
        savingSettings: false,
        settingsMessage: "Storage configuration updated.",
      });
      return true;
    } catch (err) {
      set({
        savingSettings: false,
        settingsError: err instanceof Error ? err.message : "Failed to update storage settings",
      });
      return false;
    }
  },

  fetchDiagnostics: async () => {
    try {
      const diag = await getDiagnostics();
      set({ diagnosticsData: diag });
    } catch {
      // Ignored
    }
  },

  exportDiagnosticsBundle: async () => {
    set({ exportingDiagnostics: true });
    try {
      const res = await exportDiagnostics();
      set({ exportPath: res.export_path, exportingDiagnostics: false });
      return res.export_path;
    } catch (err) {
      set({ exportingDiagnostics: false, settingsError: err instanceof Error ? err.message : "Export failed" });
      return null;
    }
  },

  executeBenchmark: async () => {
    set({ runningBenchmark: true, benchmarkError: null });
    try {
      const res = await runBenchmark();
      set({ benchmarkResults: res, runningBenchmark: false });
    } catch (err) {
      set({
        runningBenchmark: false,
        benchmarkError: err instanceof Error ? err.message : "Benchmark failed",
      });
    }
  },
}));
