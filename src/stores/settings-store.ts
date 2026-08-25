import { create } from "zustand";
import { useHealthStore } from "@/stores/health-store";
import {
  getAppSettings,
  getProviderStatus,
  discoverProvider,
  updateProvider,
  updateCogneeSettings,
  type CogneeSettingsRequest,
  type DiscoveredModel,
  type ProviderDiscoveryRequest,
  type ProviderDiscoveryResponse,
} from "@/lib/api";

export type SettingsTab = "backend" | "diagnostics" | "cognee" | "ollama" | "storage" | "theme" | "about";

interface SettingsStore {
  activeTab: SettingsTab;
  setActiveTab: (tab: SettingsTab) => void;

  // Inference Provider configuration state
  provider: "ollama" | "lmstudio" | "openai_compatible" | string;
  endpoint: string;
  model: string;
  apiKey: string;
  apiKeyConfigured: boolean;
  apiKeyMasked: string;
  providerReachable: boolean;
  providerHealthState: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  quantizationWarning: string | null;
  availableModels: DiscoveredModel[];

  // Model discovery state
  discovering: boolean;
  discoveryStatus: "available" | "reachable_but_empty" | "unreachable" | "discovery_failed" | "not_configured" | "idle" | string;
  discoveryMessage: string;
  discoveryError: string | null;

  // Cognee & Storage configuration state
  vectorDb: string;
  graphDb: string;
  relationalDb: string;
  enableKgExtraction: boolean;
  autoLinkEntities: boolean;
  caching: boolean;
  dataRoot: string;
  systemRoot: string;

  // General Status flags
  loading: boolean;
  saving: boolean;
  saveSuccess: boolean | null;
  statusMessage: string | null;
  error: string | null;

  // Actions
  setProvider: (p: string) => void;
  setEndpoint: (url: string) => void;
  setModel: (m: string) => void;
  setApiKey: (key: string) => void;
  setVectorDb: (db: string) => void;
  setGraphDb: (db: string) => void;
  setEnableKgExtraction: (enabled: boolean) => void;
  setAutoLinkEntities: (enabled: boolean) => void;
  setCaching: (caching: boolean) => void;
  fetchSettings: () => Promise<void>;
  discoverModels: (candidateProvider?: string, candidateUrl?: string, candidateKey?: string) => Promise<ProviderDiscoveryResponse | null>;
  saveProviderSettings: (provider: string, endpoint: string, model: string, apiKey?: string) => Promise<boolean>;
  saveCogneeSettings: () => Promise<boolean>;
  clearStatus: () => void;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  activeTab: "backend",
  setActiveTab: (tab) => set({ activeTab: tab }),

  provider: "ollama",
  endpoint: "http://localhost:11434/v1",
  model: "phi4-mini",
  apiKey: "",
  apiKeyConfigured: false,
  apiKeyMasked: "local",
  providerReachable: false,
  providerHealthState: "not_configured",
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
  autoLinkEntities: false,
  caching: false,
  dataRoot: "",
  systemRoot: "",

  loading: false,
  saving: false,
  saveSuccess: null,
  statusMessage: null,
  error: null,

  setProvider: (p) => set({ provider: p, saveSuccess: null, statusMessage: null }),
  setEndpoint: (url) => set({ endpoint: url, saveSuccess: null, statusMessage: null }),
  setModel: (m) => set({ model: m, saveSuccess: null, statusMessage: null }),
  setApiKey: (key) => set({ apiKey: key, saveSuccess: null, statusMessage: null }),

  setVectorDb: (db) => set({ vectorDb: db, saveSuccess: null, statusMessage: null }),
  setGraphDb: (db) => set({ graphDb: db, saveSuccess: null, statusMessage: null }),
  setEnableKgExtraction: (enabled) =>
    set({ enableKgExtraction: enabled, saveSuccess: null, statusMessage: null }),
  setAutoLinkEntities: (enabled) =>
    set({ autoLinkEntities: enabled, saveSuccess: null, statusMessage: null }),
  setCaching: (caching) => set({ caching: caching, saveSuccess: null, statusMessage: null }),

  clearStatus: () => set({ saveSuccess: null, statusMessage: null, error: null }),

  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const [appRes, provRes] = await Promise.all([
        getAppSettings(),
        getProviderStatus().catch(() => null),
      ]);

