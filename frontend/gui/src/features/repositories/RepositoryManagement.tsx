import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderGit2,
  Plus,
  RefreshCw,
  Trash2,
  ArrowUpRight,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { useRepositoryStore } from "../../stores/repositoryStore";
import { RepositorySummaryPanel } from "./RepositorySummaryPanel";
import { IndexingProgressView } from "../code/IndexingProgressView";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { Dialog } from "../../components/Dialog";
import { EmptyState } from "../../components/EmptyState";
import { toast } from "../../app/providers/ToastProvider";
import { formatDate, formatNumber } from "../../lib/utils";
import { cn } from "../../lib/utils";

export const RepositoryManagement: React.FC = () => {
  const {
    repositories,
    selectedRepo,
    selectRepository,
    indexing,
    indexingRepoId,
    indexingStartedAt,
    progress,
    indexRepo,
    deleteRepo,
    hydrated,
    error,
    openAddRepository,
    fetchRepositories,
    clearError,
    dismissProgress,
  } = useRepositoryStore();

  const navigate = useNavigate();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const indexingRepo = repositories.find((r) => r.id === indexingRepoId);
  const showProgress =
    indexing || progress?.status === "indexed" || progress?.status === "error";

  const handleReindex = async (repoId: string) => {
    await indexRepo(repoId);
    const outcome = useRepositoryStore.getState().progress;
    if (outcome?.status === "indexed") {
      toast.success(
        `Indexing completed — ${outcome.processed_files} of ${outcome.total_files} files`
      );
    } else if (outcome?.status === "error") {
      toast.error(outcome.error || "Indexing failed");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    const target = repositories.find((r) => r.id === deleteTarget);
    setDeleting(true);
    try {
      await deleteRepo(deleteTarget);
      toast.success(`Repository "${target?.name || deleteTarget}" deleted`);
      setDeleteTarget(null);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete repository");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-5 bg-[#000000]">
      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4 pb-5 border-b border-[#262626]">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold tracking-tight text-[#ededed] flex items-center gap-2">
            <FolderGit2 className="w-4 h-4 text-[#a1a1a1]" />
            <span>Repository Management</span>
          </h2>
          <p className="text-xs text-[#a1a1a1] mt-0.5">
            Every repository imported into RE:Track — select one to inspect its indexed summary,
            re-index it, or remove it.
          </p>
        </div>

        <Button size="md" onClick={openAddRepository}>
          <Plus className="w-4 h-4" />
          <span>Add Repository</span>
        </Button>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 p-3 rounded-sm bg-[#180808] border border-[#451a1a] text-[#f87171] text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="truncate">{error}</span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                clearError();
                void fetchRepositories();
              }}
            >
              Retry
            </Button>
            <Button size="sm" variant="ghost" onClick={clearError}>
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {/* Active indexing progress / last outcome (real backend state) */}
      {showProgress && progress && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
              {indexing
                ? `Indexing ${indexingRepo?.name || "repository"}`
                : `Last index run — ${indexingRepo?.name || "repository"}`}
            </span>
            {!indexing && (
              <Button size="sm" variant="ghost" onClick={dismissProgress}>
                Dismiss
              </Button>
            )}
          </div>
          <IndexingProgressView progress={progress} startedAt={indexingStartedAt} />
        </div>
      )}

      {repositories.length === 0 ? (
        <div className="flex-1 flex items-center justify-center py-10">
          <EmptyState
            icon={<FolderGit2 className="w-8 h-8 text-[#a1a1a1]" />}
            title={hydrated ? "No Repositories Tracked" : "Loading Repositories"}
            description={
              hydrated
                ? "Add a local codebase or a GitHub URL to index it into RE:Track. Imported repositories persist and reappear here on every launch."
                : "Contacting the RE:Track backend to load your persisted repositories."
            }
            action={
              hydrated ? (
                <Button onClick={openAddRepository} size="md">
                  <Plus className="w-4 h-4" />
                  <span>Add Repository</span>
                </Button>
              ) : undefined
            }
          />
        </div>
      ) : (
        <div className="flex flex-wrap gap-5 items-start">
          {/* Tracked repositories list */}
          <section className="flex-1 min-w-[320px] rounded-lg border border-[#262626] bg-[#0a0a0a] overflow-hidden">
            <div className="px-4 py-2.5 border-b border-[#262626] flex items-center justify-between">
              <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
                Tracked Repositories
              </span>
              <span data-testid="repository-count" className="text-[11px] font-mono text-[#707070]">
                {repositories.length}
              </span>
            </div>

            <ul data-testid="repository-list" className="divide-y divide-[#1a1a1a]">
              {repositories.map((repo) => {
                const isActive = selectedRepo?.id === repo.id;
                const isIndexingThisRepo = indexing && indexingRepoId === repo.id;
                return (
                  <li key={repo.id} data-testid="repository-row" data-repo-name={repo.name}>
                    <button
                      type="button"
                      onClick={() => selectRepository(repo.id)}
                      aria-current={isActive}
                      className={cn(
                        "w-full text-left px-4 py-3 transition-colors flex items-start justify-between gap-3",
                        isActive ? "bg-[#121212]" : "hover:bg-[#0f0f0f]"
                      )}
                    >
                      <div className="min-w-0 flex flex-col gap-1">
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className={cn(
                              "text-xs font-medium truncate",
                              isActive ? "text-[#ededed]" : "text-[#a1a1a1]"
                            )}
                          >
                            {repo.name}
                          </span>
                          {isActive && (
                            <span className="text-[10px] font-medium text-[#ededed] shrink-0">
                              Active
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] font-mono text-[#707070] truncate" title={repo.local_path}>
                          {repo.source_type === "github" ? repo.source_url : repo.local_path}
                        </span>
                        <span className="text-[10px] font-mono text-[#555555] truncate">
                          {formatNumber(repo.file_count || 0)} files
                          {repo.languages?.length ? ` · ${repo.languages.slice(0, 3).join(", ")}` : ""}
                          {` · ${formatDate(repo.indexed_at)}`}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 pt-0.5">
                        {isIndexingThisRepo ? (
                          <Badge variant="accent">indexing</Badge>
                        ) : (
                          <Badge variant={repo.status === "indexed" ? "success" : "default"}>
                            {repo.status || "registered"}
                          </Badge>
                        )}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>

          {/* Selected repository summary + actions */}
          <section className="flex-1 min-w-[340px] rounded-lg border border-[#262626] bg-[#0a0a0a] flex flex-col">
            {selectedRepo ? (
              <>
                <div className="px-4 py-3 border-b border-[#262626] flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <h3 className="text-sm font-semibold text-[#ededed] truncate">
                        {selectedRepo.name}
                      </h3>
                      {selectedRepo.status === "indexed" ? (
                        <Badge variant="success">
                          <CheckCircle2 className="w-3 h-3" />
                          indexed
                        </Badge>
                      ) : (
                        <Badge variant="default">{selectedRepo.status || "registered"}</Badge>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-[#707070] truncate block mt-0.5">
                      {selectedRepo.local_path}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => navigate("/code")}
                      title="Open in Code explorer"
                    >
                      <ArrowUpRight className="w-3.5 h-3.5" />
                      <span>Open</span>
                    </Button>

                    <Button
                      size="sm"
                      loading={indexing && indexingRepoId === selectedRepo.id}
                      disabled={indexing}
                      onClick={() => void handleReindex(selectedRepo.id)}
                      title={
                        indexing
                          ? "An indexing run is already in progress"
                          : "Re-index this repository"
                      }
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>{selectedRepo.status === "indexed" ? "Re-index" : "Index"}</span>
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-[#f87171] hover:text-[#f87171] hover:bg-[#180808]"
                      onClick={() => setDeleteTarget(selectedRepo.id)}
                      title="Delete repository"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </Button>
                  </div>
                </div>

                <div className="p-4 overflow-y-auto">
                  <RepositorySummaryPanel repository={selectedRepo} />
                </div>
              </>
            ) : (
              <div className="p-8 text-center text-xs text-[#707070]">
                Select a repository to inspect its summary.
              </div>
            )}
          </section>
        </div>
      )}

      {/* Deletion confirmation */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Delete "${repositories.find((r) => r.id === deleteTarget)?.name || ""}"?`}
        description="This removes the repository from the RE:Track workspace and clears its derived memory records. Source files on disk are never touched."
        maxWidth="sm"
      >
        <div className="flex items-center justify-end gap-2.5 pt-4">
          <Button variant="ghost" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button variant="danger" loading={deleting} onClick={handleDelete}>
            Delete Repository
          </Button>
        </div>
      </Dialog>
    </div>
  );
};
