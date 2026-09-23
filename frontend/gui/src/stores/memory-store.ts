import { create } from "zustand";
import {
  listDatasets,
  getMemoryStats,
  getMemoryGraph,
  getMemoryVectors,
  getDatasetItems,
  cognifyDataset,
  listRepositories,
  indexRepository,
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
  cognifying: boolean;
  cognifyingDataset: string | null;
  cognifyError: string | null;
  reindexingDatasetId: string | null;
  reindexError: string | null;

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
  cognifyActiveDataset: (datasetName?: string) => Promise<boolean>;
  reindexDataset: (datasetName: string) => Promise<boolean>;
  refreshAll: () => Promise<void>;
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
  cognifying: false,
  cognifyingDataset: null,
  cognifyError: null,
  reindexingDatasetId: null,
  reindexError: null,

  setActiveTab: (tab) => {
    set({ activeTab: tab });
    const { selectedDatasetId, datasets } = get();
    const activeDs = datasets.find((d) => d.id === selectedDatasetId);
    if (tab === "vectors") {
      get().fetchMemoryVectors();
    } else if (tab === "graph") {
      get().fetchMemoryGraph(activeDs ? activeDs.name : undefined);
    }
  },

  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setSelectedNodeId: (selectedNodeId) => set({ selectedNodeId }),
  setSort: (sortBy) => set({ sortBy }),

  selectDataset: (selectedDatasetId) => {
    set({ selectedDatasetId });
    if (selectedDatasetId) {
      const activeDs = get().datasets.find((d) => d.id === selectedDatasetId);
      get().fetchDatasetItems(selectedDatasetId);
      get().fetchMemoryGraph(activeDs ? activeDs.name : selectedDatasetId);
    } else {
      set({ selectedDatasetItems: [] });
      get().fetchMemoryGraph();
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

  cognifyActiveDataset: async (datasetName?: string) => {
    const targetName = datasetName || (() => {
      const { selectedDatasetId, datasets } = get();
      const ds = datasets.find((d) => d.id === selectedDatasetId);
      return ds ? ds.name : undefined;
    })();

    set({ cognifying: true, cognifyingDataset: targetName || "all", cognifyError: null });
    try {
      const response = await cognifyDataset({ dataset_name: targetName });
      if (response.success) {
        await Promise.all([
          get().fetchDatasets(),
          get().fetchStats(),
          get().fetchMemoryVectors(),
          get().fetchMemoryGraph(targetName),
        ]);
        return true;
      } else {
        set({ cognifyError: response.message || "Extraction failed" });
        return false;
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Extraction failed";
      set({ cognifyError: msg });
      console.error("Failed to cognify dataset:", error);
      return false;
    } finally {
      set({ cognifying: false, cognifyingDataset: null });
    }
  },

  reindexDataset: async (datasetName: string) => {
    set({ reindexingDatasetId: datasetName, reindexError: null });
    try {
      const reposRes = await listRepositories();
      const repos = reposRes.repositories || [];
      const matchingRepo = repos.find(
        (r) => r.name === datasetName || r.id === datasetName || r.local_path === datasetName
      );

      if (!matchingRepo) {
        throw new Error(`No workspace repository linked to dataset "${datasetName}". Add or import it in Workspaces.`);
      }

      const res = await indexRepository({
        repository_path: matchingRepo.local_path,
        dataset_name: datasetName,
        force_reindex: true,
      });

      if (!res.success) {
        throw new Error(res.summary || "Indexing failed");
      }

      await get().refreshAll();
      return true;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Re-indexing failed";
      set({ reindexError: msg });
      console.error("Failed to reindex dataset:", error);
      return false;
    } finally {
      set({ reindexingDatasetId: null });
    }
  },

  refreshAll: async () => {
    const { selectedDatasetId, datasets } = get();
    const activeDs = datasets.find((d) => d.id === selectedDatasetId);
    await Promise.all([
      get().fetchDatasets(),
      get().fetchStats(),
      get().fetchMemoryVectors(),
      get().fetchMemoryGraph(activeDs ? activeDs.name : undefined),
      selectedDatasetId ? get().fetchDatasetItems(selectedDatasetId) : Promise.resolve(),
    ]);
  },
}));
