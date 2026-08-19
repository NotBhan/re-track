import { create } from "zustand";
import {
  listDatasets,
  getMemoryStats,
  getMemoryGraph,
  getMemoryVectors,
  getDatasetItems,
  type DatasetInfo,
  type MemoryStatsResponse,
  type MemoryGraphResponse,
  type MemoryVectorsResponse,
  type MemoryDataItem,
} from "@/lib/api";

export type MemoryTabType = "datasets" | "vectors" | "graph";

interface MemoryStore {
  datasets: DatasetInfo[];
  stats: MemoryStatsResponse | null;
  vectors: MemoryVectorsResponse | null;
  graph: MemoryGraphResponse | null;
  selectedDatasetItems: MemoryDataItem[];
  activeTab: MemoryTabType;
  selectedDatasetId: string | null;
  selectedNodeId: string | null;
  searchQuery: string;
  sortBy: "date" | "name" | "size";
  loading: boolean;
  loadingGraph: boolean;
  loadingVectors: boolean;
  loadingItems: boolean;

  setActiveTab: (tab: MemoryTabType) => void;
  setSearchQuery: (query: string) => void;
  setSelectedNodeId: (nodeId: string | null) => void;
  setSort: (s: "date" | "name" | "size") => void;
  selectDataset: (id: string | null) => void;
  removeDataset: (id: string) => void;
  fetchDatasets: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchMemoryVectors: () => Promise<void>;
  fetchMemoryGraph: (dataset?: string) => Promise<void>;
  fetchDatasetItems: (datasetId: string) => Promise<void>;
}

export const useMemoryStore = create<MemoryStore>((set, get) => ({
  datasets: [],
  stats: null,
  vectors: null,
  graph: null,
  selectedDatasetItems: [],
  activeTab: "datasets",
  selectedDatasetId: null,
  selectedNodeId: null,
  searchQuery: "",
  sortBy: "date",
  loading: false,
  loadingGraph: false,
  loadingVectors: false,
  loadingItems: false,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setSelectedNodeId: (selectedNodeId) => set({ selectedNodeId }),
  setSort: (sortBy) => set({ sortBy }),
  selectDataset: (selectedDatasetId) => {
    set({ selectedDatasetId });
    if (selectedDatasetId) {
      get().fetchDatasetItems(selectedDatasetId);
    }
  },
  removeDataset: (id) =>
    set((state) => ({
      datasets: state.datasets.filter((d) => d.id !== id),
      selectedDatasetId:
        state.selectedDatasetId === id ? null : state.selectedDatasetId,
    })),

  fetchDatasets: async () => {
    set({ loading: true });
    try {
      const response = await listDatasets();
      if (response.success) {
        set({ datasets: response.datasets });
      }
    } catch (error) {
      console.error("Failed to fetch datasets:", error);
    } finally {
      set({ loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const response = await getMemoryStats();
      if (response.success) {
        set({ stats: response });
      }
    } catch (error) {
      console.error("Failed to fetch memory stats:", error);
    }
  },

  fetchMemoryVectors: async () => {
    set({ loadingVectors: true });
    try {
      const response = await getMemoryVectors();
      if (response.success) {
        set({ vectors: response });
      }
    } catch (error) {
      console.error("Failed to fetch memory vectors:", error);
    } finally {
      set({ loadingVectors: false });
    }
  },

  fetchMemoryGraph: async (dataset?: string) => {
    set({ loadingGraph: true });
    try {
      const response = await getMemoryGraph(dataset);
      if (response.success) {
        set({ graph: response });
      }
    } catch (error) {
      console.error("Failed to fetch memory graph:", error);
    } finally {
      set({ loadingGraph: false });
    }
  },

  fetchDatasetItems: async (datasetId: string) => {
    set({ loadingItems: true });
    try {
      const response = await getDatasetItems(datasetId);
      if (response.success) {
        set({ selectedDatasetItems: response.items });
      }
    } catch (error) {
      console.error("Failed to fetch dataset items:", error);
    } finally {
      set({ loadingItems: false });
    }
  },
}));
