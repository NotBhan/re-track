import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  X,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { AgentContextResponse } from "@/lib/api";

export interface SynthesisStage {
  id: string;
  title: string;
  shortDesc: string;
  targetPercent: number;
}

export const SYNTHESIS_STAGES: SynthesisStage[] = [
  {
    id: "intent",
    title: "1. Intent & Symbol Extraction",
    shortDesc: "Parsing task objective and detecting key identifiers...",
    targetPercent: 18,
  },
  {
    id: "memory",
    title: "2. Vector & Graph Retrieval",
    shortDesc: "Querying LanceDB embeddings and Kuzu knowledge graph...",
    targetPercent: 38,
  },
  {
    id: "ast",
    title: "3. AST Call Graph Traversal",
    shortDesc: "Extracting caller-callee paths, components and imports...",
    targetPercent: 58,
  },
  {
    id: "dedup",
    title: "4. Deduplication & Scoring",
    shortDesc: "Filtering redundant memories and ranking relevance...",
    targetPercent: 75,
  },
  {
    id: "symbols",
    title: "5. Symbol Reference Resolution",
    shortDesc: "Matching exact file paths and code citations...",
    targetPercent: 90,
  },
  {
    id: "budget",
    title: "6. Budgeting & Markdown Build",
    shortDesc: "Compressing tokens and formatting Context Package...",
    targetPercent: 98,
  },
];

interface SynthesisModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  loading: boolean;
  onCancel: () => void;
  repoName: string;
  taskPrompt: string;
  maxTokens?: number;
  agentResponse: AgentContextResponse | null;
  error?: string | null;
}

function formatDuration(ms: number): string {
  if (ms <= 0) return "0.0s";
  const sec = (ms / 1000).toFixed(1);
  return `${sec}s`;
}

