import { create } from "zustand";
import type { ContextResponse, AdvancedOptions, SuggestedPrompt } from "@/lib/api";
import { generateContext, getSuggestedPrompts } from "@/lib/api";
import { useRepositoryStore } from "@/stores/repository-store";
import { toast } from "@/components/ui/toast";

export const PRESET_WORKBENCH_PROMPTS: SuggestedPrompt[] = [
  {
    label: "Settings & Providers",
    prompt: "Find where Settings are initialized and how LLM providers are configured and hot-reloaded.",
  },
  {
    label: "OAuth2 Login",
    prompt: "Implement OAuth2 login with Google and GitHub providers including session tokens.",
  },
  {
    label: "AST Call Graph",
    prompt: "Show how AST call graphs are extracted from Python and TypeScript source files.",
  },
  {
    label: "Memory Indexing",
    prompt: "How does the IndexingService discover files, filter ignore patterns, and batch memories into Cognee?",
  },
  {
    label: "Context Budget",
    prompt: "Explain how BudgetManager trims low-priority sections and compresses tokens at line boundaries.",
  },
];

interface ContextStore {
  objective: string;
  selectedRepo: string;
  selectedRepoId: string | null;
  topK: number;
  advancedOptions: AdvancedOptions;
  result: ContextResponse | null;
  loading: boolean;
  error: string | null;
  history: ContextResponse[];

  // Recommended Prompts State for Context Studio
  recommendedPrompts: SuggestedPrompt[];
  promptSource: "ai" | "heuristic" | "preset";
  loadingPrompts: boolean;
  promptsInitialized: boolean;

  setObjective: (v: string) => void;
  setSelectedRepo: (v: string) => void;
  setSelectedRepoById: (repoId: string) => void;
  clearSelectedRepoId: () => void;
  setTopK: (v: number) => void;
  toggleAdvanced: (key: keyof AdvancedOptions) => void;
  setLoading: (v: boolean) => void;
  setError: (v: string | null) => void;
  setResult: (r: ContextResponse) => void;
  generatePackage: () => Promise<void>;
  reset: () => void;

  // Recommended Prompts Actions
  initializeRecommendedPrompts: (repoId: string) => Promise<void>;
  generateRecommendedPrompts: (repoId: string, isManual?: boolean) => Promise<void>;
  setRecommendedPrompts: (prompts: SuggestedPrompt[], source?: "ai" | "heuristic" | "preset") => void;
}

const initialAdvanced: AdvancedOptions = {
  dedup: true,
  resolveRefs: true,
  aggressiveCompress: false,
};

export const useContextStore = create<ContextStore>((set, get) => ({
  objective: "",
  selectedRepo: "retrack-core-api",
  selectedRepoId: null,
  topK: 25,
  advancedOptions: initialAdvanced,
  result: null,
  loading: false,
  error: null,
  history: [],

  recommendedPrompts: PRESET_WORKBENCH_PROMPTS,
  promptSource: "preset",
  loadingPrompts: false,
  promptsInitialized: false,

  setObjective: (v) => set({ objective: v }),
  setSelectedRepo: (v) => set({ selectedRepo: v }),
  setSelectedRepoById: (repoId) => {
    const repo = useRepositoryStore.getState().repositories.find((r) => r.id === repoId);
    if (repo) {
      set({ selectedRepo: repo.name, selectedRepoId: repoId });
    }
  },
  clearSelectedRepoId: () => set({ selectedRepoId: null }),
  setTopK: (v) => set({ topK: v }),
  toggleAdvanced: (key) =>
    set((state) => ({
      advancedOptions: {
        ...state.advancedOptions,
        [key]: !state.advancedOptions[key],
      },
    })),
  setLoading: (v) => set({ loading: v }),
  setError: (v) => set({ error: v }),
  setResult: (r) =>
    set((state) => ({
      result: r,
      history: [r, ...state.history].slice(0, 10),
    })),
  generatePackage: async () => {
    const { objective, selectedRepo, topK } = get();
    if (!objective.trim()) return;

    set({ loading: true, error: null, result: null });
    try {
      const response = await generateContext({
        task: objective.trim(),
        datasets: [selectedRepo],
        top_k: topK,
      });
      set((state) => ({
        result: response,
        loading: false,
        history: [response, ...state.history].slice(0, 10),
      }));
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Generation failed",
        loading: false,
      });
    }
  },
  reset: () =>
    set({
      objective: "",
      result: null,
      loading: false,
      error: null,
    }),

  initializeRecommendedPrompts: async (repoId: string) => {
    const { promptsInitialized, loadingPrompts, generateRecommendedPrompts } = get();
    if (promptsInitialized || loadingPrompts || !repoId) return;
    set({ promptsInitialized: true });
    await generateRecommendedPrompts(repoId, false);
  },

  generateRecommendedPrompts: async (repoId: string, isManual = false) => {
    if (!repoId) return;
    set({ loadingPrompts: true });
    try {
      const res = await getSuggestedPrompts(repoId);
      if (res && res.prompts && res.prompts.length > 0) {
        set({
          recommendedPrompts: res.prompts,
          promptSource: res.source as "ai" | "heuristic",
          loadingPrompts: false,
        });
        if (isManual) {
          toast.success(
            res.source === "ai"
              ? "Generated fresh AI prompts from loaded model"
              : "Generated repository-tailored task prompts"
          );
        }
      } else {
        set({ loadingPrompts: false });
      }
    } catch (e) {
      console.debug("Failed to load suggested prompts", e);
      set({ loadingPrompts: false });
    }
  },

  setRecommendedPrompts: (prompts, source = "preset") =>
    set({ recommendedPrompts: prompts, promptSource: source }),
}));
