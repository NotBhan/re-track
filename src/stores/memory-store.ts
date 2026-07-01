import { create } from "zustand";
import {
  listDatasets,
  getMemoryStats,
  type DatasetInfo,
  type MemoryStatsResponse,
} from "@/lib/api";

interface MemoryStore {
  datasets: DatasetInfo[];
  stats: MemoryStatsResponse | null;
  loading: boolean;
  selectedDatasetId: string | null;
  filterType: "all" | "vectors" | "graphs" | "document";
  viewMode: "list" | "grid";
  sortBy: "date" | "name" | "size";
  setFilter: (f: "all" | "vectors" | "graphs" | "document") => void;
  setViewMode: (m: "list" | "grid") => void;
  setSort: (s: "date" | "name" | "size") => void;
  selectDataset: (id: string | null) => void;
  removeDataset: (id: string) => void;
  fetchDatasets: () => Promise<void>;
  fetchStats: () => Promise<void>;
}

export const useMemoryStore = create<MemoryStore>((set) => ({
  datasets: [],
  stats: null,
  loading: false,
  selectedDatasetId: null,
  filterType: "all",
  viewMode: "list",
  sortBy: "date",

  setFilter: (f) => set({ filterType: f }),
  setViewMode: (m) => set({ viewMode: m }),
  setSort: (s) => set({ sortBy: s }),
  selectDataset: (id) => set({ selectedDatasetId: id }),
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
}));
