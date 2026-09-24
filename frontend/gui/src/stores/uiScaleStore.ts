import { create } from "zustand";

const STORAGE_KEY = "retrack:ui-scale";
export const AVAILABLE_SCALES = [80, 90, 100, 110, 125, 140, 150];
const DEFAULT_SCALE = 100;

interface UiScaleState {
  scale: number; // percentage (e.g. 100)
  setScale: (scale: number) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetScale: () => void;
}

function getInitialScale(): number {
  if (typeof window === "undefined") return DEFAULT_SCALE;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = parseInt(saved, 10);
      if (!isNaN(parsed) && parsed >= 50 && parsed <= 200) {
        return parsed;
      }
    }
  } catch {
    // ignore
  }
  return DEFAULT_SCALE;
}

function applyScaleToDocument(scale: number) {
  if (typeof document === "undefined") return;
  // Apply zoom to documentElement for full-window crisp scaling in Tauri/Chromium/WebKit
  (document.documentElement.style as any).zoom = `${scale}%`;
  document.documentElement.style.setProperty("--ui-scale", `${scale / 100}`);
}

export const useUiScaleStore = create<UiScaleState>((set, get) => {
  const initial = getInitialScale();
  applyScaleToDocument(initial);

  return {
    scale: initial,
    setScale: (scale: number) => {
      const clamped = Math.max(75, Math.min(175, scale));
      try {
        localStorage.setItem(STORAGE_KEY, String(clamped));
      } catch {
        // ignore
      }
      applyScaleToDocument(clamped);
      set({ scale: clamped });
    },
    zoomIn: () => {
      const current = get().scale;
      const next = AVAILABLE_SCALES.find((s) => s > current) || Math.min(175, current + 10);
      get().setScale(next);
    },
    zoomOut: () => {
      const current = get().scale;
      const prev = [...AVAILABLE_SCALES].reverse().find((s) => s < current) || Math.max(75, current - 10);
      get().setScale(prev);
    },
    resetScale: () => {
      get().setScale(DEFAULT_SCALE);
    },
  };
});
