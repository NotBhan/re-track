import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { useRepositoryStore } from "@/stores/repository-store";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ReindexModalProps {
  repoId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const STAGE_LABELS: Record<string, string> = {
  registered: "Preparing repository...",
  scanning: "Scanning AST symbols & files...",
  indexing: "Synthesizing vector embeddings & knowledge graph...",
  indexed: "Indexing Completed",
  error: "Indexing Failed",
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

export function ReindexModal({ repoId, open, onOpenChange }: ReindexModalProps) {
  const { repositories, progress, pollProgress, clearPoll, indexing } = useRepositoryStore();
  const [elapsed, setElapsed] = useState(0);

  const repo = repositories.find((r) => r.id === repoId);

  useEffect(() => {
    if (open && repoId) {
      setElapsed(0);
      pollProgress(repoId);
    }
    return () => {
      clearPoll();
    };
  }, [open, repoId, pollProgress, clearPoll]);

  useEffect(() => {
    if (!open || !indexing) return;
    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1000);
    }, 1000);
    return () => clearInterval(timer);
  }, [open, indexing]);

  if (!repo && !repoId) return null;

  const repoName = repo?.name || "Repository";
  const stage = progress?.stage || (indexing ? "indexing" : "registered");
  const isDone = progress?.status === "indexed";
  const isError = progress?.status === "error";
  const stageText = STAGE_LABELS[stage] || stage;

  const totalFiles = progress?.total_files || repo?.file_count || 1;
  const processedFiles = progress?.processed_files || (isDone ? totalFiles : 0);
  const percentage = Math.min(100, Math.round((processedFiles / totalFiles) * 100)) || (isDone ? 100 : 15);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-[#0a0a0a] border-[#262626] text-white p-6 shadow-2xl rounded-xl">
        <DialogHeader className="pb-4 border-b border-[#222222]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-black border border-[#262626] flex items-center justify-center">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isError ? (
                  <AlertCircle className="w-4 h-4 text-red-400" />
                ) : (
                  <RefreshCw className="w-4 h-4 text-white animate-spin" />
                )}
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-white tracking-tight">
                  {isDone ? "Indexing Complete" : isError ? "Indexing Error" : `Re-indexing ${repoName}`}
                </DialogTitle>
                <p className="text-xs font-mono text-neutral-400 mt-0.5">
                  AST Knowledge & Vector Memory
                </p>
              </div>
            </div>

            <Badge
              variant="outline"
              className={`text-[10px] font-mono uppercase px-2 py-0.5 border ${
                isDone
                  ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                  : isError
                  ? "border-red-500/30 text-red-400 bg-red-500/10"
                  : "border-[#333333] text-neutral-300 bg-black"
              }`}
            >
              {progress?.status || (indexing ? "Indexing" : "Ready")}
            </Badge>
          </div>
        </DialogHeader>

        {/* Progress Card Body */}
        <div className="space-y-4 py-2">
          <div className="flex items-center justify-between text-xs font-mono text-neutral-300">
            <span className="font-semibold text-white">{stageText}</span>
            <span className="text-neutral-400">{formatElapsed(elapsed)}</span>
          </div>

          {/* High Contrast Progress Bar */}
          <div className="w-full h-2 rounded-full bg-black border border-[#262626] overflow-hidden p-[1px]">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                isDone ? "bg-emerald-400" : isError ? "bg-red-500" : "bg-white"
              }`}
              style={{ width: `${percentage}%` }}
            />
          </div>

          {/* Stats Metrics */}
          <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-black border border-[#222222] font-mono text-xs">
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Processed Files
              </span>
              <span className="font-bold text-white">
                {processedFiles} / {totalFiles}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider block">
                Repository Size
              </span>
              <span className="font-bold text-white">
                {formatBytes(repo?.size_bytes || progress?.size_bytes || 0)}
              </span>
            </div>
          </div>

          {/* Error notice if failed */}
          {isError && progress?.error && (
            <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-xs font-mono text-red-300">
              {progress.error}
            </div>
          )}
        </div>

        <div className="pt-2 flex justify-end gap-2 border-t border-[#222222]">
          <Button
            onClick={() => onOpenChange(false)}
            className="w-full h-10 font-mono text-xs font-semibold uppercase tracking-wider bg-white text-black hover:bg-neutral-200 rounded-lg"
          >
            {isDone ? "Done" : isError ? "Dismiss" : "Run in Background"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
