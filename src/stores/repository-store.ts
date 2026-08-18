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
import { queryCache } from "@/lib/query-cache";

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

  fetchRepositories: (forceRefresh?: boolean) => Promise<void>;
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

  fetchRepositories: async (forceRefresh = false) => {
    // Only show loading spinner if we don't already have repositories cached
    if (get().repositories.length === 0) {
      set({ loading: true });
    }
    try {
      const response = await queryCache.fetchWithCache(
        "repositories",
        listRepositories,
        {
          staleTimeMs: 15_000,
          forceRefresh,
          onBackgroundRevalidate: (fresh) => {
            set({ repositories: fresh.repositories });
          },
        }
      );
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
        scanning: false,
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

      // Optimistically initialize progress so modal immediately shows active indexing
      set({
        progress: {
          status: "indexing",
          stage: "Scanning & discovering repository files...",
          processed_files: 0,
          total_files: repo.file_count || 1,
          elapsed_ms: 0,
          languages: repo.languages || [],
          frameworks: repo.frameworks || [],
          file_count: repo.file_count || 0,
          size_bytes: repo.size_bytes || 0,
          error: null,
        },
      });

      // Start polling immediately so the modal displays real-time progress transitions
      get().pollProgress(repoId);

      const res = await indexRepository({
        repository_path: repo.local_path,
        dataset_name: repo.name,
        force_reindex: true,
      });

      if (!res.success) {
        throw new Error(res.summary || "Indexing failed");
      }

      // Explicitly mark progress as indexed and stop polling
      const { pollInterval } = get();
      if (pollInterval) clearInterval(pollInterval);

      set({
        indexing: false,
        pollInterval: null,
        progress: {
          status: "indexed",
          stage: "Indexing Completed",
          processed_files: res.processed_files || repo.file_count || 1,
          total_files: res.total_files || repo.file_count || 1,
          elapsed_ms: 0,
          languages: repo.languages || [],
          frameworks: repo.frameworks || [],
          file_count: res.total_files || repo.file_count || 0,
          size_bytes: repo.size_bytes || 0,
          error: null,
        },
      });

      await get().fetchRepositories();
    } catch (err) {
      const errMsg =
        typeof err === "string"
          ? err
          : err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "message" in err
          ? String((err as any).message)
          : "Failed to index repository";

      const { pollInterval } = get();
      if (pollInterval) clearInterval(pollInterval);

      set({
        indexing: false,
        pollInterval: null,
        error: errMsg,
        progress: {
          status: "error",
          stage: "Indexing Failed",
          processed_files: 0,
          total_files: 1,
          elapsed_ms: 0,
          languages: [],
          frameworks: [],
          error: errMsg,
          file_count: 0,
          size_bytes: 0,
        },
      });
    }
  },

  pollProgress: (repoId: string) => {
    const existing = get().pollInterval;
    if (existing) clearInterval(existing);

    // Initial poll immediately
    getRepositoryProgress(repoId)
      .then((progress) => {
        set({ progress });
        if (progress.status === "indexed" || progress.status === "error") {
          set({ indexing: false });
        }
      })
      .catch(() => {});

    let pollCount = 0;
    const interval = setInterval(async () => {
      pollCount++;
      try {
        const progress = await getRepositoryProgress(repoId);
        set({ progress });
        if (progress.status === "indexed" || progress.status === "error" || pollCount > 120) {
          clearInterval(interval);
          set({ pollInterval: null, indexing: false });
          await get().fetchRepositories();
        }
      } catch {
        if (pollCount > 60) {
          clearInterval(interval);
          set({ pollInterval: null, indexing: false });
        }
      }
    }, 400);

    set({ pollInterval: interval });
  },

  clearPoll: () => {
    const { pollInterval } = get();
    if (pollInterval) clearInterval(pollInterval);
    set({ pollInterval: null });
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
