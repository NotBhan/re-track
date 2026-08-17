import { useEffect, useState, useRef } from "react";
import { Loader2, X, Sparkles, Clock, CheckCircle2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

export interface SynthesisStage {
  id: string;
  title: string;
  description: string;
  targetPercent: number;
}

export const SYNTHESIS_STAGES: SynthesisStage[] = [
  {
    id: "intent",
    title: "Parsing Intent & Symbols",
    description: "Analyzing prompt objective & detecting target symbols with LLM...",
    targetPercent: 18,
  },
  {
    id: "graph",
    title: "Vector & Graph Retrieval",
    description: "Querying LanceDB embeddings & Kuzu knowledge graph topology...",
    targetPercent: 38,
  },
  {
    id: "ast",
    title: "AST Call Graph Traversal",
    description: "Extracting caller-callee paths, module imports, and component hierarchies...",
    targetPercent: 58,
  },
  {
    id: "dedup",
    title: "Deduplicating & Scoring",
    description: "Filtering redundant memories & calculating multi-factor relevance scores...",
    targetPercent: 75,
  },
  {
    id: "symbols",
    title: "Resolving Symbol References",
    description: "Matching exact file paths, line numbers, and critical code citations...",
    targetPercent: 90,
  },
  {
    id: "budget",
    title: "Budgeting & Markdown Render",
    description: "Compressing tokens within budget limit and formatting Context Package...",
    targetPercent: 98,
  },
];

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
  const [progress, setProgress] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (loading) {
      startTimeRef.current = Date.now();
      setProgress(5);
      setStageIndex(0);
      setElapsedMs(0);

      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current;
        setElapsedMs(elapsed);

        // Asymptotic progression: fast at first, moves through stages, slows at 94% until done
        setProgress((prev) => {
          if (prev >= 95) {
            return Math.min(97, prev + 0.05);
          }
          if (prev >= 90) {
            return prev + 0.15;
          }
          if (prev >= 75) {
            return prev + 0.35;
          }
          if (prev >= 40) {
            return prev + 0.55;
          }
          return prev + 0.85;
        });
      }, 50);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (progress > 0) {
        setProgress(100);
        const timeout = setTimeout(() => {
          setProgress(0);
          setElapsedMs(0);
        }, 1200);
        return () => clearTimeout(timeout);
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [loading]);

  // Determine current active stage from progress percentage
  useEffect(() => {
    if (!loading) return;
    const currentIdx = SYNTHESIS_STAGES.findIndex((s) => progress <= s.targetPercent);
    setStageIndex(currentIdx !== -1 ? currentIdx : SYNTHESIS_STAGES.length - 1);
  }, [progress, loading]);

  const activeStage = SYNTHESIS_STAGES[stageIndex] || SYNTHESIS_STAGES[0];
  const elapsedSec = (elapsedMs / 1000).toFixed(1);

  if (!loading && progress === 0) {
    return null;
  }

  // --- Compact Top Bar / Banner Variant ---
  if (variant === "compact" || variant === "banner") {
    return (
      <div className={cn("w-full overflow-hidden", className)}>
        <div className="flex items-center justify-between px-3 py-1.5 bg-[#0e0e0e] border-b border-[#262626] text-xs font-mono">
          <div className="flex items-center gap-2 min-w-0">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-white shrink-0" />
            <span className="text-white font-semibold truncate">
              Synthesizing: {activeStage.title}
            </span>
            <span className="text-[10px] text-neutral-400 hidden sm:inline">
              ({Math.round(progress)}%)
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] text-neutral-400 font-mono flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {elapsedSec}s
            </span>
            {onCancel && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onCancel}
                className="h-6 px-2 text-[10px] font-mono text-neutral-400 hover:text-red-400 hover:bg-red-500/10 cursor-pointer"
              >
                Cancel
              </Button>
            )}
          </div>
        </div>

        {/* Shimmering Progress Bar */}
        <Progress
          value={progress}
          variant="gradient"
          className="h-1 rounded-none border-none bg-[#141414]"
        />
      </div>
    );
  }

  // --- Full Card Variant ---
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        className={cn(
          "rounded-xl bg-gradient-to-b from-[#121212] to-black border border-[#2a2a2a] p-4 sm:p-5 shadow-2xl space-y-4",
          className
        )}
      >
        {/* Header with Title, Percentage & Cancel */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white text-black flex items-center justify-center font-bold shadow-md shrink-0">
              {progress >= 100 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : (
                <Sparkles className="w-4 h-4 text-black animate-pulse" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-xs sm:text-sm font-bold text-white tracking-tight flex items-center gap-2">
                  <span>Synthesizing Context Package</span>
                  <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    {Math.round(progress)}%
                  </span>
                </h4>
              </div>
              {taskTitle && (
                <p className="text-[11px] font-mono text-neutral-400 truncate max-w-sm sm:max-w-md mt-0.5">
                  &ldquo;{taskTitle}&rdquo;
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs font-mono text-neutral-400 bg-black px-2 py-1 rounded border border-[#262626] flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-neutral-400" />
              <span>{elapsedSec}s</span>
            </span>

            {onCancel && (
              <Button
                variant="outline"
                size="sm"
                onClick={onCancel}
                className="h-7 px-2.5 text-xs font-mono border-[#333] bg-black text-neutral-400 hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10 gap-1 cursor-pointer"
                title="Cancel Synthesis"
              >
                <X className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Cancel</span>
              </Button>
            )}
          </div>
        </div>

        {/* Progress Bar with Gradient Glow */}
        <div className="space-y-1.5">
          <Progress
            value={progress}
            variant="gradient"
            className="h-2 bg-[#181818]"
          />
          <div className="flex justify-between text-[11px] font-mono text-neutral-400">
            <span className="text-white font-medium flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin text-white" />
              <span>Stage {stageIndex + 1} of {SYNTHESIS_STAGES.length}: {activeStage.title}</span>
            </span>
            <span>{Math.round(progress)}% complete</span>
          </div>
        </div>

        {/* Active Stage Description */}
        <p className="text-xs font-mono text-neutral-300 italic bg-black/60 rounded-lg p-2.5 border border-[#222]">
          {activeStage.description}
        </p>

        {/* Step Progression Pills */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-1 pt-1">
          {SYNTHESIS_STAGES.map((s, idx) => {
            const isDone = progress > s.targetPercent;
            const isCurrent = idx === stageIndex;

            return (
              <div
                key={s.id}
                className={cn(
                  "px-2 py-1 rounded text-[10px] font-mono text-center truncate transition-colors border",
                  isDone
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    : isCurrent
                    ? "bg-white text-black border-white font-bold shadow-xs"
                    : "bg-black border-[#222] text-neutral-500"
                )}
                title={s.title}
              >
                {idx + 1}. {s.title.split(" ")[0]}
              </div>
            );
          })}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
