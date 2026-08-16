import { useState, useEffect } from "react";
import {
  GitBranch,
  FolderOpen,
  Loader2,
  CheckCircle2,
  Clock,
  FileCode,
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
  const { createAndScan, indexRepo, scanning, indexing, lastScan, clearScan } =
    useRepositoryStore();

  const [sourceType, setSourceType] = useState<"github" | "local">("github");
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
  const [indexingStarted, setIndexingStarted] = useState(false);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setIndexingStarted(false);
      setSourceType("github");
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
  }, [githubUrl, sourceType]);

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
        localPath: "Folder picker not available",
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
        errors.localPath = "Local path is required";
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
    setIndexingStarted(true);
    try {
      await indexRepo(createdRepoId);
    } catch {
      // error is set by store
    } finally {
      setSubmitting(false);
    }
  };

  // Auto-close modal 1s after indexing completes
  useEffect(() => {
    if (indexingStarted && !indexing && !error) {
      const timer = setTimeout(() => onOpenChange(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [indexingStarted, indexing, error, onOpenChange]);

  const isScanning = scanning;
  const isIndexing = indexing;
  const showScanResults = lastScan && createdRepoId;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[780px] bg-surface-container text-on-surface border-outline-variant">
        <DialogHeader>
          <DialogTitle className="text-on-surface text-xl font-semibold">
            Create Repository Index
          </DialogTitle>
          <DialogDescription className="text-on-surface-variant text-sm">
            Add a repository to RE:Track (RefinedEngine Track) and build its knowledge index
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="rounded-md bg-error/10 border border-error/30 px-4 py-3 text-sm text-error">
            {error}
          </div>
        )}

        {!showScanResults ? (
          <div className="space-y-5">
            {/* Source Type Selection */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSourceType("github")}
                className={`flex items-center gap-3 p-4 rounded-lg border-2 transition-all text-left ${
                  sourceType === "github"
                    ? "border-primary bg-primary/5"
                    : "border-outline-variant bg-surface-container-lowest hover:border-outline"
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    sourceType === "github"
                      ? "bg-primary/10"
                      : "bg-surface-container-high"
                  }`}
                >
                  <GitBranch
                    className={`w-5 h-5 ${
                      sourceType === "github"
                        ? "text-primary"
                        : "text-on-surface-variant"
                    }`}
                  />
                </div>
                <div>
                  <p className="text-sm font-medium text-on-surface">
                    GitHub Repository
                  </p>
                  <p className="text-xs text-on-surface-variant">
                    Clone from URL
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setSourceType("local")}
                className={`flex items-center gap-3 p-4 rounded-lg border-2 transition-all text-left ${
                  sourceType === "local"
                    ? "border-primary bg-primary/5"
                    : "border-outline-variant bg-surface-container-lowest hover:border-outline"
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    sourceType === "local"
                      ? "bg-primary/10"
                      : "bg-surface-container-high"
                  }`}
                >
                  <FolderOpen
                    className={`w-5 h-5 ${
                      sourceType === "local"
                        ? "text-primary"
                        : "text-on-surface-variant"
                    }`}
                  />
                </div>
                <div>
                  <p className="text-sm font-medium text-on-surface">
                    Local Repository
                  </p>
                  <p className="text-xs text-on-surface-variant">
                    Browse local folder
                  </p>
                </div>
              </button>
            </div>

            {/* GitHub URL */}
            {sourceType === "github" && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-on-surface">
                  Repository URL
                </label>
                <Input
                  placeholder="https://github.com/user/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className={`bg-surface-container-lowest border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 ${
                    validationErrors.githubUrl
                      ? "border-error focus-visible:ring-error/50"
                      : ""
                  }`}
                />
                {validationErrors.githubUrl && (
                  <p className="text-xs text-error">{validationErrors.githubUrl}</p>
                )}
              </div>
            )}

            {/* Local Path */}
            {sourceType === "local" && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-on-surface">
                  Folder Path
                </label>
                <div className="flex gap-2">
                  <Input
                    placeholder="/path/to/repository"
                    value={localPath}
                    readOnly
                    className={`bg-surface-container-lowest border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 ${
                      validationErrors.localPath
                        ? "border-error focus-visible:ring-error/50"
                        : ""
                    }`}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleBrowseFolder}
                    className="shrink-0 border-outline-variant text-on-surface hover:bg-surface-container-high"
                  >
                    Browse
                  </Button>
                </div>
                {validationErrors.localPath && (
                  <p className="text-xs text-error">{validationErrors.localPath}</p>
                )}
              </div>
            )}

            {/* Repository Name */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-on-surface">
                Repository Name
              </label>
              <Input
                placeholder="my-repository"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                className={`bg-surface-container-lowest border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 ${
                  validationErrors.repoName
                    ? "border-error focus-visible:ring-error/50"
                    : ""
                }`}
              />
              {validationErrors.repoName && (
                <p className="text-xs text-error">{validationErrors.repoName}</p>
              )}
            </div>

            {/* Dataset Name */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-on-surface">
                Dataset Name{" "}
                <span className="text-on-surface-variant font-normal">
                  (optional)
                </span>
              </label>
              <Input
                placeholder="defaults to repository name"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                className="bg-surface-container-lowest border-outline-variant text-on-surface placeholder:text-on-surface-variant/50"
              />
            </div>

            {/* Checkboxes */}
            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={cloneIfMissing}
                  onCheckedChange={(checked) =>
                    setCloneIfMissing(checked === true)
                  }
                />
                <span className="text-sm text-on-surface">Clone if not local</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <Checkbox
                  checked={keepSynced}
                  onCheckedChange={(checked) => setKeepSynced(checked === true)}
                />
                <span className="text-sm text-on-surface">Keep synchronized</span>
              </label>
            </div>
          </div>
        ) : (
          /* Scan Results */
          <div className="space-y-5">
            {isIndexing && createdRepoId && (
              <IndexProgress
                repositoryName={repoName}
                repoId={createdRepoId}
              />
            )}
            {!isIndexing && (
              <>
                {/* Languages and Frameworks cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg bg-surface-container-lowest border border-outline-variant p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <FileCode className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium text-on-surface">
                        Languages
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {lastScan!.languages.length > 0 ? (
                        lastScan!.languages.map((lang) => (
                          <Badge
                            key={lang}
                            variant="secondary"
                            className="bg-primary/10 text-primary border-primary/20"
                          >
                            {lang}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-on-surface-variant">
                          No languages detected
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="rounded-lg bg-surface-container-lowest border border-outline-variant p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <CheckCircle2 className="w-4 h-4 text-primary" />
                      <span className="text-sm font-medium text-on-surface">
                        Frameworks
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {lastScan!.frameworks.length > 0 ? (
                        lastScan!.frameworks.map((fw) => (
                          <Badge
                            key={fw}
                            variant="secondary"
                            className="bg-secondary/10 text-secondary border-secondary/20"
                          >
                            {fw}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-xs text-on-surface-variant">
                          No frameworks detected
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex gap-6 text-sm text-on-surface-variant">
                  <div className="flex items-center gap-1.5">
                    <FileCode className="w-4 h-4" />
                    <span>
                      {lastScan!.file_count.toLocaleString()} files
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4" />
                    <span>
                      ~{Math.ceil(lastScan!.estimated_index_time_ms / 1000)}s estimated
                      indexing time
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            className="text-on-surface-variant hover:text-on-surface"
          >
            Cancel
          </Button>
          {showScanResults ? (
            <Button
              type="button"
              onClick={handleIndexNow}
              disabled={submitting || isIndexing}
              className="bg-primary text-on-primary hover:bg-primary/90"
            >
              {isIndexing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Indexing...
                </>
              ) : (
                "Index Now"
              )}
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || isScanning}
              className="bg-primary text-on-primary hover:bg-primary/90"
            >
              {isScanning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Scanning...
                </>
              ) : submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Index"
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
