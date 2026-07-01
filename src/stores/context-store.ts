import { create } from "zustand";
import type { ContextResponse, AdvancedOptions, PipelineStep } from "@/types";
import { mockPipelineSteps } from "@/data/mock";

interface ContextStore {
  objective: string;
  selectedRepo: string;
  topK: number;
  advancedOptions: AdvancedOptions;
  pipelineSteps: PipelineStep[];
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
  reset: () => void;
}

const initialAdvanced: AdvancedOptions = {
  dedup: true,
  resolveRefs: true,
  aggressiveCompress: false,
};

export const useContextStore = create<ContextStore>((set) => ({
  objective: "",
  selectedRepo: "andes-core-api",
  topK: 25,
  advancedOptions: initialAdvanced,
  pipelineSteps: mockPipelineSteps,
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
  reset: () =>
    set({
      objective: "",
      result: null,
      loading: false,
      error: null,
    }),
}));
