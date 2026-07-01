import { create } from "zustand";
import type { Dataset } from "@/types";
import { mockDatasets } from "@/data/mock";

interface MemoryStore {
  datasets: Dataset[];
  selectedDatasetId: string | null;
  filterType: "all" | "vectors" | "graphs" | "document";
  viewMode: "list" | "grid";
  sortBy: "date" | "name" | "size";
  setFilter: (f: "all" | "vectors" | "graphs" | "document") => void;
  setViewMode: (m: "list" | "grid") => void;
  setSort: (s: "date" | "name" | "size") => void;
  selectDataset: (id: string | null) => void;
  removeDataset: (id: string) => void;
}

export const useMemoryStore = create<MemoryStore>((set) => ({
  datasets: mockDatasets,
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
}));
