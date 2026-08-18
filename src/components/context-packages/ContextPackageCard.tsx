import { useState } from "react";
import {
  Copy,
  Trash2,
  GitBranch,
  Clock,
  Check,
  Download,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { useContextPackageStore } from "@/stores/context-package-store";
import type { SavedContextPackage } from "@/lib/api";
import { toast } from "@/components/ui/toast";
import { motion, AnimatePresence } from "motion/react";

function formatRelativeTime(dateStr: string): string {
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
}

interface ContextPackageCardProps {
  pkg: SavedContextPackage;
  onCompareSelect?: (pkg: SavedContextPackage) => void;
  isCompareSelected?: boolean;
}

export function ContextPackageCard({ pkg, onCompareSelect, isCompareSelected }: ContextPackageCardProps) {
  const removePackage = useContextPackageStore((s) => s.removePackage);
  const [expanded, setExpanded] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(pkg.markdown);
      setCopied(true);
      toast.success("Package markdown copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    const blob = new Blob([pkg.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${pkg.name.replace(/[^a-zA-Z0-9_-]/g, "_")}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Downloaded package");
  };

  const handleDelete = async () => {
    await removePackage(pkg.id);
    setShowDeleteConfirm(false);
    toast.success("Package deleted");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg bg-[#0a0a0a] border transition-colors overflow-hidden ${
        isCompareSelected
          ? "border-white bg-[#0e0e0e]"
          : "border-[#1e1e1e] hover:border-[#2a2a2a]"
      }`}
    >
      <div className="p-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <h3 className="text-sm font-semibold text-white truncate">{pkg.name}</h3>
              <Badge
                variant="outline"
                className="shrink-0 text-[10px] font-mono"
              >
                ~{pkg.token_estimate.toLocaleString()} tokens
              </Badge>
              {pkg.tags && pkg.tags.map((t) => (
                <span key={t} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#121212] text-neutral-400 border border-[#222222]">
                  {t}
                </span>
              ))}
            </div>

            <p className="text-xs text-neutral-300 mb-2.5 line-clamp-2 leading-relaxed font-sans">
              {pkg.task}
            </p>

            <div className="flex items-center gap-3 text-xs font-mono text-neutral-500 flex-wrap">
              <span className="flex items-center gap-1.5 text-neutral-400">
                <GitBranch className="w-3 h-3 text-neutral-300" />
                <span>{pkg.repository_name}</span>
                <span className="text-neutral-600">/</span>
                <span className="text-neutral-500">{pkg.repository_branch || "main"}</span>
              </span>
              <span className="flex items-center gap-1 text-neutral-500">
                <Clock className="w-3 h-3" />
                <span>{formatRelativeTime(pkg.created_at)}</span>
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-start">
            {onCompareSelect && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onCompareSelect(pkg)}
                className={`h-7 px-2 text-xs cursor-pointer ${
                  isCompareSelected ? "bg-white text-black font-medium" : "border-[#222222] bg-[#0a0a0a] text-neutral-300 hover:text-white"
                }`}
              >
                <span>{isCompareSelected ? "Selected" : "Compare"}</span>
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="h-7 px-2 text-xs border-[#222222] bg-[#0a0a0a] text-neutral-300 hover:text-white gap-1 cursor-pointer"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="h-7 w-7 p-0 border-[#222222] bg-[#0a0a0a] text-neutral-300 hover:text-white cursor-pointer"
              title="Download Markdown"
              aria-label="Download Markdown"
            >
              <Download className="w-3 h-3" />
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              aria-label={expanded ? "Hide preview" : "Show preview"}
              className="h-7 px-2 text-xs border-[#222222] bg-[#0a0a0a] text-neutral-300 hover:text-white gap-1 cursor-pointer"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              <span>{expanded ? "Hide" : "Preview"}</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDeleteConfirm(true)}
              className="h-7 w-7 p-0 border-red-500/20 text-red-400 hover:bg-red-950/20 cursor-pointer"
              title="Delete Package"
              aria-label="Delete Package"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        </div>
      </div>

      {/* Expanded Markdown View */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-[#1a1a1a] bg-[#050505] p-4 font-mono text-xs text-neutral-300 max-h-96 overflow-y-auto leading-relaxed whitespace-pre-wrap selection:bg-white selection:text-black"
          >
            {pkg.markdown}
          </motion.div>
        )}
      </AnimatePresence>

      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Context Package"
        description="Are you sure you want to delete this saved context package? This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </motion.div>
  );
}