export function SynthesisModal({
  open,
  onOpenChange,
  loading,
  onCancel,
  repoName,
  taskPrompt,
  maxTokens = 8000,
  agentResponse,
  error,
}: SynthesisModalProps) {
  const [displayPct, setDisplayPct] = useState(0);
  const [liveElapsedMs, setLiveElapsedMs] = useState(0);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isDone = Boolean(agentResponse && !loading);
  const isError = Boolean(error && !loading);

  const [activeStageIdx, setActiveStageIdx] = useState(0);

  // ── Timer & Progress percentage interpolation ───────────────────────────────
  useEffect(() => {
    if (loading) {
      startTimeRef.current = Date.now();
      setDisplayPct(5);
      setLiveElapsedMs(0);
      setActiveStageIdx(0);

      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current;
        setLiveElapsedMs(elapsed);

        setDisplayPct((prev) => {
          if (prev >= 95) return Math.min(97, prev + 0.05);
          if (prev >= 90) return prev + 0.15;
          if (prev >= 75) return prev + 0.35;
          if (prev >= 40) return prev + 0.6;
          return prev + 0.9;
        });
      }, 50);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (isDone) {
        setDisplayPct(100);
        setActiveStageIdx(SYNTHESIS_STAGES.length - 1);
      }
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loading, isDone]);

  // Determine active stage from percentage
  useEffect(() => {
    if (!loading) return;
    const currentIdx = SYNTHESIS_STAGES.findIndex((s) => displayPct <= s.targetPercent);
    setActiveStageIdx(currentIdx !== -1 ? currentIdx : SYNTHESIS_STAGES.length - 1);
  }, [displayPct, loading]);

  const activeStage = SYNTHESIS_STAGES[activeStageIdx] || SYNTHESIS_STAGES[0];
  const pctDisplay = Math.round(displayPct);

  // ETA Calculation
  let etaLabel = "";
  if (loading && liveElapsedMs > 1000) {
    const projectedTotal = 4500;
    const remaining = Math.max(0, projectedTotal - liveElapsedMs);
    etaLabel = `~${(remaining / 1000).toFixed(1)}s remaining`;
  } else if (isDone) {
    etaLabel = `Done in ${formatDuration(liveElapsedMs)}`;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg bg-[#0a0a0a] border-[#262626] text-white p-6 shadow-2xl rounded-2xl">
        <DialogHeader className="pb-4 border-b border-[#222222]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-black border border-[#262626] flex items-center justify-center">
                {isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : isError ? (
                  <AlertCircle className="w-5 h-5 text-red-400" />
                ) : (
                  <Sparkles className="w-5 h-5 text-white animate-pulse" />
                )}
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-white tracking-tight">
                  {isDone
                    ? "Synthesis Complete"
                    : isError
                    ? "Synthesis Failed"
                    : "Synthesizing Context Package"}
                </DialogTitle>
                <p className="text-xs font-mono text-neutral-400 mt-0.5">
                  {repoName} • AST Knowledge & Vector Memory
                </p>
              </div>
            </div>

            <Badge
              variant="outline"
              className={`text-[10px] font-mono uppercase px-2.5 py-1 border ${
                isDone
                  ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
                  : isError
                  ? "border-red-500/40 text-red-400 bg-red-500/10"
                  : "border-white/30 text-white bg-white/5 animate-pulse"
              }`}
            >
              {isDone ? "Ready" : isError ? "Error" : "Synthesizing"}
            </Badge>
          </div>
        </DialogHeader>

        {/* Progress Body */}
        <div className="space-y-4 py-2 font-mono">
          {/* Target prompt preview */}
          {taskPrompt && (
            <div className="px-3 py-2 rounded-lg bg-black border border-[#222222] text-xs text-neutral-400 truncate">
              <span className="text-neutral-500 font-semibold mr-1.5">Task:</span>
              <span className="text-white italic">&ldquo;{taskPrompt}&rdquo;</span>
            </div>
          )}

          {/* Stage description & Elapsed */}
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-white truncate max-w-[280px]">
              {isDone ? "Context Package synthesized & ready!" : activeStage.title}
            </span>
            <span className="text-neutral-400 text-right">
              {etaLabel || formatDuration(liveElapsedMs)}
            </span>
          </div>

          {/* Progress Bar & Percentage */}
          <div className="space-y-1.5">
            <div className="w-full h-2 rounded-full bg-black border border-[#262626] overflow-hidden p-[1px]">
              <div
                className={`h-full rounded-full transition-all duration-100 ${
                  isDone
                    ? "bg-emerald-400 shadow-[0_0_8px_#34d399]"
                    : isError
                    ? "bg-red-500"
                    : "bg-white shadow-[0_0_8px_#ffffff]"
                }`}
                style={{
                  width: `${displayPct}%`,
                }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-neutral-500 font-mono">
              <span className="truncate max-w-[320px]">
                {isDone ? "Complete" : activeStage.shortDesc}
              </span>
              <span
                className={`font-bold ${
                  isDone ? "text-emerald-400" : isError ? "text-red-400" : "text-white"
                }`}
              >
                {pctDisplay}%
              </span>
            </div>
          </div>

          {/* Multi-Step Telemetry Checklist */}
          <div className="rounded-xl bg-black border border-[#222222] p-3 space-y-2">
            <div className="text-[10px] uppercase font-semibold text-neutral-400 tracking-wider mb-1">
              Telemetry Pipeline Stages
            </div>
            <div className="space-y-1.5">
              {SYNTHESIS_STAGES.map((stg, idx) => {
                const isStepCompleted = isDone || activeStageIdx > idx;
                const isStepActive = loading && activeStageIdx === idx;

                return (
                  <div
                    key={stg.id}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                      isStepActive
                        ? "bg-[#141414] border border-[#333333] text-white"
                        : isStepCompleted
                        ? "text-neutral-300"
                        : "text-neutral-600"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {isStepCompleted ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : isStepActive ? (
                        <RefreshCw className="w-3.5 h-3.5 text-white animate-spin" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-neutral-700 flex items-center justify-center text-[9px] text-neutral-600">
                          {idx + 1}
                        </div>
                      )}
                      <span className={isStepActive ? "font-bold text-white" : ""}>
                        {stg.title}
                      </span>
                    </div>

                    <span className="text-[10px] text-neutral-500">
                      {isStepCompleted ? "Done" : isStepActive ? "Active" : "Pending"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-black border border-[#222222] text-xs">
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Token Budget
              </span>
              <span className="font-bold text-white">
                {maxTokens.toLocaleString()} max
              </span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Intent Type
              </span>
              <span className="font-bold text-neutral-300 truncate block">
                {agentResponse?.intent_category || "Analyzing..."}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Memory Engine
              </span>
              <span className="font-bold text-emerald-400">
                LanceDB + Kuzu
              </span>
            </div>
          </div>

          {/* Error Message */}
          {isError && (
            <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-xs text-red-300">
              {error}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="pt-3 flex items-center justify-between border-t border-[#222222] gap-3">
          {loading ? (
            <>
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  onCancel();
                  onOpenChange(false);
                }}
                className="text-xs font-mono text-neutral-400 hover:text-white hover:bg-[#141414] gap-1.5"
              >
                <X className="w-3.5 h-3.5" />
                Cancel
              </Button>
              <Button
                type="button"
                onClick={() => onOpenChange(false)}
                className="h-9 px-4 font-mono text-xs font-semibold uppercase tracking-wider bg-white text-black hover:bg-neutral-200 rounded-lg"
              >
                Run in Background
              </Button>
            </>
          ) : (
            <Button
              type="button"
              onClick={() => onOpenChange(false)}
              className="w-full h-10 font-mono text-xs font-bold uppercase tracking-wider bg-white text-black hover:bg-neutral-200 rounded-lg shadow-sm"
            >
              <CheckCircle2 className="w-4 h-4 mr-2 text-emerald-600" />
              {isDone ? "Done • View Package" : "Dismiss"}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
