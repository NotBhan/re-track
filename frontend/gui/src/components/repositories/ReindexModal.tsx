import { useEffect, useRef, useState } from "react";
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
  scanning: "Scanning AST files...",
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

function formatDuration(ms: number): string {
  if (ms <= 0) return "—";
  const totalSec = Math.ceil(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function ReindexModal({ repoId, open, onOpenChange }: ReindexModalProps) {
  const { repositories, progress, pollProgress, clearPoll, indexing, error } =
    useRepositoryStore();

  // Smoothed display percentage (we drive it with requestAnimationFrame to
  // avoid visible jumps when the poll interval fires).
  const [displayPct, setDisplayPct] = useState(0);
  const displayPctRef = useRef(0);

  // Interpolated elapsed ms — updated every 100 ms between polls so the
  // timer feels live rather than lurching forward once per second.
  const [liveElapsedMs, setLiveElapsedMs] = useState(0);
  const liveElapsedRef = useRef(0);
  const lastPollTimeRef = useRef<number | null>(null);
  const lastPollElapsedRef = useRef(0);

  const repo = repositories.find((r) => r.id === repoId);

  // ── Start / stop polling ──────────────────────────────────────────────────
  useEffect(() => {
    if (open && repoId) {
      setDisplayPct(0);
      displayPctRef.current = 0;
      setLiveElapsedMs(0);
      liveElapsedRef.current = 0;
      lastPollTimeRef.current = null;
      lastPollElapsedRef.current = 0;
      pollProgress(repoId);
    }
    return () => { clearPoll(); };
  }, [open, repoId, pollProgress, clearPoll]);

  // ── Sync backend elapsed_ms each time a poll arrives ──────────────────────
  useEffect(() => {
    if (!progress) return;
    const backendMs = progress.elapsed_ms ?? 0;
    lastPollTimeRef.current = performance.now();
    lastPollElapsedRef.current = backendMs;
    liveElapsedRef.current = backendMs;
    setLiveElapsedMs(backendMs);
  }, [progress]);

  // ── Interpolate elapsed between polls at 100 ms resolution ───────────────
  useEffect(() => {
    if (!open || !indexing) return;
    const id = setInterval(() => {
      if (lastPollTimeRef.current === null) return;
      const walledMs = performance.now() - lastPollTimeRef.current;
      const interpolated = lastPollElapsedRef.current + walledMs;
      liveElapsedRef.current = interpolated;
      setLiveElapsedMs(interpolated);
    }, 100);
    return () => clearInterval(id);
  }, [open, indexing]);

  // ── Smooth progress bar via rAF ───────────────────────────────────────────
  const isDone = progress?.status === "indexed";
  const isError = progress?.status === "error" || Boolean(error);
  const totalFiles = progress?.total_files || repo?.file_count || 1;
  const processedFiles = progress?.processed_files ?? (isDone ? totalFiles : 0);

  const targetPct = isDone
    ? 100
    : isError
    ? displayPctRef.current // freeze on error
    : Math.max(15, Math.min(99, Math.round((processedFiles / Math.max(1, totalFiles)) * 100)));

  useEffect(() => {
    let rafId: number;
    const animate = () => {
      const current = displayPctRef.current;
      const diff = targetPct - current;
      if (Math.abs(diff) < 0.2) {
        displayPctRef.current = targetPct;
        setDisplayPct(targetPct);
        return;
      }
      // Ease toward target — faster for large gaps, slower as we approach.
      const step = diff * 0.08;
      const next = current + step;
      displayPctRef.current = next;
      setDisplayPct(next);
      rafId = requestAnimationFrame(animate);
    };
    rafId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId);
  }, [targetPct]);

  // ── ETA calculation ───────────────────────────────────────────────────────
  const filesRemaining = Math.max(0, totalFiles - processedFiles);
  let etaLabel = "";
  if (!isDone && !isError && liveElapsedMs > 2000 && processedFiles > 0) {
    const msPerFile = liveElapsedMs / processedFiles;
    const etaMs = msPerFile * filesRemaining;
    etaLabel = `~${formatDuration(etaMs)} remaining`;
  } else if (isDone) {
    etaLabel = `Done in ${formatDuration(liveElapsedMs)}`;
  }

  if (!repo && !repoId) return null;

  const repoName = repo?.name || "Repository";
  const stageText = progress?.stage
    ? STAGE_LABELS[progress.stage] || progress.stage
    : progress?.status
    ? STAGE_LABELS[progress.status] || progress.status
    : indexing
    ? "Scanning & discovering repository files..."
    : "Ready to index";
  const pctDisplay = Math.round(displayPct);

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
                  {isDone
                    ? "Indexing Complete"
                    : isError
                    ? "Indexing Error"
                    : `Re-indexing ${repoName}`}
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

        {/* Progress Body */}
        <div className="space-y-4 py-2">
          {/* Stage label + elapsed / ETA row */}
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="font-semibold text-white">{stageText}</span>
            <span className="text-neutral-400 text-right">
              {etaLabel || formatDuration(liveElapsedMs)}
            </span>
          </div>

          {/* Progress bar + percentage */}
          <div className="space-y-1">
            <div className="w-full h-2 rounded-full bg-black border border-[#262626] overflow-hidden p-[1px]">
              <div
                className={`h-full rounded-full ${
                  isDone ? "bg-emerald-400" : isError ? "bg-red-500" : "bg-white"
                }`}
                style={{
                  width: `${displayPct}%`,
                  transition: "none", // driven by rAF, no CSS transition needed
                }}
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono text-neutral-500">
              <span>
                {processedFiles.toLocaleString()} / {totalFiles.toLocaleString()} files
              </span>
              <span
                className={
                  isDone ? "text-emerald-400" : isError ? "text-red-400" : "text-neutral-300"
                }
              >
                {pctDisplay}%
              </span>
            </div>
          </div>

          {/* Stats grid */}
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

          {/* Error notice */}
          {isError && (progress?.error || error) && (
            <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-xs font-mono text-red-300">
              {progress?.error || error}
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
