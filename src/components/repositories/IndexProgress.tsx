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
          <CheckCircle2 className="w-4 h-4 text-secondary" />
        ) : progress?.status === "error" ? (
          <AlertCircle className="w-4 h-4 text-error" />
        ) : (
          <Loader2 className="w-4 h-4 animate-spin text-primary" />
        )}
        <span className="text-sm font-medium text-on-surface">
          {progress?.status === "indexed"
            ? `Completed indexing ${repositoryName}`
            : `Indexing ${repositoryName}`}
        </span>
      </div>

      <div className="rounded-lg bg-surface-container-lowest border border-outline-variant p-4 space-y-3">
        {/* Stage */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-on-surface-variant">{stageLabel}</span>
          {progress && progress.status !== "indexed" && progress.status !== "error" && (
            <span className="text-xs text-on-surface-variant/60">
              {formatElapsed(elapsed)}
            </span>
          )}
        </div>

        {/* Progress bar */}
        {progress && progress.total_files > 0 && progress.status !== "indexed" && (
          <div className="w-full bg-surface-container-high rounded-full h-1.5">
            <div
              className="bg-primary h-1.5 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(100, (progress.processed_files / progress.total_files) * 100)}%`,
              }}
            />
          </div>
        )}

        {/* Stats */}
        {progress && (
          <div className="flex flex-wrap gap-3 text-xs text-on-surface-variant">
            {progress.file_count > 0 && (
              <span>{progress.file_count} files</span>
            )}
            {progress.size_bytes > 0 && (
              <span>{formatBytes(progress.size_bytes)}</span>
            )}
            {progress.total_files > 0 && (
              <span>
                {progress.processed_files}/{progress.total_files} processed
              </span>
            )}
          </div>
        )}

        {/* Language/framework badges */}
        {progress && (progress.languages.length > 0 || progress.frameworks.length > 0) && (
          <div className="flex flex-wrap gap-1.5">
            {progress.languages.map((lang) => (
              <span
                key={lang}
                className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary"
              >
                {lang}
              </span>
            ))}
            {progress.frameworks.map((fw) => (
              <span
                key={fw}
                className="inline-flex items-center rounded-full bg-secondary/10 px-2 py-0.5 text-xs text-secondary"
              >
                {fw}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Error */}
      {progress?.status === "error" && progress.error && (
        <div className="rounded-md bg-error/10 border border-error/30 px-4 py-3 text-sm text-error">
          {progress.error}
        </div>
      )}
    </div>
  );
}
