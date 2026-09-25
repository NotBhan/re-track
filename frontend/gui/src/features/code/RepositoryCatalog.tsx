import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderGit2,
  RefreshCw,
  Trash2,
  Search,
  Network,
  FileText,
  Plus,
  ArrowLeft,
} from "lucide-react";
import { useRepositoryStore } from "../../stores/repositoryStore";
import { CallGraphView } from "./CallGraphView";
import { ManifestTable } from "./ManifestTable";
import { IndexingProgressView } from "./IndexingProgressView";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { Tabs } from "../../components/Tabs";
import { Dialog } from "../../components/Dialog";
import { EmptyState } from "../../components/EmptyState";
import { toast } from "../../app/providers/ToastProvider";

export const RepositoryCatalog: React.FC = () => {
  const {
    repositories,
    selectedRepo,
    indexing,
    indexingRepoId,
    indexingStartedAt,
    progress,
    indexRepo,
    scanRepo,
    deleteRepo,
    scanning,
    openAddRepository,
    dismissProgress,
  } = useRepositoryStore();

  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"graph" | "manifest">("graph");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // If no repository is registered, show clean initial launch state
  if (!selectedRepo && repositories.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <EmptyState
          icon={<FolderGit2 className="w-8 h-8 text-[#a1a1a1]" />}
          title="No Repositories Tracked"
          description="Add a local codebase or Git repository to explore its AST call graph, generate developer context, and build semantic memory."
          action={
            <Button onClick={openAddRepository} size="md">
              <Plus className="w-4 h-4" />
              <span>Add Repository</span>
            </Button>
          }
        />
      </div>
    );
  }

  const handleDelete = async () => {
    if (!selectedRepo) return;
    setDeleting(true);
    try {
      await deleteRepo(selectedRepo.id);
      toast.success(`Repository "${selectedRepo.name}" deleted`);
      setDeleteConfirmOpen(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete repository");
    } finally {
      setDeleting(false);
    }
  };

  const isIndexed = selectedRepo?.status === "indexed" || selectedRepo?.indexed_at;
  const isIndexingThisRepo = indexing && indexingRepoId === selectedRepo?.id;
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

  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-5">
      {/* Repository Header: Name, path, branch, actions */}
      <div className="flex flex-wrap items-start justify-between gap-4 pb-5 border-b border-[#262626]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <h2 className="text-lg font-semibold tracking-tight text-[#ededed] truncate">
              {selectedRepo?.name}
            </h2>
            <Badge variant={isIndexed ? "success" : "default"}>
              {selectedRepo?.status || "registered"}
            </Badge>
            {selectedRepo?.branch && (
              <span className="text-[11px] font-mono text-[#707070]">
                branch: {selectedRepo.branch}
              </span>
            )}
          </div>
          <div className="text-[11px] text-[#707070] font-mono mt-1 break-all">
            {selectedRepo?.local_path}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => navigate("/repositories")}
            title="Back to Repository Management"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Repositories</span>
          </Button>

          <Button
            size="sm"
            variant="secondary"
            loading={scanning}
            onClick={() => selectedRepo && scanRepo(selectedRepo.id)}
            title="Scan repository structure"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Scan</span>
          </Button>

          <Button
            size="sm"
            loading={isIndexingThisRepo}
            disabled={indexing}
            onClick={() => selectedRepo && void handleReindex(selectedRepo.id)}
            title={indexing ? "An indexing run is already in progress" : "Re-index this repository"}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{isIndexed ? "Re-index" : "Index"}</span>
          </Button>

          <Button
            size="sm"
            variant="ghost"
            className="text-[#f87171] hover:text-[#f87171] hover:bg-[#180808]"
            onClick={() => setDeleteConfirmOpen(true)}
            title="Delete repository"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Delete</span>
          </Button>
        </div>
      </div>

      {/* Real-time Indexing Progress View */}
      {showProgress && progress && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
              {indexing
                ? `Indexing ${repositories.find((r) => r.id === indexingRepoId)?.name || "repository"}`
                : `Last index run — ${repositories.find((r) => r.id === indexingRepoId)?.name || "repository"}`}
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

      {/* Tabs: AST Call Graph vs Manifest Overview */}
      <div className="flex flex-col gap-4">
        <Tabs
          items={[
            { id: "graph", label: "AST Call Graph", icon: <Network className="w-3.5 h-3.5" /> },
            { id: "manifest", label: "Manifest & Overview", icon: <FileText className="w-3.5 h-3.5" /> },
          ]}
          activeId={activeTab}
          onChange={(id) => setActiveTab(id as "graph" | "manifest")}
        />

        {activeTab === "graph" ? (
          <CallGraphView
            status={selectedRepo?.call_graph_status || (isIndexed ? "analyzed" : "not_analyzed")}
            nodes={selectedRepo?.call_graph_nodes || []}
            edges={selectedRepo?.call_graph_edges || []}
            error={selectedRepo?.call_graph_error}
            onAnalyze={() => selectedRepo && void handleReindex(selectedRepo.id)}
          />
        ) : (
          selectedRepo && <ManifestTable repository={selectedRepo} />
        )}
      </div>

      {/* Deletion Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onOpenChange={setDeleteConfirmOpen}
        title={`Delete "${selectedRepo?.name}"?`}
        description="This removes the repository from the RE:Track workspace and clears its derived memory records. Source files on disk are never touched."
        maxWidth="sm"
      >
        <div className="flex items-center justify-end gap-2.5 pt-4">
          <Button variant="ghost" onClick={() => setDeleteConfirmOpen(false)}>
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
