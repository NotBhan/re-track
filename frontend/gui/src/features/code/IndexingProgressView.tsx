import React, { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import type { IndexingProgress } from "../../types/api";
import { formatNumber } from "../../lib/utils";

interface IndexingProgressViewProps {
  progress: IndexingProgress;
  startedAt?: number | null;
}

function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

export const IndexingProgressView: React.FC<IndexingProgressViewProps> = ({
  progress,
  startedAt,
}) => {
  const [now, setNow] = useState(() => Date.now());

  const isDone = progress.status === "indexed";
  const isError = progress.status === "error";
  const isRunning = !isDone && !isError;

  useEffect(() => {
    if (!isRunning) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [isRunning]);

  // Real backend phase data (IndexingService reports named phases with a step index).
  const stageIndex = progress.stage_index ?? null;
  const stageTotal = progress.stage_total ?? null;
  const hasPhaseProgress =
    stageIndex !== null && stageTotal !== null && stageTotal > 0 && stageIndex > 0;
  const phasePercent = hasPhaseProgress
    ? Math.min(100, Math.round((stageIndex / stageTotal) * 100))
    : 0;

  const elapsedMs = startedAt && isRunning ? Math.max(0, now - startedAt) : progress.elapsed_ms;

  return (
    <div
      data-testid="indexing-progress"
      data-status={progress.status}
      className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          {isDone ? (
            <CheckCircle2 className="w-4 h-4 text-[#10b981] shrink-0" />
          ) : isError ? (
            <AlertCircle className="w-4 h-4 text-[#f87171] shrink-0" />
          ) : (
            <Loader2 className="w-4 h-4 text-[#ededed] animate-spin shrink-0" />
          )}
          <span className="text-xs font-medium text-[#ededed] truncate">{progress.stage}</span>
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-[#707070] shrink-0">
          {hasPhaseProgress && (
            <span>
              Phase {stageIndex} of {stageTotal}
            </span>
          )}
          {isDone && (
            <span>
              {formatNumber(progress.processed_files)} / {formatNumber(progress.total_files)} files
            </span>
          )}
          {isRunning && elapsedMs > 0 && <span>Elapsed {formatElapsed(elapsedMs)}</span>}
        </div>
      </div>

      {/* Phase progress when the backend reports a stage index, otherwise indeterminate */}
      {hasPhaseProgress ? (
        <div className="w-full h-1 bg-[#1a1a1a] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#ededed]/80 transition-all duration-300 rounded-full"
            style={{ width: `${phasePercent}%` }}
          />
        </div>
      ) : isDone ? (
        <div className="w-full h-1 bg-[#1a1a1a] rounded-full overflow-hidden">
          <div className="h-full w-full bg-[#10b981]/70 rounded-full" />
        </div>
      ) : isError ? (
        <div className="w-full h-1 bg-[#1a1a1a] rounded-full overflow-hidden">
          <div className="h-full w-full bg-[#f87171]/70 rounded-full" />
        </div>
      ) : (
        <div
          className="w-full h-1 bg-[#1a1a1a] rounded-full overflow-hidden"
          role="progressbar"
          aria-label="Indexing in progress"
        >
          <div className="h-full w-1/3 bg-[#ededed]/70 rounded-full animate-[retrack-indeterminate_1.4s_ease-in-out_infinite]" />
        </div>
      )}

      {progress.error && (
        <div className="text-xs text-[#f87171] bg-[#180808] p-2.5 rounded-sm border border-[#451a1a]">
          {progress.error}
        </div>
      )}
    </div>
  );
};
