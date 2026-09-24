import { create } from "zustand";
import type {
  AgentContextResponse,
  SuggestedPrompt,
  SavedContextPackage,
  ContextPackageSaveRequest,
} from "../types/api";
import {
  getAgentContext,
  getSuggestedPrompts,
  listContextPackages,
  saveContextPackage,
  deleteContextPackage,
} from "../lib/api";
import { useRepositoryStore } from "./repositoryStore";

export const DEFAULT_PRESET_PROMPTS: SuggestedPrompt[] = [
  {
    label: "Provider Architecture",
    prompt: "Show how inference providers (LM Studio, Ollama) are discovered, validated, and hot-reloaded.",
  },
  {
    label: "AST Extraction",
    prompt: "Explain how deterministic AST call graphs are extracted from Python and TypeScript files.",
  },
  {
    label: "Semantic Memory",
    prompt: "How does the memory pipeline ingest files, compute embeddings, and build the knowledge graph?",
  },
  {
    label: "Context Budget",
    prompt: "How does the context engine select relevant symbols, rank evidence, and compress tokens?",
  },
];

interface ContextStore {
  taskPrompt: string;
  selectedRepoId: string | null;
  maxTokens: number;
  includeStructuralGraph: boolean;

  synthesizing: boolean;
  error: string | null;
  result: AgentContextResponse | null;

  suggestedPrompts: SuggestedPrompt[];
  loadingPrompts: boolean;
  promptSource: "ai" | "heuristic" | "preset";

  savedPackages: SavedContextPackage[];
  loadingPackages: boolean;

  setTaskPrompt: (prompt: string) => void;
  setSelectedRepoId: (repoId: string | null) => void;
  setMaxTokens: (tokens: number) => void;
  setIncludeStructuralGraph: (include: boolean) => void;

  synthesize: () => Promise<void>;
  fetchPrompts: (repoId?: string) => Promise<void>;
  fetchPackages: () => Promise<void>;
  saveCurrentAsPackage: (name: string, tags?: string[]) => Promise<SavedContextPackage | null>;
  deleteSavedPackage: (packageId: string) => Promise<void>;
  clearResult: () => void;
}

export const useContextMenuStore = create<ContextStore>((set, get) => ({
  taskPrompt: "",
  selectedRepoId: null,
  maxTokens: 4096,
  includeStructuralGraph: true,

  synthesizing: false,
  error: null,
  result: null,

  suggestedPrompts: DEFAULT_PRESET_PROMPTS,
  loadingPrompts: false,
  promptSource: "preset",

  savedPackages: [],
  loadingPackages: false,

  setTaskPrompt: (prompt) => set({ taskPrompt: prompt }),
  setSelectedRepoId: (repoId) => set({ selectedRepoId: repoId }),
  setMaxTokens: (tokens) => set({ maxTokens: tokens }),
  setIncludeStructuralGraph: (include) => set({ includeStructuralGraph: include }),

  synthesize: async () => {
    const { taskPrompt, maxTokens, includeStructuralGraph } = get();
    if (!taskPrompt.trim()) return;

    const repoStore = useRepositoryStore.getState();
    const activeRepo = get().selectedRepoId
      ? repoStore.repositories.find((r) => r.id === get().selectedRepoId)
      : repoStore.selectedRepo || (repoStore.repositories.length > 0 ? repoStore.repositories[0] : null);

    if (!activeRepo) {
      set({ error: "No repository selected. Please select a repository first." });
      return;
    }

    set({ synthesizing: true, error: null });

    try {
      const response = await getAgentContext({
        task_prompt: taskPrompt.trim(),
        repository_path: activeRepo.local_path,
        dataset_name: activeRepo.name,
        max_tokens: maxTokens,
        include_structural_graph: includeStructuralGraph,
      });

      set({
        result: response,
        synthesizing: false,
        error: response.success ? null : "Synthesis did not succeed",
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({
        synthesizing: false,
        error: msg,
      });
    }
  },

  fetchPrompts: async (repoId?: string) => {
    const targetId = repoId || get().selectedRepoId || useRepositoryStore.getState().selectedId;
    if (!targetId) return;

    set({ loadingPrompts: true });
    try {
      const res = await getSuggestedPrompts(targetId);
      if (res && res.prompts && res.prompts.length > 0) {
        set({
          suggestedPrompts: res.prompts,
          promptSource: res.source,
          loadingPrompts: false,
        });
      } else {
        set({ loadingPrompts: false });
      }
    } catch {
      set({ loadingPrompts: false });
    }
  },

  fetchPackages: async () => {
    set({ loadingPackages: true });
    try {
      const res = await listContextPackages();
      set({ savedPackages: res.packages || [], loadingPackages: false });
    } catch {
      set({ loadingPackages: false });
    }
  },

  saveCurrentAsPackage: async (name: string, tags: string[] = []) => {
    const { result, taskPrompt } = get();
    if (!result) return null;

    const repoStore = useRepositoryStore.getState();
    const activeRepo = repoStore.selectedRepo || repoStore.repositories[0];

    const payload: ContextPackageSaveRequest = {
      name,
      task: taskPrompt,
      objective: result.task_summary || taskPrompt,
      repository_id: activeRepo?.id || "unknown",
      repository_name: activeRepo?.name || "unknown",
      repository_branch: activeRepo?.branch || "main",
      repository_commit: activeRepo?.commit_hash || "",
      indexing_version: "v1.0",
      markdown: result.context_markdown,
      section_count: 5,
      token_estimate: result.estimated_tokens,
      total_time_ms: result.generation_time_ms,
      tags,
    };

    try {
      const saved = await saveContextPackage(payload);
      set((state) => ({ savedPackages: [saved, ...state.savedPackages] }));
      return saved;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to save package" });
      return null;
    }
  },

  deleteSavedPackage: async (packageId: string) => {
    try {
      await deleteContextPackage(packageId);
      set((state) => ({
        savedPackages: state.savedPackages.filter((p) => p.id !== packageId),
      }));
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to delete package" });
    }
  },

  clearResult: () => set({ result: null, error: null }),
}));
