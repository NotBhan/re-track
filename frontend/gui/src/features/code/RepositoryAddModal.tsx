import React, { useState } from "react";
import { Folder, GitBranch, AlertCircle } from "lucide-react";
import { Dialog } from "../../components/Dialog";
import { Button } from "../../components/Button";
import { Input } from "../../components/Input";
import { useRepositoryStore } from "../../stores/repositoryStore";
import { toast } from "../..//app/providers/ToastProvider";

interface RepositoryAddModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const RepositoryAddModal: React.FC<RepositoryAddModalProps> = ({ open, onOpenChange }) => {
  const [sourceType, setSourceType] = useState<"local" | "github">("local");
  const [localPath, setLocalPath] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [repoName, setRepoName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { createAndScan } = useRepositoryStore();

  const handleBrowseFolder = async () => {
    try {
      // Use Tauri dialog plugin if available
      const { open: openDialog } = await import("@tauri-apps/plugin-dialog");
      const selected = await openDialog({
        directory: true,
        multiple: false,
        title: "Select Repository Directory",
      });

      if (selected && typeof selected === "string") {
        setLocalPath(selected);
        const folderName = selected.split(/[/\\]/).filter(Boolean).pop();
        if (folderName && !repoName) {
          setRepoName(folderName);
        }
      }
    } catch (e) {
      console.warn("Folder picker unavailable or cancelled:", e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (sourceType === "local" && !localPath.trim()) {
      setError("Please specify a local directory path.");
      return;
    }
    if (sourceType === "github" && !githubUrl.trim()) {
      setError("Please enter a GitHub repository URL.");
      return;
    }

    setLoading(true);
    try {
      const finalName = repoName.trim() || (sourceType === "local" ? localPath.split("/").pop() : githubUrl.split("/").pop()) || "repository";
      await createAndScan({
        source_type: sourceType,
        local_path: sourceType === "local" ? localPath.trim() : undefined,
        source_url: sourceType === "github" ? githubUrl.trim() : undefined,
        name: finalName,
      });

      toast.success(`Repository "${finalName}" added and scanned`);
      onOpenChange(false);
      setLocalPath("");
      setGithubUrl("");
      setRepoName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add repository");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Add Repository"
      description="Track and index a local codebase or remote repository into RE:Track."
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Source Type Selector */}
        <div className="flex p-1 bg-white/[0.03] border border-white/[0.06] rounded-lg">
          <button
            type="button"
            onClick={() => setSourceType("local")}
            className={`flex-1 flex items-center justify-center gap-2 py-1.5 rounded-md text-xs font-medium transition-all ${
              sourceType === "local"
                ? "bg-white/[0.1] text-white shadow-xs"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Folder className="w-3.5 h-3.5" />
            <span>Local Directory</span>
          </button>
          <button
            type="button"
            onClick={() => setSourceType("github")}
            className={`flex-1 flex items-center justify-center gap-2 py-1.5 rounded-md text-xs font-medium transition-all ${
              sourceType === "github"
                ? "bg-white/[0.1] text-white shadow-xs"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>GitHub URL</span>
          </button>
        </div>

        {/* Path / URL input */}
        {sourceType === "local" ? (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-300">Directory Path</label>
            <div className="flex gap-2">
              <Input
                placeholder="/path/to/project"
                value={localPath}
                onChange={(e) => {
                  setLocalPath(e.target.value);
                  const folder = e.target.value.split(/[/\\]/).filter(Boolean).pop();
                  if (folder && !repoName) setRepoName(folder);
                }}
              />
              <Button type="button" variant="secondary" onClick={handleBrowseFolder}>
                Browse
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-300">GitHub Repository URL</label>
            <Input
              placeholder="https://github.com/owner/repository.git"
              value={githubUrl}
              onChange={(e) => {
                setGithubUrl(e.target.value);
                const name = e.target.value.replace(/\.git$/, "").split("/").pop();
                if (name && !repoName) setRepoName(name);
              }}
            />
          </div>
        )}

        {/* Repository Name override */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-slate-300">Display Name</label>
          <Input
            placeholder="e.g. my-project"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-lg text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Add & Scan
          </Button>
        </div>
      </form>
    </Dialog>
  );
};
