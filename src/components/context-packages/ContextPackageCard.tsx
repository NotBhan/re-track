import { useState } from "react";
import {
  Copy,
  Trash2,
  GitBranch,
  Clock,
  Hash,
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
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl bg-[#0a0a0a] border transition-all shadow-md overflow-hidden ${
        isCompareSelected
          ? "border-white shadow-[0_0_16px_rgba(255,255,255,0.08)] bg-[#0e0e0e]"
          : "border-[#262626] hover:border-[#404040]"
      }`}
    >
      <div className="p-5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2.5 mb-2 flex-wrap">
              <h3 className="text-base font-bold text-white truncate">{pkg.name}</h3>
              <Badge
                variant="outline"
                className="shrink-0 text-[10px] font-mono border-[#333333] bg-black text-neutral-300"
              >
                <Hash className="w-3 h-3 mr-1 text-neutral-500" />
                ~{pkg.token_estimate.toLocaleString()} tokens
              </Badge>
              {pkg.tags && pkg.tags.map((t) => (
                <span key={t} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-900 text-neutral-400 border border-neutral-800">
                  {t}
                </span>
              ))}
            </div>

            <p className="text-xs font-mono text-neutral-300 mb-3 line-clamp-2 leading-relaxed">
              {pkg.task}
            </p>

            <div className="flex items-center gap-4 text-xs font-mono text-neutral-500 flex-wrap">
              <span className="flex items-center gap-1.5 text-neutral-400">
                <GitBranch className="w-3.5 h-3.5 text-white" />
                {pkg.repository_name}
                <span className="text-neutral-600">/</span>
                {pkg.repository_branch || "main"}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {formatRelativeTime(pkg.created_at)}
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
                className={`h-8 px-2.5 text-xs font-mono border-[#333] cursor-pointer ${
                  isCompareSelected ? "bg-white text-black font-semibold" : "bg-black text-neutral-300 hover:text-white"
                }`}
              >
                <span>{isCompareSelected ? "Selected" : "Compare"}</span>
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="h-8 px-2.5 text-xs font-mono border-[#333] bg-black text-neutral-300 hover:text-white gap-1 cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="h-8 w-8 p-0 border-[#333] bg-black text-neutral-300 hover:text-white cursor-pointer"
              title="Download Markdown"
            >
              <Download className="w-3.5 h-3.5" />
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="h-8 px-2.5 text-xs font-mono border-[#333] bg-black text-neutral-300 hover:text-white gap-1 cursor-pointer"
            >
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              <span>{expanded ? "Hide" : "Preview"}</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDeleteConfirm(true)}
              className="h-8 w-8 p-0 border-red-500/20 text-red-400 hover:bg-red-500/10 cursor-pointer"
              title="Delete Package"
            >
              <Trash2 className="w-3.5 h-3.5" />
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
            className="border-t border-[#262626] bg-black p-5 font-mono text-xs text-neutral-300 max-h-96 overflow-y-auto leading-relaxed whitespace-pre-wrap selection:bg-white selection:text-black"
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
