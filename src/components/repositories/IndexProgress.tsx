import { useEffect, useState } from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { useRepositoryStore } from "@/stores/repository-store";

interface IndexProgressProps {
  repositoryName: string;
  repoId: string;
}

const STAGE_LABELS: Record<string, string> = {
  registered: "Ready to index",
  scanning: "Scanning files...",
  indexing: "Building knowledge graph...",
  indexed: "Completed",
  error: "Error occurred",
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function IndexProgress({ repositoryName, repoId }: IndexProgressProps) {
  const progress = useRepositoryStore((s) => s.progress);
  const pollProgress = useRepositoryStore((s) => s.pollProgress);
  const clearPoll = useRepositoryStore((s) => s.clearPoll);

  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    pollProgress(repoId);
    return () => clearPoll();
  }, [repoId, pollProgress, clearPoll]);

  useEffect(() => {
    if (!progress || progress.status === "indexed" || progress.status === "error") {
      return;
    }
    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1000);
    }, 1000);
    return () => clearInterval(timer);
  }, [progress?.status]);

  const stageLabel = progress
    ? STAGE_LABELS[progress.stage] ?? progress.stage
    : "Starting...";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {progress?.status === "indexed" ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        ) : progress?.status === "error" ? (
          <AlertCircle className="w-4 h-4 text-red-400" />
        ) : (
          <Loader2 className="w-4 h-4 animate-spin text-white" />
        )}
        <span className="text-sm font-bold font-mono text-white">
          {progress?.status === "indexed"
            ? `Completed indexing ${repositoryName}`
            : `Indexing ${repositoryName}`}
        </span>
      </div>

      <div className="rounded-xl bg-black border border-[#262626] p-4 space-y-3 font-mono">
        {/* Stage */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-neutral-300">{stageLabel}</span>
          {progress && progress.status !== "indexed" && progress.status !== "error" && (
            <span className="text-xs text-neutral-500">
              {formatElapsed(elapsed)}
            </span>
          )}
        </div>

        {/* Progress bar */}
        {progress && progress.total_files > 0 && (
          <div className="w-full bg-[#141414] border border-[#262626] rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-300 ${
                progress.status === "indexed"
                  ? "bg-emerald-400"
                  : progress.status === "error"
                  ? "bg-red-500"
                  : "bg-white"
              }`}
              style={{
                width:
                  progress.status === "indexed"
                    ? "100%"
                    : `${Math.min(100, (progress.processed_files / progress.total_files) * 100)}%`,
              }}
            />
          </div>
        )}

        {/* Stats */}
        {progress && (
          <div className="flex flex-wrap gap-3 text-xs text-neutral-400">
            {progress.file_count > 0 && (
              <span>{progress.file_count} files</span>
            )}
            {progress.size_bytes > 0 && (
              <span>{formatBytes(progress.size_bytes)}</span>
            )}
            {progress.total_files > 0 && (
              <span className="text-white font-semibold">
                {progress.processed_files}/{progress.total_files} processed
              </span>
            )}
          </div>
        )}

        {/* Language/framework badges */}
        {progress && (progress.languages.length > 0 || progress.frameworks.length > 0) && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {progress.languages.map((lang) => (
              <span
                key={lang}
                className="inline-flex items-center rounded-md bg-[#141414] border border-[#262626] px-2 py-0.5 text-[10px] text-neutral-300 font-mono"
              >
                {lang}
              </span>
            ))}
            {progress.frameworks.map((fw) => (
              <span
                key={fw}
                className="inline-flex items-center rounded-md bg-[#141414] border border-[#262626] px-2 py-0.5 text-[10px] text-neutral-300 font-mono"
              >
                {fw}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Error */}
      {progress?.status === "error" && progress.error && (
        <div className="rounded-lg bg-red-950/40 border border-red-500/30 px-4 py-3 text-xs font-mono text-red-300">
          {progress.error}
        </div>
      )}
    </div>
  );
}
