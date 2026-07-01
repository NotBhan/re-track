import { create } from "zustand";

type SettingsTab = "backend" | "cognee" | "ollama" | "storage" | "theme" | "about";

interface SettingsStore {
  activeTab: SettingsTab;
  setActiveTab: (tab: SettingsTab) => void;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  activeTab: "backend",
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
