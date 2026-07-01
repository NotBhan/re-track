import { create } from "zustand";
import type { ContextResponse, AdvancedOptions } from "@/types";

import { generateContext } from "@/lib/api";

interface ContextStore {
  objective: string;
  selectedRepo: string;
  topK: number;
  advancedOptions: AdvancedOptions;
  result: ContextResponse | null;
  loading: boolean;
  error: string | null;
  history: ContextResponse[];
  setObjective: (v: string) => void;
  setSelectedRepo: (v: string) => void;
  setTopK: (v: number) => void;
  toggleAdvanced: (key: keyof AdvancedOptions) => void;
  setLoading: (v: boolean) => void;
  setError: (v: string | null) => void;
  setResult: (r: ContextResponse) => void;
  generatePackage: () => Promise<void>;
  reset: () => void;
}

const initialAdvanced: AdvancedOptions = {
  dedup: true,
  resolveRefs: true,
  aggressiveCompress: false,
};

export const useContextStore = create<ContextStore>((set, get) => ({
  objective: "",
  selectedRepo: "andes-core-api",
  topK: 25,
  advancedOptions: initialAdvanced,
  result: null,
  loading: false,
  error: null,
  history: [],

  setObjective: (v) => set({ objective: v }),
  setSelectedRepo: (v) => set({ selectedRepo: v }),
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
}));
