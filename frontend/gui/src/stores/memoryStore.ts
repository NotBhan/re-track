import { create } from "zustand";
import type {
  DatasetInfo,
  MemoryStatsResponse,
  MemoryVectorsResponse,
  MemoryGraphResponse,
  MemoryDataItem,
} from "../types/api";
import {
  listDatasets,
  getMemoryStats,
  getMemoryVectors,
  getMemoryGraph,
  getDatasetItems,
  cognifyDataset,
} from "../lib/api";

export type MemoryViewTab = "documents" | "vectors" | "graph";

interface MemoryStore {
  datasets: DatasetInfo[];
  selectedDatasetId: string | null;
  datasetItems: MemoryDataItem[];

  stats: MemoryStatsResponse | null;
  vectors: MemoryVectorsResponse | null;
  graph: MemoryGraphResponse | null;

  activeTab: MemoryViewTab;
  loading: boolean;
  loadingItems: boolean;
  loadingGraph: boolean;
  loadingVectors: boolean;
  cognifying: boolean;
  error: string | null;

  setActiveTab: (tab: MemoryViewTab) => void;
  selectDataset: (id: string | null) => void;
  fetchDatasets: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchVectors: () => Promise<void>;
  fetchGraph: (datasetName?: string) => Promise<void>;
  fetchItems: (datasetId: string) => Promise<void>;
  cognify: (datasetName?: string) => Promise<boolean>;
  refreshAll: () => Promise<void>;
}

export const useMemoryEngineStore = create<MemoryStore>((set, get) => ({
  datasets: [],
  selectedDatasetId: null,
  datasetItems: [],

  stats: null,
  vectors: null,
  graph: null,

  activeTab: "documents",
  loading: false,
  loadingItems: false,
  loadingGraph: false,
  loadingVectors: false,
  cognifying: false,
  error: null,

  setActiveTab: (tab) => {
    set({ activeTab: tab });
    const { selectedDatasetId, datasets } = get();
    const activeDs = datasets.find((d) => d.id === selectedDatasetId);
    if (tab === "vectors") {
      get().fetchVectors();
    } else if (tab === "graph") {
      get().fetchGraph(activeDs?.name);
    }
  },

  selectDataset: (id) => {
    set({ selectedDatasetId: id });
    if (id) {
      const activeDs = get().datasets.find((d) => d.id === id);
      get().fetchItems(id);
      if (get().activeTab === "graph") {
        get().fetchGraph(activeDs?.name);
      }
    } else {
      set({ datasetItems: [] });
      if (get().activeTab === "graph") {
        get().fetchGraph();
      }
    }
  },

  fetchDatasets: async () => {
    set({ loading: true });
    try {
      const res = await listDatasets();
      const list = res.datasets || [];
      const currentSelected = get().selectedDatasetId;
      const nextSelected = currentSelected && list.some((d) => d.id === currentSelected)
        ? currentSelected
        : list.length > 0
        ? list[0].id
        : null;

      set({
        datasets: list,
        selectedDatasetId: nextSelected,
        loading: false,
      });

      if (nextSelected) {
        get().fetchItems(nextSelected);
      }
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load datasets",
      });
    }
  },

  fetchStats: async () => {
    try {
      const res = await getMemoryStats();
      set({ stats: res });
    } catch {
      // Ignored non-critical background fetch
    }
  },

  fetchVectors: async () => {
    set({ loadingVectors: true });
    try {
      const res = await getMemoryVectors();
      set({ vectors: res, loadingVectors: false });
    } catch {
      set({ loadingVectors: false });
    }
  },

  fetchGraph: async (datasetName?: string) => {
    set({ loadingGraph: true });
    try {
      const res = await getMemoryGraph(datasetName);
      set({ graph: res, loadingGraph: false });
    } catch {
      set({ loadingGraph: false });
    }
  },

  fetchItems: async (datasetId: string) => {
    set({ loadingItems: true });
    try {
      const res = await getDatasetItems(datasetId);
      set({ datasetItems: res.items || [], loadingItems: false });
    } catch {
      set({ loadingItems: false, datasetItems: [] });
    }
  },

  cognify: async (datasetName?: string) => {
    const { selectedDatasetId, datasets } = get();
    const activeDs = datasets.find((d) => d.id === selectedDatasetId);
    const targetName = datasetName || activeDs?.name;

    set({ cognifying: true, error: null });
    try {
      const res = await cognifyDataset({ dataset_name: targetName });
      if (res.success) {
        await get().refreshAll();
        set({ cognifying: false });
        return true;
      } else {
        set({ cognifying: false, error: res.message || "Cognification failed" });
        return false;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Cognification failed";
      set({ cognifying: false, error: msg });
      return false;
    }
  },

  refreshAll: async () => {
    const { selectedDatasetId, datasets } = get();
    const activeDs = datasets.find((d) => d.id === selectedDatasetId);
    await Promise.all([
      get().fetchDatasets(),
      get().fetchStats(),
      get().fetchVectors(),
      get().fetchGraph(activeDs?.name),
    ]);
  },
}));
