import { create } from "zustand";
import type { Repository, ScanResult, IndexingProgress } from "../types/api";
import {
  listRepositories,
  createRepository,
  scanRepository,
  indexRepository,
  deleteRepository,
  getRepositoryProgress,
} from "../lib/api";

interface RepositoryStore {
  repositories: Repository[];
  selectedId: string | null;
  selectedRepo: Repository | null;
  searchQuery: string;

  loading: boolean;
  scanning: boolean;
  indexing: boolean;
  error: string | null;

  lastScan: ScanResult | null;
  progress: IndexingProgress | null;
  pollTimer: ReturnType<typeof setInterval> | null;

  fetchRepositories: () => Promise<void>;
  selectRepository: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  createAndScan: (req: {
    source_type: string;
    source_url?: string;
    local_path?: string;
    name?: string;
  }) => Promise<Repository>;
  scanRepo: (repoId: string) => Promise<ScanResult>;
  indexRepo: (repoId: string) => Promise<void>;
  pollProgress: (repoId: string) => void;
  stopPolling: () => void;
  deleteRepo: (repoId: string) => Promise<void>;
  clearError: () => void;
  clearScan: () => void;
}

export const useRepositoryStore = create<RepositoryStore>((set, get) => ({
  repositories: [],
  selectedId: null,
  selectedRepo: null,
  searchQuery: "",

  loading: false,
  scanning: false,
  indexing: false,
  error: null,

  lastScan: null,
  progress: null,
  pollTimer: null,

  fetchRepositories: async () => {
    if (get().repositories.length === 0) {
      set({ loading: true });
    }
    try {
      const res = await listRepositories();
      const repos = Array.isArray(res?.repositories) ? res.repositories : [];
      const currentSelectedId = get().selectedId;
      const resolvedSelected = currentSelectedId
        ? repos.find((r) => r.id === currentSelectedId) || null
        : repos.length > 0
        ? repos[0]
        : null;

      set({
        repositories: repos,
        selectedId: resolvedSelected ? resolvedSelected.id : null,
        selectedRepo: resolvedSelected,
        loading: false,
        error: null,
      });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },

  selectRepository: (id: string | null) => {
    const repos = get().repositories;
    const selected = id ? repos.find((r) => r.id === id) || null : null;
    set({ selectedId: id, selectedRepo: selected });
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
  },

  createAndScan: async (req) => {
    set({ loading: true, error: null });
    try {
      const repo = await createRepository(req);
      set({ loading: false, scanning: true });

      try {
        const scan = await scanRepository(repo.id);
        set({ lastScan: scan, scanning: false });
      } catch (scanErr) {
        set({
          scanning: false,
          error: scanErr instanceof Error ? scanErr.message : "Scan failed",
        });
      }

      await get().fetchRepositories();
      get().selectRepository(repo.id);
      return repo;
    } catch (err) {
      set({
        loading: false,
        scanning: false,
        error: err instanceof Error ? err.message : "Failed to create repository",
      });
      throw err;
    }
  },

  scanRepo: async (repoId: string) => {
    set({ scanning: true, error: null });
    try {
      const scan = await scanRepository(repoId);
      set({ lastScan: scan, scanning: false });
      await get().fetchRepositories();
      return scan;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Scan failed";
      set({ scanning: false, error: msg });
      throw err;
    }
  },

  indexRepo: async (repoId: string) => {
    set({ indexing: true, error: null });
    const repo = get().repositories.find((r) => r.id === repoId);
    if (!repo) {
      set({ indexing: false, error: "Repository not found" });
      return;
    }

    set({
      progress: {
        status: "indexing",
        stage: "Discovering repository source files...",
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

    get().pollProgress(repoId);

    try {
      const res = await indexRepository({
        repository_path: repo.local_path,
        dataset_name: repo.name,
        force_reindex: true,
      });

      get().stopPolling();

      if (!res.success) {
        throw new Error(res.summary || "Indexing failed");
      }

      set({
        indexing: false,
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
      get().stopPolling();
      const msg = err instanceof Error ? err.message : "Failed to index repository";
      set({
        indexing: false,
        error: msg,
        progress: {
          status: "error",
          stage: "Indexing Failed",
          processed_files: 0,
          total_files: 1,
          elapsed_ms: 0,
          languages: [],
          frameworks: [],
          file_count: 0,
          size_bytes: 0,
          error: msg,
        },
      });
    }
  },

  pollProgress: (repoId: string) => {
    get().stopPolling();

    getRepositoryProgress(repoId)
      .then((p) => {
        set({ progress: p });
        if (p.status === "indexed" || p.status === "error") {
          set({ indexing: false });
        }
      })
      .catch(() => {});

    let count = 0;
    const timer = setInterval(async () => {
      count++;
      try {
        const p = await getRepositoryProgress(repoId);
        set({ progress: p });
        if (p.status === "indexed" || p.status === "error" || count > 150) {
          get().stopPolling();
          set({ indexing: false });
          await get().fetchRepositories();
        }
      } catch {
        if (count > 60) {
          get().stopPolling();
          set({ indexing: false });
        }
      }
    }, 450);

    set({ pollTimer: timer });
  },

  stopPolling: () => {
    const timer = get().pollTimer;
    if (timer) {
      clearInterval(timer);
      set({ pollTimer: null });
    }
  },

  deleteRepo: async (repoId: string) => {
    set({ loading: true, error: null });
    try {
      await deleteRepository(repoId);
      const remaining = get().repositories.filter((r) => r.id !== repoId);
      set({
        repositories: remaining,
        selectedId: remaining.length > 0 ? remaining[0].id : null,
        selectedRepo: remaining.length > 0 ? remaining[0] : null,
        loading: false,
      });
      await get().fetchRepositories();
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to delete repository",
      });
      throw err;
    }
  },

  clearError: () => set({ error: null }),
  clearScan: () => set({ lastScan: null }),
}));
