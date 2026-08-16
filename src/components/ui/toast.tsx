import { create } from "zustand";
import { AlertCircle, CheckCircle2, Info, Loader2, X } from "lucide-react";

export type ToastType = "info" | "success" | "warning" | "error" | "loading";

export interface ToastItem {
  id: string;
  title?: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastStore {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, "id">) => string;
  removeToast: (id: string) => void;
  updateToast: (id: string, updates: Partial<ToastItem>) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    const item: ToastItem = { ...toast, id };
    set((state) => ({ toasts: [...state.toasts, item] }));

    if (toast.type !== "loading" && toast.duration !== 0) {
      const duration = toast.duration || 4000;
      setTimeout(() => {
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
      }, duration);
    }
    return id;
  },
  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },
  updateToast: (id, updates) => {
    set((state) => ({
      toasts: state.toasts.map((t) => {
        if (t.id === id) {
          const updated = { ...t, ...updates };
          if (updated.type !== "loading" && updated.duration !== 0) {
            const duration = updated.duration || 4000;
            setTimeout(() => {
              set((s) => ({ toasts: s.toasts.filter((item) => item.id !== id) }));
            }, duration);
          }
          return updated;
        }
        return t;
      }),
    }));
  },
}));

export const toast = {
  info: (message: string, title?: string) =>
    useToastStore.getState().addToast({ message, title, type: "info" }),
  success: (message: string, title?: string) =>
    useToastStore.getState().addToast({ message, title, type: "success" }),
  warning: (message: string, title?: string) =>
    useToastStore.getState().addToast({ message, title, type: "warning" }),
  error: (message: string, title?: string) =>
    useToastStore.getState().addToast({ message, title, type: "error" }),
  loading: (message: string, title?: string) =>
    useToastStore.getState().addToast({ message, title, type: "loading" }),
  dismiss: (id: string) => useToastStore.getState().removeToast(id),
  update: (id: string, updates: Partial<ToastItem>) =>
    useToastStore.getState().updateToast(id, updates),
};

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 max-w-md w-full pointer-events-none">
      {toasts.map((t) => {
        const isError = t.type === "error";
        const isSuccess = t.type === "success";
        const isLoading = t.type === "loading";
        const isWarning = t.type === "warning";

        return (
          <div
            key={t.id}
            className={`pointer-events-auto p-4 rounded-xl border backdrop-blur-md shadow-2xl transition-all animate-in fade-in slide-in-from-bottom-5 duration-200 flex items-start gap-3 bg-[#0a0a0a]/95 text-foreground ${
              isError
                ? "border-red-500/40 bg-red-950/20"
                : isSuccess
                ? "border-emerald-500/40 bg-emerald-950/20"
                : isWarning
                ? "border-amber-500/40 bg-amber-950/20"
                : "border-[#262626]"
            }`}
          >
            {isLoading && (
              <Loader2 className="w-4 h-4 text-white animate-spin shrink-0 mt-0.5" />
            )}
            {isSuccess && (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            )}
            {isError && (
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            )}
            {isWarning && (
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            )}
            {t.type === "info" && (
              <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            )}

            <div className="flex-1 text-xs">
              {t.title && (
                <p className="font-semibold font-mono text-white mb-0.5">{t.title}</p>
              )}
              <p className="text-muted-foreground font-mono leading-relaxed">{t.message}</p>
            </div>

            <button
              onClick={() => removeToast(t.id)}
              className="text-muted-foreground hover:text-white transition-colors p-1 rounded-md"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
