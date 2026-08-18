import { useEffect, useState, useRef } from "react";
import { Loader2, X, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

interface SynthesisProgressBarProps {
  loading: boolean;
  onCancel?: () => void;
  variant?: "card" | "compact" | "banner";
  className?: string;
  taskTitle?: string;
}

export function SynthesisProgressBar({
  loading,
  onCancel,
  variant = "card",
  className,
  taskTitle,
}: SynthesisProgressBarProps) {
  const [elapsedMs, setElapsedMs] = useState(0);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (loading) {
      startTimeRef.current = Date.now();
      setElapsedMs(0);

      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current;
        setElapsedMs(elapsed);
      }, 100);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setElapsedMs(0);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [loading]);

  const elapsedSec = (elapsedMs / 1000).toFixed(1);

  if (!loading) {
    return null;
  }

  // --- Compact Top Bar / Banner Variant ---
  if (variant === "compact" || variant === "banner") {
    return (
      <div className={cn("w-full overflow-hidden", className)}>
        <div className="flex items-center justify-between px-3 py-1.5 bg-[#0a0a0a] border-b border-[#1e1e1e] text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-white shrink-0" />
            <span className="text-white font-medium truncate">
              Synthesizing context package…
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[11px] text-neutral-400 font-mono flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {elapsedSec}s
            </span>
            {onCancel && (
              <Button
                variant="ghost"
                size="xs"
                onClick={onCancel}
                className="h-6 px-2 text-[11px] text-neutral-400 hover:text-red-400 hover:bg-red-500/10 cursor-pointer"
              >
                Cancel
              </Button>
            )}
          </div>
        </div>

        {/* Indeterminate linear loading bar */}
        <div className="h-0.5 w-full bg-[#141414] overflow-hidden">
          <div className="h-full bg-white animate-pulse w-full" />
        </div>
      </div>
    );
  }

  // --- Full Card Variant ---
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.15 }}
        className={cn(
          "rounded-lg bg-[#0a0a0a] border border-[#1e1e1e] p-4 shadow-xl space-y-3",
          className
        )}
      >
        {/* Header with Title, Timer & Cancel */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-md bg-[#141414] border border-[#222222] text-white flex items-center justify-center shrink-0">
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-semibold text-white tracking-tight">
                  Synthesizing Context Package
                </h4>
              </div>
              {taskTitle && (
                <p className="text-xs text-neutral-400 truncate max-w-sm sm:max-w-md mt-0.5 font-mono">
                  &ldquo;{taskTitle}&rdquo;
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs font-mono text-neutral-400 bg-[#050505] px-2 py-1 rounded-md border border-[#222222] flex items-center gap-1.5">
              <Clock className="w-3 h-3 text-neutral-500" />
              <span>{elapsedSec}s</span>
            </span>

            {onCancel && (
              <Button
                variant="outline"
                size="sm"
                onClick={onCancel}
                className="h-7 px-2.5 text-xs text-neutral-400 hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10 gap-1 cursor-pointer"
                title="Cancel Synthesis"
              >
                <X className="w-3 h-3" />
                <span>Cancel</span>
              </Button>
            )}
          </div>
        </div>

        {/* Indeterminate Activity Bar */}
        <div className="space-y-1.5">
          <div className="h-1 bg-[#141414] rounded-full overflow-hidden relative">
            <div className="h-full bg-white rounded-full w-1/3 animate-[pulse_1.5s_ease-in-out_infinite]" />
          </div>
          <div className="flex justify-between text-[11px] text-neutral-500 font-mono">
            <span>Querying AST call graph, semantic embeddings &amp; memory topology…</span>
            <span>Active</span>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
