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

const ACTIVE_REPOSITORY_KEY = "retrack:active-repository";
const BOOTSTRAP_RETRY_MS = 500;
const BOOTSTRAP_MAX_ATTEMPTS = 120;
const PROGRESS_POLL_MS = 600;

function readPersistedActiveRepoId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(ACTIVE_REPOSITORY_KEY);
  } catch {
    return null;
  }
}

function persistActiveRepoId(repoId: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (repoId) {
      localStorage.setItem(ACTIVE_REPOSITORY_KEY, repoId);
    } else {
      localStorage.removeItem(ACTIVE_REPOSITORY_KEY);
    }
  } catch {
    // ignore
  }
}

interface RepositoryStore {
  repositories: Repository[];
  selectedId: string | null;
  selectedRepo: Repository | null;
  searchQuery: string;

  hydrated: boolean;
  loading: boolean;
  scanning: boolean;
  indexing: boolean;
  indexingRepoId: string | null;
  error: string | null;

  addRepositoryOpen: boolean;

  lastScan: ScanResult | null;
  progress: IndexingProgress | null;
  pollTimer: ReturnType<typeof setInterval> | null;
  bootstrapTimer: ReturnType<typeof setTimeout> | null;
  indexingStartedAt: number | null;

  fetchRepositories: () => Promise<boolean>;
  bootstrapRepositories: () => void;
  stopBootstrap: () => void;
  openAddRepository: () => void;
  closeAddRepository: () => void;
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
  dismissProgress: () => void;
}

