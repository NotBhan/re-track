import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  getAppSettings,
  updateCogneeSettings,
  type CogneeSettingsRequest,
} from "@/lib/api";

export type SettingsTab = "backend" | "diagnostics" | "cognee" | "ollama" | "storage" | "theme" | "about";

interface SettingsStore {
  activeTab: SettingsTab;
  setActiveTab: (tab: SettingsTab) => void;

  // Cognee & Storage configuration state
  vectorDb: string;
  graphDb: string;
  relationalDb: string;
  enableKgExtraction: boolean;
  autoLinkEntities: boolean;
  caching: boolean;
  dataRoot: string;
  systemRoot: string;

  // Status flags
  loading: boolean;
  saving: boolean;
  saveSuccess: boolean | null;
  statusMessage: string | null;
  error: string | null;

  // Actions
  setVectorDb: (db: string) => void;
  setGraphDb: (db: string) => void;
  setEnableKgExtraction: (enabled: boolean) => void;
  setAutoLinkEntities: (enabled: boolean) => void;
  setCaching: (caching: boolean) => void;
  fetchSettings: () => Promise<void>;
  saveCogneeSettings: () => Promise<boolean>;
  clearStatus: () => void;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set, get) => ({
      activeTab: "backend",
      setActiveTab: (tab) => set({ activeTab: tab }),

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
          const res = await getAppSettings();
          set({
            vectorDb: res.vector_db,
            graphDb: res.graph_db,
            relationalDb: res.relational_db,
            enableKgExtraction: res.enable_kg_extraction,
            autoLinkEntities: res.auto_link_entities,
            caching: res.caching,
            dataRoot: res.data_root,
            systemRoot: res.system_root,
            loading: false,
          });
        } catch (err) {
          console.error("Failed to fetch settings from backend:", err);
          set({ loading: false, error: err instanceof Error ? err.message : String(err) });
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
    }),
    {
      name: "retrack-settings-storage",
      partialize: (state) => ({
        activeTab: state.activeTab,
        vectorDb: state.vectorDb,
        graphDb: state.graphDb,
        enableKgExtraction: state.enableKgExtraction,
        autoLinkEntities: state.autoLinkEntities,
        caching: state.caching,
      }),
    }
  )
);
