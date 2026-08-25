import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, RefreshCw, ArrowRight, CheckCircle2 } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

interface ProviderAlertBannerProps {
  className?: string;
  showWhenOnline?: boolean;
}

export function ProviderAlertBanner({ className, showWhenOnline = false }: ProviderAlertBannerProps) {
  const navigate = useNavigate();
  const {
    backendOnline,
    providerIdentity,
    providerReachable,
    activeModel,
    configuredModel,
    engineReason,
    pollHealth,
  } = useHealthStore();
  const [retrying, setRetrying] = useState(false);

  const isOnline = backendOnline && providerReachable;

  const providerLabel =
    providerIdentity === "lmstudio"
      ? "LM Studio"
      : providerIdentity === "ollama"
      ? "Ollama"
      : providerIdentity === "openai_compatible"
      ? "OpenAI Compatible"
      : providerIdentity || "Local Provider";

  const activeModelDisplay = activeModel || configuredModel || "Connected";

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await pollHealth();
    } finally {
      setTimeout(() => setRetrying(false), 600);
    }
  };

  if (isOnline && !showWhenOnline) {
    return null;
  }

  return (
    <AnimatePresence>
      {!isOnline ? (
        <motion.div
          initial={{ opacity: 0, y: -10, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: -10, height: 0 }}
          transition={{ duration: 0.25 }}
          className={cn(
            "relative overflow-hidden rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-950/40 via-black to-amber-950/20 p-3.5 sm:p-4 text-amber-200 shadow-lg",
            className
          )}
        >
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                <AlertCircle className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs sm:text-sm font-semibold text-white tracking-tight flex items-center gap-2">
                  <span>AI Provider Offline</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {providerLabel}
                  </span>
                </p>
                <p className="text-xs text-neutral-400 mt-0.5 font-mono">
                  {engineReason || "Inference provider endpoint is unreachable. Verify provider host and port in Settings."}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end shrink-0">
              <button
                onClick={handleRetry}
                disabled={retrying}
                className="px-3 py-1.5 rounded-lg border border-[#333] bg-[#141414] hover:bg-[#202020] text-neutral-300 hover:text-white text-xs font-mono transition-colors flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
              >
                <RefreshCw className={cn("w-3.5 h-3.5", retrying && "animate-spin text-amber-400")} />
                <span>{retrying ? "Checking..." : "Retry"}</span>
              </button>

              <button
                onClick={() => navigate("/settings")}
                className="px-3.5 py-1.5 rounded-lg bg-amber-400 text-black hover:bg-amber-300 text-xs font-semibold font-mono transition-all flex items-center gap-1.5 shadow-sm cursor-pointer"
              >
                <span>Configure</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </motion.div>
      ) : showWhenOnline ? (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "rounded-lg border border-emerald-500/20 bg-emerald-950/20 px-3 py-1.5 text-xs font-mono text-emerald-300 flex items-center justify-between",
            className
          )}
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>AI Provider Active: <strong>{providerLabel} ({activeModelDisplay})</strong></span>
          </div>
          <span className="text-[10px] text-emerald-400/80">Ready for synthesis</span>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
