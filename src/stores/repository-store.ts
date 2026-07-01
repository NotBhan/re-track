import { create } from "zustand";
import type { RepositorySummaryInfo } from "@/lib/api";
import {
  getRepositorySummaries,
  indexRepository,
  forgetDataset,
} from "@/lib/api";

interface RepositoryStore {
  repositories: RepositorySummaryInfo[];
  selectedId: string | null;
  selected: RepositorySummaryInfo | undefined;
  searchQuery: string;
  loading: boolean;
  select: (id: string | null) => void;
  setSearchQuery: (q: string) => void;
  fetchRepositories: () => Promise<void>;
  indexRepo: (path: string, name: string) => Promise<void>;
  removeRepo: (id: string) => Promise<void>;
}

export const useRepositoryStore = create<RepositoryStore>((set, get) => ({
  repositories: [],
  selectedId: null,
  selected: undefined,
  searchQuery: "",
  loading: false,

  select: (id) =>
    set({
      selectedId: id,
      selected: get().repositories.find((r) => r.id === id),
    }),

  setSearchQuery: (q) => set({ searchQuery: q }),

  fetchRepositories: async () => {
    set({ loading: true });
    try {
      const response = await getRepositorySummaries();
      if (response.success) {
        set({ repositories: response.repositories, loading: false });
      } else {
        set({ loading: false });
      }
    } catch {
      set({ loading: false });
    }
  },

  indexRepo: async (path: string, name: string) => {
    await indexRepository({ repository_path: path, dataset_name: name });
    await get().fetchRepositories();
  },

  removeRepo: async (id: string) => {
    await forgetDataset({ dataset: id });
    set((state) => ({
      repositories: state.repositories.filter((r) => r.id !== id),
      selectedId: state.selectedId === id ? null : state.selectedId,
      selected: state.selectedId === id ? undefined : state.selected,
    }));
    await get().fetchRepositories();
  },
}));
