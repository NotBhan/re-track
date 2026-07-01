import { create } from "zustand";
import type { Repository } from "@/types";
import { mockRepositories } from "@/data/mock";

interface RepositoryStore {
  repositories: Repository[];
  selectedId: string | null;
  selected: Repository | undefined;
  searchQuery: string;
  select: (id: string | null) => void;
  setSearchQuery: (q: string) => void;
  remove: (id: string) => void;
}

export const useRepositoryStore = create<RepositoryStore>((set, get) => ({
  repositories: mockRepositories,
  selectedId: null,
  selected: undefined,
  searchQuery: "",

  select: (id) =>
    set({
      selectedId: id,
      selected: get().repositories.find((r) => r.id === id),
    }),

  setSearchQuery: (q) => set({ searchQuery: q }),

  remove: (id) =>
    set((state) => ({
      repositories: state.repositories.filter((r) => r.id !== id),
      selectedId: state.selectedId === id ? null : state.selectedId,
      selected: state.selectedId === id ? undefined : state.selected,
    })),
}));