export const useRepositoryStore = create<RepositoryStore>((set, get) => {
  let fetchInFlight: Promise<boolean> | null = null;

  return {
    repositories: [],
    selectedId: null,
    selectedRepo: null,
    searchQuery: "",

    hydrated: false,
    loading: false,
    scanning: false,
    indexing: false,
    indexingRepoId: null,
    error: null,

    addRepositoryOpen: false,

    lastScan: null,
    progress: null,
    pollTimer: null,
    bootstrapTimer: null,
    indexingStartedAt: null,

    fetchRepositories: async () => {
      if (fetchInFlight) return fetchInFlight;

      if (get().repositories.length === 0) {
        set({ loading: true });
      }

      fetchInFlight = (async () => {
        try {
          const res = await listRepositories();
          const repos = Array.isArray(res?.repositories) ? res.repositories : [];
          const currentSelectedId = get().selectedId;
          const persistedId = readPersistedActiveRepoId();
          const resolvedSelected =
            repos.find((r) => r.id === currentSelectedId) ||
            repos.find((r) => r.id === persistedId) ||
            repos[0] ||
            null;

          set({
            repositories: repos,
            selectedId: resolvedSelected ? resolvedSelected.id : null,
            selectedRepo: resolvedSelected,
            loading: false,
            hydrated: true,
            error: null,
          });
          persistActiveRepoId(resolvedSelected ? resolvedSelected.id : null);
          return true;
        } catch (err) {
          set({
            loading: false,
            error: err instanceof Error ? err.message : String(err),
          });
          return false;
        } finally {
          fetchInFlight = null;
        }
      })();

      return fetchInFlight;
    },

    bootstrapRepositories: () => {
      get().stopBootstrap();
      let attempts = 0;

      const attempt = async () => {
        const ok = await get().fetchRepositories();
        attempts += 1;
        if (ok || attempts >= BOOTSTRAP_MAX_ATTEMPTS) {
          set({ bootstrapTimer: null });
          return;
        }
        const timer = setTimeout(() => {
          void attempt();
        }, BOOTSTRAP_RETRY_MS);
        set({ bootstrapTimer: timer });
      };

      void attempt();
    },

    stopBootstrap: () => {
      const timer = get().bootstrapTimer;
      if (timer) {
        clearTimeout(timer);
        set({ bootstrapTimer: null });
      }
    },

    openAddRepository: () => set({ addRepositoryOpen: true }),
    closeAddRepository: () => set({ addRepositoryOpen: false }),

    selectRepository: (id: string | null) => {
      const repos = get().repositories;
      const selected = id ? repos.find((r) => r.id === id) || null : null;
      set({ selectedId: id, selectedRepo: selected });
      persistActiveRepoId(selected ? selected.id : null);
    },

    setSearchQuery: (query) => {
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
      const { indexing, indexingRepoId, repositories } = get();
      if (indexing) {
        if (indexingRepoId !== repoId) {
          set({ error: "Another repository is already being indexed. Wait for it to finish." });
        }
        return;
      }

      const repo = repositories.find((r) => r.id === repoId);
      if (!repo) {
        set({ error: "Repository not found" });
        return;
      }

      set({
        indexing: true,
        indexingRepoId: repoId,
        indexingStartedAt: Date.now(),
        error: null,
        progress: {
          status: "indexing",
          stage: "Submitting index request…",
          stage_index: null,
          stage_total: null,
          processed_files: 0,
          total_files: repo.file_count || 0,
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
          indexingStartedAt: null,
          progress: {
            status: "indexed",
            stage: "Indexing completed",
            stage_index: null,
            stage_total: null,
            processed_files: res.processed_files || repo.file_count || 0,
            total_files: res.total_files || repo.file_count || 0,
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
          indexingStartedAt: null,
          error: msg,
          progress: {
            status: "error",
            stage: "Indexing failed",
            stage_index: null,
            stage_total: null,
            processed_files: 0,
            total_files: repo.file_count || 0,
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

      const mergeProgress = (
        prev: IndexingProgress | null,
        incoming: Partial<IndexingProgress>
      ): IndexingProgress => ({
        status: incoming.status ?? prev?.status ?? "indexing",
        stage: incoming.stage ?? prev?.stage ?? "Working…",
        stage_index: incoming.stage_index ?? prev?.stage_index ?? null,
        stage_total: incoming.stage_total ?? prev?.stage_total ?? null,
        // Prefer incoming totals when present; fall back to the value seeded by indexRepo
        total_files:
          incoming.total_files != null && incoming.total_files > 0
            ? incoming.total_files
            : prev?.total_files ?? 0,
        processed_files: incoming.processed_files ?? prev?.processed_files ?? 0,
        file_count: incoming.file_count ?? prev?.file_count ?? 0,
        size_bytes: incoming.size_bytes ?? prev?.size_bytes ?? 0,
        elapsed_ms: incoming.elapsed_ms ?? prev?.elapsed_ms ?? 0,
        languages: incoming.languages ?? prev?.languages ?? [],
        frameworks: incoming.frameworks ?? prev?.frameworks ?? [],
        error: incoming.error ?? prev?.error ?? null,
      });

      const timer = setInterval(async () => {
        try {
          const p = await getRepositoryProgress(repoId);
          set((s) => ({ progress: mergeProgress(s.progress, p) }));
        } catch {
          // The blocking index call owns failure reporting; ignore transient poll errors.
        }
      }, PROGRESS_POLL_MS);

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
      const previous = get().repositories;
      const previousSelectedId = get().selectedId;
      set({ loading: true, error: null });
      try {
        await deleteRepository(repoId);
        const remaining = previous.filter((r) => r.id !== repoId);
        const nextSelected =
          previousSelectedId === repoId
            ? remaining[0] || null
            : remaining.find((r) => r.id === previousSelectedId) || remaining[0] || null;

        set({
          repositories: remaining,
          selectedId: nextSelected ? nextSelected.id : null,
          selectedRepo: nextSelected,
          loading: false,
        });
        persistActiveRepoId(nextSelected ? nextSelected.id : null);
        await get().fetchRepositories();
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to delete repository";
        set({ loading: false, error: msg });
        throw err;
      }
    },

    clearError: () => set({ error: null }),
    clearScan: () => set({ lastScan: null }),
    dismissProgress: () => set({ progress: null }),
  };
});
