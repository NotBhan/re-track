import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "../../lib/utils";

export interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

interface ToastContextValue {
  showToast: (message: string, type?: "success" | "error" | "info") => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let globalToastHandler: ((msg: string, type?: "success" | "error" | "info") => void) | null = null;

export const toast = {
  success: (msg: string) => globalToastHandler?.(msg, "success"),
  error: (msg: string) => globalToastHandler?.(msg, "error"),
  info: (msg: string) => globalToastHandler?.(msg, "info"),
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: "success" | "error" | "info" = "info") => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, type, message }]);

      setTimeout(() => {
        removeToast(id);
      }, 3500);
    },
    [removeToast]
  );

  globalToastHandler = showToast;

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto flex items-center justify-between p-3 rounded-lg border shadow-xl text-xs font-medium animate-in slide-in-from-bottom-2 duration-150",
              t.type === "success" && "bg-[#051a0e] text-[#10b981] border-[#10b981]/25",
              t.type === "error" && "bg-[#180808] text-[#f87171] border-[#451a1a]",
              t.type === "info" && "bg-[#121212] text-[#ededed] border-[#262626]"
            )}
          >
            <div className="flex items-center gap-2.5">
              {t.type === "success" && <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0" />}
              {t.type === "error" && <AlertCircle className="w-4 h-4 text-[#f87171] shrink-0" />}
              {t.type === "info" && <Info className="w-4 h-4 text-[#a1a1a1] shrink-0" />}
              <span className="leading-snug">{t.message}</span>
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-[#a1a1a1] hover:text-[#ededed] p-1 ml-2 rounded-sm"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
};
