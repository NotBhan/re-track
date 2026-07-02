import { create } from "zustand";
import {
  listContextPackages,
  saveContextPackage,
  deleteContextPackage,
  appendContextPackage,
} from "@/lib/api";
import type {
  SavedContextPackage,
  ContextPackageSaveRequest,
  ContextPackageAppendRequest,
} from "@/lib/api";

interface ContextPackageStore {
  packages: SavedContextPackage[];
  loading: boolean;
  error: string | null;
  fetchPackages: () => Promise<void>;
  savePackage: (req: ContextPackageSaveRequest) => Promise<SavedContextPackage | null>;
  removePackage: (id: string) => Promise<void>;
  appendToPackage: (
    id: string,
    task: string,
    markdown: string,
    objective?: string
  ) => Promise<void>;
}

export const useContextPackageStore = create<ContextPackageStore>((set) => ({
  packages: [],
  loading: false,
  error: null,

  fetchPackages: async () => {
    set({ loading: true, error: null });
    try {
      const result = await listContextPackages();
      set({ packages: result.packages, loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  savePackage: async (req) => {
    set({ error: null });
    try {
      const saved = await saveContextPackage(req);
      set((state) => ({ packages: [saved, ...state.packages] }));
      return saved;
    } catch (err) {
      set({ error: String(err) });
      return null;
    }
  },

  removePackage: async (id) => {
    set({ error: null });
    try {
      await deleteContextPackage(id);
      set((state) => ({
        packages: state.packages.filter((p) => p.id !== id),
      }));
    } catch (err) {
      set({ error: String(err) });
    }
  },

  appendToPackage: async (id, task, markdown, objective) => {
    set({ error: null });
    try {
      const req: ContextPackageAppendRequest = {
        additional_task: task,
        additional_markdown: markdown,
        additional_objective: objective ?? "",
      };
      const updated = await appendContextPackage(id, req);
      set((state) => ({
        packages: state.packages.map((p) => (p.id === id ? updated : p)),
      }));
    } catch (err) {
      set({ error: String(err) });
    }
  },
}));
