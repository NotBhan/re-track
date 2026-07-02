import { create } from "zustand";
import type { Repository, ScanResult } from "@/types/repository";
import type { IndexingProgress } from "@/lib/api";
import {
  listRepositories,
  createRepository,
  scanRepository,
  indexRepository,
  deleteRepository,
  getRepositoryProgress,
} from "@/lib/api";

interface RepositoryStore {
  repositories: Repository[];
  selectedId: string | null;
  selected: Repository | undefined;
  searchQuery: string;

  loading: boolean;
  indexing: boolean;
  scanning: boolean;
  error: string | null;

  lastScan: ScanResult | null;

  progress: IndexingProgress | null;
  pollInterval: ReturnType<typeof setInterval> | null;

  fetchRepositories: () => Promise<void>;
  createAndScan: (req: {
    source_type: string;
    source_url?: string;
    local_path?: string;
    name?: string;
  }) => Promise<Repository>;
  indexRepo: (repoId: string) => Promise<void>;
  pollProgress: (repoId: string) => void;
  clearPoll: () => void;
  removeRepo: (repoId: string) => Promise<void>;
  select: (id: string | null) => void;
  setSearchQuery: (q: string) => void;
  clearError: () => void;
  clearScan: () => void;
}

export const useRepositoryStore = create<RepositoryStore>((set, get) => ({
  repositories: [],
  selectedId: null,
  selected: undefined,
  searchQuery: "",

  loading: false,
  indexing: false,
  scanning: false,
  error: null,

  lastScan: null,

  progress: null,
  pollInterval: null,

  fetchRepositories: async () => {
    set({ loading: true });
    try {
      const response = await listRepositories();
      set({ repositories: response.repositories, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  createAndScan: async (req) => {
    set({ loading: true, error: null });
    try {
      const repository = await createRepository(req);
      set({ loading: false });

      set({ scanning: true });
      try {
        const scanResult = await scanRepository(repository.id);
        set({ lastScan: scanResult, scanning: false });
      } catch (scanErr) {
        set({
          scanning: false,
          error: scanErr instanceof Error ? scanErr.message : "Scan failed",
        });
      }

      await get().fetchRepositories();
      return repository;
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to create repository",
      });
      throw err;
    }
  },

  indexRepo: async (repoId: string) => {
    set({ indexing: true, error: null });
    try {
      const repo = get().repositories.find((r) => r.id === repoId);
      if (!repo) throw new Error("Repository not found");

      await indexRepository({
        repository_path: repo.local_path,
        dataset_name: repo.name,
      });

      get().pollProgress(repoId);
    } catch (err) {
      set({
        indexing: false,
        error: err instanceof Error ? err.message : "Failed to index repository",
      });
    }
  },

  pollProgress: (repoId: string) => {
    const existing = get().pollInterval;
    if (existing) clearInterval(existing);

    const interval = setInterval(async () => {
      try {
        const progress = await getRepositoryProgress(repoId);
        set({ progress });
        if (progress.status === "indexed" || progress.status === "error") {
          clearInterval(interval);
          set({ pollInterval: null, indexing: false });
          await get().fetchRepositories();
        }
      } catch {
        // Ignore polling errors
      }
    }, 2000);
    set({ pollInterval: interval });
  },

  clearPoll: () => {
    const { pollInterval } = get();
    if (pollInterval) clearInterval(pollInterval);
    set({ pollInterval: null, progress: null });
  },

  removeRepo: async (repoId: string) => {
    try {
      await deleteRepository(repoId);
      set((state) => ({
        repositories: state.repositories.filter((r) => r.id !== repoId),
        selectedId: state.selectedId === repoId ? null : state.selectedId,
        selected: state.selectedId === repoId ? undefined : state.selected,
      }));
      await get().fetchRepositories();
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to delete repository",
      });
    }
  },

  select: (id) =>
    set({
      selectedId: id,
      selected: get().repositories.find((r) => r.id === id),
    }),

  setSearchQuery: (q) => set({ searchQuery: q }),

  clearError: () => set({ error: null }),

  clearScan: () => set({ lastScan: null }),
}));
