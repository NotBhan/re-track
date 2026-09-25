import { create } from "zustand";

const STORAGE_KEY = "retrack:markdown-view";

export type MarkdownViewMode = "rendered" | "raw";

interface PreferencesState {
  markdownViewMode: MarkdownViewMode;
  setMarkdownViewMode: (mode: MarkdownViewMode) => void;
}

function getInitialMarkdownViewMode(): MarkdownViewMode {
  if (typeof window === "undefined") return "rendered";
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "raw" || saved === "rendered") return saved;
  } catch {
    // ignore
  }
  return "rendered";
}

export const usePreferencesStore = create<PreferencesState>((set) => ({
  markdownViewMode: getInitialMarkdownViewMode(),
  setMarkdownViewMode: (mode) => {
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // ignore
    }
    set({ markdownViewMode: mode });
  },
}));