      const stateUpdate: Partial<SettingsStore> = {
        vectorDb: appRes.vector_db,
        graphDb: appRes.graph_db,
        relationalDb: appRes.relational_db,
        enableKgExtraction: appRes.enable_kg_extraction,
        autoLinkEntities: appRes.auto_link_entities,
        caching: appRes.caching,
        dataRoot: appRes.data_root,
        systemRoot: appRes.system_root,
        provider: appRes.llm_provider || "ollama",
        endpoint: appRes.llm_endpoint || (appRes.llm_provider === "lmstudio" ? "http://localhost:1234/v1" : "http://localhost:11434/v1"),
        model: appRes.llm_model || "phi4-mini",
        apiKeyConfigured: Boolean(appRes.api_key_configured),
        apiKeyMasked: appRes.api_key_masked || "local",
        loading: false,
      };

      if (provRes) {
        stateUpdate.provider = provRes.provider;
        stateUpdate.endpoint = provRes.base_url;
        stateUpdate.model = provRes.active_model || stateUpdate.model;
        stateUpdate.providerReachable = provRes.is_reachable;
        stateUpdate.providerHealthState = provRes.health_state;
        stateUpdate.availableModels = provRes.loaded_models || [];
        stateUpdate.discoveryStatus = provRes.discovery_status || (provRes.is_reachable ? "available" : "unreachable");
        stateUpdate.quantizationWarning = provRes.quantization_warning || null;
        stateUpdate.apiKeyConfigured = provRes.api_key_configured;
        stateUpdate.apiKeyMasked = provRes.api_key_masked;
      }

      set(stateUpdate);
    } catch (err) {
      console.error("Failed to fetch settings from backend:", err);
      set({ loading: false, error: err instanceof Error ? err.message : String(err) });
    }
  },

  discoverModels: async (candidateProvider, candidateUrl, candidateKey) => {
    const state = get();
    const targetProvider = candidateProvider || state.provider;
    const targetUrl = candidateUrl || state.endpoint;
    const targetKey = candidateKey !== undefined ? candidateKey : (state.apiKey || "local");

    set({ discovering: true, discoveryError: null, discoveryMessage: "Probing endpoint for models..." });

    try {
      const payload: ProviderDiscoveryRequest = {
        provider: targetProvider,
        base_url: targetUrl,
        api_key: targetKey,
      };
      const res = await discoverProvider(payload);

      set({
        discovering: false,
        discoveryStatus: res.status,
        discoveryMessage: res.message,
        discoveryError: res.error_details || null,
        availableModels: res.models || [],
        providerReachable: res.is_reachable,
      });

      return res;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({
        discovering: false,
        discoveryStatus: "discovery_failed",
        discoveryMessage: `Discovery failed: ${msg}`,
        discoveryError: msg,
      });
      return null;
    }
  },

  saveProviderSettings: async (provider, endpoint, model, apiKey) => {
    set({ saving: true, saveSuccess: null, statusMessage: null, error: null });
    try {
      const res = await updateProvider({
        provider,
        base_url: endpoint,
        model,
        api_key: apiKey || "local",
      });

      set({
        provider: res.provider,
        endpoint: res.base_url,
        model: res.model,
        providerReachable: res.reachable,
        providerHealthState: res.health_state || (res.reachable ? "healthy" : "unavailable"),
        quantizationWarning: res.quantization_warning || null,
        apiKeyConfigured: Boolean(res.api_key_configured),
        apiKeyMasked: res.api_key_masked || "local",
        apiKey: "", // Never retain raw secret in active store state after save
        saving: false,
        saveSuccess: true,
        statusMessage: `Provider configured: ${res.provider} (${res.model})`,
      });

      // Synchronize global runtime engine state immediately across all UI surfaces
      useHealthStore.getState().pollHealth().catch((e) => console.error("pollHealth after save error:", e));

      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({
        saving: false,
        saveSuccess: false,
        error: msg,
        statusMessage: `Failed to update provider: ${msg}`,
      });
      return false;
    }
  },

  saveCogneeSettings: async () => {
    const state = get();
    set({ saving: true, saveSuccess: null, statusMessage: null, error: null });
    try {
      const payload: CogneeSettingsRequest = {
        vector_db: state.vectorDb,
        graph_db: state.graphDb,
        enable_kg_extraction: state.enableKgExtraction,
        auto_link_entities: state.autoLinkEntities,
        caching: state.caching,
      };
      const res = await updateCogneeSettings(payload);
      set({
        vectorDb: res.vector_db,
        graphDb: res.graph_db,
        relationalDb: res.relational_db,
        enableKgExtraction: res.enable_kg_extraction,
        autoLinkEntities: res.auto_link_entities,
        caching: res.caching,
        saving: false,
        saveSuccess: true,
        statusMessage: "Cognee settings saved & persisted to disk.",
      });
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("Failed to save Cognee settings:", err);
      set({
        saving: false,
        saveSuccess: false,
        error: msg,
        statusMessage: `Failed to save: ${msg}`,
      });
      return false;
    }
  },
}));

