import React, { useState } from "react";
import {
  FolderGit2,
  RefreshCw,
  Trash2,
  Search,
  Network,
  FileText,
  Plus,
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

interface RepositoryCatalogProps {
  onOpenAddModal: () => void;
}

export const RepositoryCatalog: React.FC<RepositoryCatalogProps> = ({ onOpenAddModal }) => {
  const {
    repositories,
    selectedRepo,
    indexing,
    progress,
    indexRepo,
    scanRepo,
    deleteRepo,
    scanning,
  } = useRepositoryStore();

  const [activeTab, setActiveTab] = useState<"graph" | "manifest">("graph");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // If no repository is registered, show clean initial launch state (Journey A)
  if (!selectedRepo && repositories.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <EmptyState
          icon={<FolderGit2 className="w-8 h-8 text-sky-400" />}
          title="No Repositories Tracked"
          description="Add a local codebase or Git repository to explore its AST call graph, generate developer context, and build semantic memory."
          action={
            <Button onClick={onOpenAddModal} size="md">
              <Plus className="w-4 h-4 mr-1.5" />
              Add Repository
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
      toast.success(`Repository "${selectedRepo.name}" removed`);
      setDeleteConfirmOpen(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete repository");
    } finally {
      setDeleting(false);
    }
  };

  const isIndexed = selectedRepo?.status === "indexed" || selectedRepo?.indexed_at;

  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
      {/* Repository Header: Name, path, branch, actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-white/[0.06]">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold tracking-tight text-slate-100">
              {selectedRepo?.name}
            </h2>
            <Badge variant={isIndexed ? "success" : "default"}>
              {selectedRepo?.status || "registered"}
            </Badge>
            {selectedRepo?.branch && (
              <span className="text-xs font-mono text-slate-400">
                branch: {selectedRepo.branch}
              </span>
            )}
          </div>
          <div className="text-xs text-slate-400 font-mono mt-1 break-all">
            {selectedRepo?.local_path}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
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
            loading={indexing}
            onClick={() => selectedRepo && indexRepo(selectedRepo.id)}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{isIndexed ? "Re-index" : "Index Repository"}</span>
          </Button>

          <Button
            size="sm"
            variant="danger"
            onClick={() => setDeleteConfirmOpen(true)}
            title="Delete repository"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Real-time Indexing Progress View */}
      {indexing && progress && <IndexingProgressView progress={progress} />}

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
            onAnalyze={() => selectedRepo && indexRepo(selectedRepo.id)}
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
        description="This will remove the repository from RE:Track workspace. Stored memory records for this dataset will also be cleared. Source files on disk will NOT be touched."
        maxWidth="sm"
      >
        <div className="flex items-center justify-end gap-2.5 pt-4">
          <Button variant="ghost" onClick={() => setDeleteConfirmOpen(false)}>
            Cancel
          </Button>
          <Button variant="danger" loading={deleting} onClick={handleDelete}>
            Confirm Delete
          </Button>
        </div>
      </Dialog>
    </div>
  );
};
