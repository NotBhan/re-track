import React from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import type { IndexingProgress } from "../../types/api";
import { formatNumber } from "../../lib/utils";

interface IndexingProgressViewProps {
  progress: IndexingProgress;
}

export const IndexingProgressView: React.FC<IndexingProgressViewProps> = ({ progress }) => {
  const percent = progress.total_files > 0
    ? Math.min(100, Math.round((progress.processed_files / progress.total_files) * 100))
    : 0;

  const isDone = progress.status === "indexed";
  const isError = progress.status === "error";

  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {isDone ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : isError ? (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          ) : (
            <Loader2 className="w-4 h-4 text-sky-400 animate-spin" />
          )}
          <span className="text-xs font-semibold text-slate-200">{progress.stage}</span>
        </div>

        <div className="text-xs font-mono text-slate-400">
          {formatNumber(progress.processed_files)} / {formatNumber(progress.total_files)} files ({percent}%)
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 rounded-full ${
            isDone
              ? "bg-emerald-400"
              : isError
              ? "bg-rose-400"
              : "bg-sky-400"
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>

      {progress.error && (
        <div className="text-xs text-rose-400 bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20">
          {progress.error}
        </div>
      )}
    </div>
  );
};
