import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  GitBranch,
  FolderOpen,
  Loader2,
  CheckCircle2,
  Clock,
  FileCode,
  FolderSearch,
  Sparkles,
} from "lucide-react";
import { IndexProgress } from "./IndexProgress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useRepositoryStore } from "@/stores/repository-store";

interface CreateRepositoryIndexModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateRepositoryIndexModal({
  open,
  onOpenChange,
}: CreateRepositoryIndexModalProps) {
  const navigate = useNavigate();
  const {
    createAndScan,
    indexRepo,
    scanning,
    indexing,
    lastScan,
    clearScan,
    progress,
    select,
    fetchRepositories,
  } = useRepositoryStore();

  const [sourceType, setSourceType] = useState<"github" | "local">("local");
  const [githubUrl, setGithubUrl] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [repoName, setRepoName] = useState("");
  const [datasetName, setDatasetName] = useState("");
  const [cloneIfMissing, setCloneIfMissing] = useState(true);
  const [keepSynced, setKeepSynced] = useState(false);
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdRepoId, setCreatedRepoId] = useState<string | null>(null);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setSourceType("local");
      setGithubUrl("");
      setLocalPath("");
      setRepoName("");
      setDatasetName("");
      setCloneIfMissing(true);
      setKeepSynced(false);
      setValidationErrors({});
      setSubmitting(false);
      setError(null);
      setCreatedRepoId(null);
      clearScan();
    }
  }, [open, clearScan]);

  // Auto-populate repo name from GitHub URL
  useEffect(() => {
    if (sourceType === "github" && githubUrl) {
      const segments = githubUrl.replace(/\/+$/, "").split("/");
      const lastSegment = segments[segments.length - 1];
      if (lastSegment && !repoName) {
        setRepoName(lastSegment);
      }
    }
  }, [githubUrl, sourceType, repoName]);

  const handleBrowseFolder = async () => {
    try {
      const { open: openDialog } = await import("@tauri-apps/plugin-dialog");
      const selected = await openDialog({
        directory: true,
        multiple: false,
        title: "Select Repository Folder",
      });
      if (selected) {
        const path = typeof selected === "string" ? selected : selected;
        setLocalPath(path);
        const segments = path.replace(/\/+$/, "").split("/");
        const folderName = segments[segments.length - 1];
        if (folderName) setRepoName(folderName);
      }
    } catch {
      setValidationErrors((prev) => ({
        ...prev,
        localPath: "Folder picker not available in browser mode",
      }));
    }
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (sourceType === "github") {
      if (!githubUrl.trim()) {
        errors.githubUrl = "GitHub URL is required";
      } else if (
        !githubUrl.match(/^https?:\/\/(github\.com|gitlab\.com|bitbucket\.org)\//)
      ) {
        errors.githubUrl = "Enter a valid repository URL";
      }
    } else {
      if (!localPath.trim()) {
        errors.localPath = "Local path is required. Click Browse to select a folder.";
      }
    }
    if (!repoName.trim()) {
      errors.repoName = "Repository name is required";
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    setSubmitting(true);
    setError(null);
    try {
      const repo = await createAndScan({
        source_type: sourceType,
        source_url: sourceType === "github" ? githubUrl : undefined,
        local_path: sourceType === "local" ? localPath : undefined,
        name: repoName,
      });
      setCreatedRepoId(repo.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create repository");
    } finally {
      setSubmitting(false);
    }
  };

  const handleIndexNow = async () => {
    if (!createdRepoId) return;
    setSubmitting(true);
    try {
      await indexRepo(createdRepoId);
    } catch {
      // error is handled and displayed by store
    } finally {
      setSubmitting(false);
    }
  };

  const handleDone = () => {
    onOpenChange(false);
    if (createdRepoId) {
      select(createdRepoId);
    }
    fetchRepositories();
    navigate("/");
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && progress?.status === "indexed") {
      if (createdRepoId) {
        select(createdRepoId);
      }
      fetchRepositories();
      navigate("/");
    }
    onOpenChange(nextOpen);
  };

  const isScanning = scanning;
  const isIndexing = indexing;
  const showScanResults = lastScan && createdRepoId;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[620px] bg-[#0a0a0a] text-white border border-[#262626] p-7 shadow-2xl rounded-2xl">
        <DialogHeader className="pb-4 border-b border-[#222222]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-black border border-[#2a2a2a] flex items-center justify-center text-white">
              <FolderSearch className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold text-white tracking-tight">
                Index Repository
              </DialogTitle>
              <DialogDescription className="text-xs font-mono text-neutral-400 mt-0.5">
                Parse AST trees, chunk definitions, and build semantic graph
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {error && (
          <div className="rounded-lg bg-red-950/40 border border-red-500/30 px-4 py-3 text-xs font-mono text-red-300">
            {error}
          </div>
        )}

        {!showScanResults ? (
          <div className="space-y-5 py-2">
            {/* High-Contrast Segmented Source Selector */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSourceType("local")}
                className={`flex items-center gap-3.5 p-3.5 rounded-xl border text-left transition-all ${
                  sourceType === "local"
                    ? "border-white bg-[#141414] text-white shadow-sm"
                    : "border-[#222222] bg-black text-neutral-400 hover:border-[#383838] hover:text-white"
                }`}
              >
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                    sourceType === "local"
                      ? "bg-white text-black font-bold"
                      : "bg-[#141414] text-neutral-400"
                  }`}
                >
                  <FolderOpen className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-medium text-white">Local Directory</p>
                  <p className="text-[11px] text-neutral-500">Browse disk</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setSourceType("github")}
                className={`flex items-center gap-3 p-2.5 rounded-md border text-left transition-colors cursor-pointer ${
                  sourceType === "github"
                    ? "border-white bg-[#141414] text-white shadow-xs"
                    : "border-[#222222] bg-[#050505] text-neutral-400 hover:border-[#383838] hover:text-white"
                }`}
              >
                <div
                  className={`w-7 h-7 rounded flex items-center justify-center ${
                    sourceType === "github"
                      ? "bg-white text-black font-bold"
                      : "bg-[#141414] text-neutral-400"
                  }`}
                >
                  <GitBranch className="w-3.5 h-3.5" />
                </div>
                <div>
                  <p className="text-xs font-medium text-white">Git Remote</p>
                  <p className="text-[11px] text-neutral-500">Clone via URL</p>
                </div>
              </button>
            </div>

            {/* Local Path Picker */}
            {sourceType === "local" && (
              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-300">
                  Folder Path
                </label>
                <div className="flex gap-2">
                  <Input
                    placeholder="/home/user/my-project"
                    value={localPath}
                    onChange={(e) => setLocalPath(e.target.value)}
                    className={`h-8 text-xs font-mono bg-[#050505] border-[#222222] text-neutral-200 placeholder:text-neutral-600 rounded-md focus-visible:ring-1 focus-visible:ring-white ${
                      validationErrors.localPath ? "border-red-500/80" : ""
                    }`}
                  />
                  <Button
                    type="button"
                    onClick={handleBrowseFolder}
                    className="shrink-0 h-8 px-3 text-xs font-medium bg-white text-black hover:bg-neutral-200 rounded-md cursor-pointer shadow-xs"
                  >
                    Browse...
                  </Button>
                </div>
                {validationErrors.localPath && (
                  <p className="text-xs text-red-400 font-mono mt-1">{validationErrors.localPath}</p>
                )}
              </div>
            )}

            {/* GitHub URL */}
            {sourceType === "github" && (
              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-300">
                  Repository URL
                </label>
                <Input
                  placeholder="https://github.com/organization/repository"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className={`h-8 text-xs font-mono bg-[#050505] border-[#222222] text-neutral-200 placeholder:text-neutral-600 rounded-md focus-visible:ring-1 focus-visible:ring-white ${
                    validationErrors.githubUrl ? "border-red-500/80" : ""
                  }`}
                />
                {validationErrors.githubUrl && (
                  <p className="text-xs text-red-400 font-mono mt-1">{validationErrors.githubUrl}</p>
                )}
              </div>
            )}

            {/* Repository Name & Dataset Name Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-300">
                  Repository Name
                </label>
                <Input
                  placeholder="re-track"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  className={`h-8 text-xs font-mono bg-[#050505] border-[#222222] text-neutral-200 placeholder:text-neutral-600 rounded-md focus-visible:ring-1 focus-visible:ring-white ${
                    validationErrors.repoName ? "border-red-500/80" : ""
                  }`}
                />
                {validationErrors.repoName && (
                  <p className="text-xs text-red-400 font-mono mt-1">{validationErrors.repoName}</p>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-neutral-400">
                  Dataset Tag <span className="text-neutral-500 font-normal">(optional)</span>
                </label>
                <Input
                  placeholder="defaults to repo name"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  className="h-8 text-xs font-mono bg-[#050505] border-[#222222] text-neutral-200 placeholder:text-neutral-600 rounded-md focus-visible:ring-1 focus-visible:ring-white"
                />
              </div>
            </div>

            {/* Checkboxes in clean dark card */}
            <div className="p-3 rounded-md bg-[#050505] border border-[#1e1e1e] flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-neutral-300">
                <Checkbox
                  checked={cloneIfMissing}
                  onCheckedChange={(checked) => setCloneIfMissing(checked === true)}
                  className="border-[#444444] data-[state=checked]:bg-white data-[state=checked]:text-black rounded"
                />
                <span>Clone if not local</span>
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer text-xs font-mono text-neutral-300">
                <Checkbox
                  checked={keepSynced}
                  onCheckedChange={(checked) => setKeepSynced(checked === true)}
                  className="border-[#444444] data-[state=checked]:bg-white data-[state=checked]:text-black"
                />
                <span>Auto-sync file changes</span>
              </label>
            </div>
          </div>
        ) : (
          /* Scan Results & Indexing Progress */
          <div className="space-y-5 py-2">
            {(isIndexing || progress?.status === "indexed" || progress?.status === "error") && createdRepoId ? (
              <IndexProgress
                repositoryName={repoName}
                repoId={createdRepoId}
              />
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-xl bg-black border border-[#262626] p-4 space-y-2">
                    <div className="flex items-center gap-2 mb-2">
                      <FileCode className="w-4 h-4 text-white" />
                      <span className="text-xs font-mono font-semibold text-neutral-300 uppercase tracking-wider">
                        Detected Languages
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {lastScan!.languages.length > 0 ? (
                        lastScan!.languages.map((lang) => (
                          <Badge
                            key={lang}
                            variant="secondary"
                            className="bg-[#141414] text-white border border-[#2a2a2a] text-xs font-mono"
                          >
                            {lang}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs font-mono text-neutral-500">
                          None detected
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl bg-black border border-[#262626] p-4 space-y-2">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-mono font-semibold text-neutral-300 uppercase tracking-wider">
                        Frameworks
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {lastScan!.frameworks.length > 0 ? (
                        lastScan!.frameworks.map((fw) => (
                          <Badge
                            key={fw}
                            variant="secondary"
                            className="bg-[#141414] text-neutral-200 border border-[#2a2a2a] text-xs font-mono"
                          >
                            {fw}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs font-mono text-neutral-500">
                          None detected
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="p-3.5 rounded-lg bg-black border border-[#222222] flex justify-between text-xs font-mono text-neutral-400">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-white" />
                    <span className="text-white font-bold">
                      {lastScan!.file_count.toLocaleString()}
                    </span>
                    <span>files scanned</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-white" />
                    <span>Est. index time:</span>
                    <span className="text-white font-bold">
                      ~{Math.ceil((lastScan!.estimated_index_time_ms ?? (lastScan!.file_count || 1) * 60) / 1000)}s
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        <DialogFooter className="pt-4 border-t border-[#222222] flex items-center justify-between">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            className="text-xs font-mono text-neutral-400 hover:text-white hover:bg-[#141414]"
          >
            Cancel
          </Button>
          {showScanResults ? (
            progress?.status === "indexed" ? (
              <Button
                type="button"
                onClick={handleDone}
                className="h-10 px-5 text-xs font-mono font-bold uppercase tracking-wider bg-white text-black hover:bg-neutral-200 rounded-lg shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4 mr-2 text-emerald-600" />
                Done
              </Button>
            ) : progress?.status === "error" ? (
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  className="h-10 px-4 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white rounded-lg"
                >
                  Dismiss
                </Button>
                <Button
                  type="button"
                  onClick={handleIndexNow}
                  className="h-10 px-4 text-xs font-mono font-bold uppercase tracking-wider bg-white text-black hover:bg-neutral-200 rounded-lg shadow-sm"
                >
                  Retry
                </Button>
              </div>
            ) : (
              <Button
                type="button"
                onClick={handleIndexNow}
                disabled={submitting || isIndexing}
                className="h-10 px-5 text-xs font-mono font-bold uppercase tracking-wider bg-white text-black hover:bg-neutral-200 rounded-lg shadow-sm"
              >
                {isIndexing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Indexing AST...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Index Now
                  </>
                )}
              </Button>
            )
          ) : (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || isScanning}
              className="h-10 px-5 text-xs font-mono font-bold uppercase tracking-wider bg-white text-black hover:bg-neutral-200 rounded-lg shadow-sm"
            >
              {isScanning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Scanning Files...
                </>
              ) : submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                "Scan & Index"
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
