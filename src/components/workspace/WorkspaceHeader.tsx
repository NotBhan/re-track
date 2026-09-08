import { FolderGit2, RefreshCw, Layers, GitBranch, GitCommit, ArrowLeftRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Repository } from "@/types/repository";
import { IndexProgress } from "@/components/repositories/IndexProgress";

interface WorkspaceHeaderProps {
  repository: Repository;
  scanning: boolean;
  onTriggerScan: () => void;
  onOpenReindex: () => void;
  onClearSelection: () => void;
}

export function WorkspaceHeader({
  repository,
  scanning,
  onTriggerScan,
  onOpenReindex,
  onClearSelection,
}: WorkspaceHeaderProps) {
  const branchName = repository.branch || (repository.metadata?.branch as string) || null;
  const commitHash = repository.commit_hash || (repository.metadata?.commit_hash as string) || (repository.metadata?.commit as string) || null;

  const isIndexingOrScanning = repository.status === "scanning" || repository.status === "indexing" || scanning;

  return (
    <div className="border-b border-[#1e1e1e] bg-[#070707] shrink-0">
      <div className="px-4 sm:px-6 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Left: Identity and Git metadata */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-[#121212] border border-[#262626] flex items-center justify-center text-white shrink-0">
            <FolderGit2 className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-bold text-white tracking-tight truncate">
                {repository.name}
              </h2>

              {/* Status Badge */}
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px] font-mono capitalize",
                  repository.status === "indexed"
                    ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/60"
                    : repository.status === "indexing" || repository.status === "scanning"
                    ? "bg-amber-950/40 text-amber-400 border-amber-800/60"
                    : "bg-neutral-900 text-neutral-400 border-neutral-800"
                )}
              >
                {repository.status}
              </Badge>

              {/* Truthful Branch Name */}
              {branchName ? (
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono py-0 h-4 border-neutral-700 bg-neutral-900 text-neutral-300 gap-1"
                >
                  <GitBranch className="w-2.5 h-2.5" />
                  {branchName}
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono py-0 h-4 border-neutral-800 bg-neutral-950 text-neutral-500"
                >
                  Git: Not detected
                </Badge>
              )}

              {/* Truthful Commit SHA */}
              {commitHash ? (
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono py-0 h-4 border-neutral-700 bg-neutral-900 text-neutral-300 gap-1"
                >
                  <GitCommit className="w-2.5 h-2.5" />
                  {commitHash.slice(0, 7)}
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="text-[10px] font-mono py-0 h-4 border-neutral-800 bg-neutral-950 text-neutral-500"
                >
                  SHA: Unavailable
                </Badge>
              )}
            </div>

            <p className="text-[11px] font-mono text-neutral-400 truncate mt-0.5" title={repository.local_path}>
              {repository.local_path}
            </p>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
          <Button
            variant="outline"
            size="sm"
            onClick={onTriggerScan}
            disabled={scanning || repository.status === "scanning"}
            className="h-8 px-3 text-xs font-mono gap-1.5 border-[#262626] bg-[#0a0a0a] text-neutral-300 hover:text-white hover:bg-[#1a1a1a] cursor-pointer"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", (scanning || repository.status === "scanning") && "animate-spin text-amber-400")} />
            <span>{scanning || repository.status === "scanning" ? "Scanning..." : "Scan Changes"}</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={onOpenReindex}
            disabled={repository.status === "indexing"}
            className="h-8 px-3 text-xs font-mono gap-1.5 border-[#262626] bg-[#0a0a0a] text-neutral-300 hover:text-white hover:bg-[#1a1a1a] cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Re-index</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClearSelection}
            className="h-8 px-2.5 text-xs font-mono text-neutral-400 hover:text-white hover:bg-[#1a1a1a] cursor-pointer gap-1"
          >
            <ArrowLeftRight className="w-3 h-3" />
            <span>Switch</span>
          </Button>
        </div>
      </div>

      {/* Progress banner when actively indexing or scanning */}
      {isIndexingOrScanning && (
        <div className="px-4 sm:px-6 py-2.5 bg-[#0e0e0e] border-t border-[#1a1a1a]">
          <IndexProgress repositoryName={repository.name} repoId={repository.id} />
        </div>
      )}
    </div>
  );
}
