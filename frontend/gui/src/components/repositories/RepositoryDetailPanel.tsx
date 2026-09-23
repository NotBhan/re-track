import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Trash2,
  FolderGit2,
  Code,
  Layers,
  Package,
  FileText,
  GitBranch,
  Zap,
} from "lucide-react";
import { useRepositoryStore } from "@/stores/repository-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReindexModal } from "./ReindexModal";
import { QuickContextModal } from "./QuickContextModal";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export function RepositoryDetailPanel() {
  const { selected, select, indexRepo, removeRepo } = useRepositoryStore();
  const navigate = useNavigate();
  const [showReindexModal, setShowReindexModal] = useState(false);
  const [showQuickContext, setShowQuickContext] = useState(false);

  if (!selected) {
    return (
      <aside className="w-full h-full bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] flex flex-col items-center justify-center p-6 text-center min-h-0">
        <div className="w-10 h-10 rounded-lg bg-[#0f0f0f] border border-[#222222] flex items-center justify-center mb-3 text-neutral-400">
          <GitBranch className="w-5 h-5 text-neutral-300" />
        </div>
        <h4 className="text-sm font-semibold text-white tracking-tight">No Repository Selected</h4>
        <p className="text-xs text-neutral-500 mt-1 max-w-xs leading-relaxed">
          Select any workspace card from the catalog to inspect file statistics, architecture details, and synthesize context.
        </p>
      </aside>
    );
  }

  return (
    <aside className="w-full h-full bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] flex flex-col overflow-hidden min-h-0">
      {/* Header */}
      <div className="p-4 border-b border-[#1a1a1a] flex items-start justify-between gap-3 bg-[#080808] shrink-0">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-white tracking-tight truncate">
              {selected.name}
            </h3>
            <Badge
              variant={
                selected.status === "indexed"
                  ? "success"
                  : selected.status === "error"
                  ? "destructive"
                  : "outline"
              }
              className="text-[10px] font-mono uppercase px-1.5 py-0"
            >
              {selected.status}
            </Badge>
          </div>
          <p className="font-mono text-xs text-neutral-500 truncate" title={selected.local_path}>
            {selected.local_path}
          </p>
        </div>

        <button
          onClick={() => select(null)}
          aria-label="Close detail panel"
          title="Close detail panel"
          className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-[#141414] transition-colors shrink-0 cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Action Bar */}
      <div className="px-4 py-2.5 border-b border-[#1a1a1a] bg-[#0a0a0a] flex items-center gap-2 shrink-0 flex-wrap">
        <Button
          size="sm"
          onClick={() => setShowQuickContext(true)}
          className="h-7.5 px-2.5 text-xs bg-[#141414] border border-[#262626] text-neutral-200 hover:text-white gap-1.5 transition-colors cursor-pointer"
        >
          <Zap className="w-3 h-3 text-amber-400 fill-amber-400" />
          <span>Quick Context</span>
        </Button>

        <Button
          size="sm"
          onClick={() => navigate(`/studio?repo=${selected.id}`)}
          className="h-7.5 px-3 text-xs bg-white text-black font-medium hover:bg-neutral-200 gap-1 shadow-xs cursor-pointer"
        >
          <Sparkles className="w-3 h-3" />
          <span>Studio</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/knowledge/${selected.id}`)}
          className="h-7.5 px-2.5 text-xs border-[#222222] bg-[#0a0a0a] text-neutral-300 hover:text-white hover:bg-[#141414] gap-1 cursor-pointer"
        >
          <ExternalLink className="w-3 h-3" />
          <span>Knowledge</span>
        </Button>
      </div>

      {/* Scrollable Body with Clean Divided Sections */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 divide-y divide-[#141414] [&>*:not(:first-child)]:pt-4">
        {/* Project Overview */}
        {selected.summary && (
          <div>
            <h4 className="flex items-center gap-1.5 text-xs font-semibold text-neutral-200 mb-1.5 tracking-tight">
              <FileText className="w-3.5 h-3.5 text-neutral-400" />
              <span>Project Overview</span>
            </h4>
            <p className="text-xs text-neutral-400 leading-relaxed font-sans">
              {selected.summary}
            </p>
          </div>
        )}

        {/* Compact Key-Value Metadata Grid */}
        <div>
          <h4 className="text-xs font-semibold text-neutral-200 mb-2 tracking-tight">
            Repository Metrics
          </h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs font-mono">
            <div className="flex items-center justify-between border-b border-[#141414] pb-1">
              <span className="text-neutral-500">File Count</span>
              <span className="text-neutral-200 font-medium">{selected.file_count.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between border-b border-[#141414] pb-1">
              <span className="text-neutral-500">Total Size</span>
              <span className="text-neutral-200 font-medium">{formatBytes(selected.size_bytes)}</span>
            </div>
            <div className="flex items-center justify-between border-b border-[#141414] pb-1">
              <span className="text-neutral-500">Status</span>
              <span className="capitalize text-neutral-200 font-medium">{selected.status}</span>
            </div>
            <div className="flex items-center justify-between border-b border-[#141414] pb-1">
              <span className="text-neutral-500">Source</span>
              <span className="capitalize text-neutral-200 font-medium">{selected.source_type || "Local"}</span>
            </div>
          </div>
        </div>

        {/* Languages Detected */}
        {selected.languages && selected.languages.length > 0 && (
          <div>
            <h4 className="flex items-center gap-1.5 text-xs font-semibold text-neutral-200 mb-2 tracking-tight">
              <Code className="w-3.5 h-3.5 text-neutral-400" />
              <span>Languages</span>
            </h4>
            <div className="flex flex-wrap gap-1">
              {selected.languages.map((lang) => (
                <span
                  key={lang}
                  className="text-[11px] font-mono text-neutral-300 bg-[#0c0c0c] border border-[#222222] px-2 py-0.5 rounded"
                >
                  {lang}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Frameworks & Libraries */}
        {selected.frameworks && selected.frameworks.length > 0 && (
          <div>
            <h4 className="flex items-center gap-1.5 text-xs font-semibold text-neutral-200 mb-2 tracking-tight">
              <Package className="w-3.5 h-3.5 text-neutral-400" />
              <span>Frameworks &amp; Dependencies</span>
            </h4>
            <div className="flex flex-wrap gap-1">
              {selected.frameworks.map((fw) => (
                <span
                  key={fw}
                  className="text-[11px] font-mono text-neutral-300 bg-[#0c0c0c] border border-[#222222] px-2 py-0.5 rounded"
                >
                  {fw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Discovered Entry Points */}
        {selected.entry_points && selected.entry_points.length > 0 && (
          <div>
            <h4 className="flex items-center gap-1.5 text-xs font-semibold text-neutral-200 mb-2 tracking-tight">
              <FolderGit2 className="w-3.5 h-3.5 text-neutral-400" />
              <span>Entry Points</span>
            </h4>
            <ul className="space-y-1 font-mono text-xs text-neutral-300">
              {selected.entry_points.map((ep) => (
                <li key={ep} className="flex items-center gap-2 truncate" title={ep}>
                  <span className="w-1 h-1 rounded-full bg-neutral-500 shrink-0" />
                  <span className="truncate text-[11px] text-neutral-400">{ep}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Key Architectural Components */}
        {selected.components && selected.components.length > 0 && (
          <div>
            <h4 className="flex items-center gap-1.5 text-xs font-semibold text-neutral-200 mb-2 tracking-tight">
              <Layers className="w-3.5 h-3.5 text-neutral-400" />
              <span>Key Components</span>
            </h4>
            <div className="flex flex-wrap gap-1">
              {selected.components.map((comp) => (
                <span
                  key={comp}
                  className="text-[11px] font-mono text-neutral-300 bg-[#0c0c0c] border border-[#222222] px-2 py-0.5 rounded"
                >
                  {comp}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Utility Actions */}
      <div className="p-3 border-t border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-2 shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            indexRepo(selected.id);
            setShowReindexModal(true);
          }}
          className="h-7 text-xs border-[#222222] bg-[#0a0a0a] text-neutral-300 hover:text-white gap-1 cursor-pointer"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Re-index</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => removeRepo(selected.id)}
          className="h-7 text-xs border-red-500/20 text-red-400 hover:bg-red-950/20 gap-1 cursor-pointer"
        >
          <Trash2 className="w-3 h-3" />
          <span>Delete</span>
        </Button>
      </div>

      {/* Reindex Modal */}
      <ReindexModal
        repoId={selected.id}
        open={showReindexModal}
        onOpenChange={setShowReindexModal}
      />

      {/* Quick Context Modal */}
      <QuickContextModal
        repo={selected}
        open={showQuickContext}
        onOpenChange={setShowQuickContext}
      />
    </aside>
  );
}
