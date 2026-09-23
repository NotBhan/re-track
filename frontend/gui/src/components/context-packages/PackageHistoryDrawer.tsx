import { useEffect, useMemo, useState } from "react";
import {
  History,
  Copy,
  Download,
  Trash2,
  GitBranch,
  Clock,
  Check,
  X,
  ChevronRight,
  Bookmark,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useContextPackageStore } from "@/stores/context-package-store";
import type { SavedContextPackage } from "@/lib/api";
import { toast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

interface PackageHistoryDrawerProps {
  activeRepoId: string | null;
  activeRepoName?: string;
  onSelectPackage?: (pkg: SavedContextPackage) => void;
  onClose?: () => void;
  className?: string;
}

function formatRelativeTime(dateStr: string): string {
  try {
    const now = Date.now();
    const then = new Date(dateStr).getTime();
    const diffMs = now - then;
    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days === 1) return "yesterday";
    return `${days}d ago`;
  } catch {
    return dateStr;
  }
}

export function PackageHistoryDrawer({
  activeRepoId,
  activeRepoName,
  onSelectPackage,
  onClose,
  className,
}: PackageHistoryDrawerProps) {
  const packages = useContextPackageStore((s) => s.packages);
  const fetchPackages = useContextPackageStore((s) => s.fetchPackages);
  const removePackage = useContextPackageStore((s) => s.removePackage);

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  // Scoped strictly to the active repository
  const repoPackages = useMemo(() => {
    if (!activeRepoId && !activeRepoName) return [];
    return packages.filter((p) => {
      if (activeRepoId && p.repository_id === activeRepoId) return true;
      if (activeRepoName && p.repository_name === activeRepoName) return true;
      return false;
    });
  }, [packages, activeRepoId, activeRepoName]);

  const handleCopy = async (pkg: SavedContextPackage, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(pkg.markdown);
      setCopiedId(pkg.id);
      toast.success("Package markdown copied to clipboard");
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      toast.error("Failed to copy markdown");
    }
  };

  const handleDownload = (pkg: SavedContextPackage, e: React.MouseEvent) => {
    e.stopPropagation();
    const blob = new Blob([pkg.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${pkg.name.replace(/[^a-zA-Z0-9_-]/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Downloaded package markdown");
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await removePackage(id);
    toast.success("Package deleted from library");
  };

  return (
    <div className={cn("flex flex-col h-full bg-[#0a0a0a] border-l border-[#1e1e1e] font-sans", className)}>
      {/* Header */}
      <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-neutral-300" />
          <h3 className="text-xs font-semibold text-white tracking-tight">Package History</h3>
          <Badge variant="outline" className="text-[10px] font-mono">
            {repoPackages.length} {repoPackages.length === 1 ? "package" : "packages"}
          </Badge>
        </div>

        {onClose && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-7 w-7 p-0 text-neutral-400 hover:text-white hover:bg-[#1a1a1a] cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </Button>
        )}
      </div>

      {/* Repository Scope Indicator */}
      <div className="px-3 py-2 bg-[#050505] border-b border-[#141414] flex items-center justify-between text-[11px] font-mono text-neutral-400">
        <div className="flex items-center gap-1.5 truncate">
          <GitBranch className="w-3 h-3 text-neutral-500 shrink-0" />
          <span className="text-neutral-500">Repository:</span>
          <span className="text-neutral-200 font-medium truncate">{activeRepoName || activeRepoId || "None"}</span>
        </div>
        <span className="text-[10px] text-neutral-500 shrink-0">Scoped</span>
      </div>

      {/* Package List */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2.5">
        {repoPackages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center">
            <div className="w-10 h-10 rounded-lg bg-[#0f0f0f] border border-[#222222] flex items-center justify-center mb-2 text-neutral-400">
              <Bookmark className="w-4 h-4 text-neutral-500" />
            </div>
            <h4 className="text-xs font-semibold text-neutral-300">
              No saved packages for this repository
            </h4>
            <p className="text-[11px] text-neutral-500 mt-1 max-w-xs leading-relaxed">
              Synthesize a context package and click &ldquo;Save&rdquo; to build a reusable prompt and package history.
            </p>
          </div>
        ) : (
          repoPackages.map((pkg) => {
            const isCopied = copiedId === pkg.id;
            const isSelected = selectedId === pkg.id;

            return (
              <div
                key={pkg.id}
                onClick={() => {
                  setSelectedId(pkg.id);
                  if (onSelectPackage) onSelectPackage(pkg);
                }}
                className={cn(
                  "rounded-lg p-3 border transition-colors cursor-pointer text-left space-y-2",
                  isSelected
                    ? "bg-[#141414] border-neutral-400"
                    : "bg-[#060606] border-[#1c1c1c] hover:border-[#2a2a2a] hover:bg-[#0c0c0c]"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <h4 className="text-xs font-semibold text-white truncate">{pkg.name}</h4>
                    <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-neutral-400">
                      <span className="text-neutral-300 font-medium">
                        ~{(pkg.token_estimate || 0).toLocaleString()} tokens
                      </span>
                      <span className="text-neutral-600">·</span>
                      <span className="flex items-center gap-1 text-neutral-500">
                        <Clock className="w-3 h-3" />
                        <span>{formatRelativeTime(pkg.created_at)}</span>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={(e) => handleCopy(pkg, e)}
                      className="h-6 w-6 p-0 text-neutral-400 hover:text-white hover:bg-[#1a1a1a]"
                      title="Copy Markdown"
                    >
                      {isCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={(e) => handleDownload(pkg, e)}
                      className="h-6 w-6 p-0 text-neutral-400 hover:text-white hover:bg-[#1a1a1a]"
                      title="Download Markdown"
                    >
                      <Download className="w-3 h-3" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={(e) => handleDelete(pkg.id, e)}
                      className="h-6 w-6 p-0 text-neutral-400 hover:text-red-400 hover:bg-red-950/20"
                      title="Delete Package"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>

                {pkg.task && (
                  <p className="text-[11px] text-neutral-400 line-clamp-2 leading-relaxed">
                    {pkg.task}
                  </p>
                )}

                <div className="flex items-center justify-between pt-1 border-t border-[#141414] text-[10px] font-mono">
                  <div className="flex flex-wrap gap-1">
                    {pkg.tags &&
                      pkg.tags.map((t) => (
                        <span
                          key={t}
                          className="px-1.5 py-0.2 rounded bg-[#101010] border border-[#222] text-neutral-400"
                        >
                          {t}
                        </span>
                      ))}
                  </div>

                  <span className="text-neutral-400 hover:text-white flex items-center gap-0.5">
                    <span>Load in Studio</span>
                    <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
