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

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="flex items-center gap-1.5 text-xs font-medium text-neutral-300">
        <Icon className="w-3.5 h-3.5 text-neutral-400" />
        <span>{title}</span>
      </h4>
      <div className="bg-[#050505] p-3 rounded-lg border border-[#1a1a1a]">
        {children}
      </div>
    </div>
  );
}

function TagList({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((item) => (
        <span
          key={item}
          className="text-xs font-mono text-neutral-300 bg-[#121212] border border-[#222222] px-2 py-0.5 rounded"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function FileList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5 font-mono text-xs text-neutral-300">
      {items.map((item) => (
        <li key={item} className="flex items-center gap-2 truncate">
          <span className="w-1 h-1 rounded-full bg-neutral-500 shrink-0" />
          <span className="truncate">{item}</span>
        </li>
      ))}
    </ul>
  );
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
          Select any workspace card from the catalog to inspect AST call graphs, file statistics, and synthesize context.
        </p>
      </aside>
    );
  }

  const callNodesCount = Array.isArray(selected.metadata?.call_graph_nodes)
    ? selected.metadata.call_graph_nodes.length
    : 0;

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
          <p className="font-mono text-xs text-neutral-500 truncate">
            {selected.local_path}
          </p>
        </div>

        <button
          onClick={() => select(null)}
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

      {/* Scrollable Body */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
        {/* Purpose / Summary */}
        {selected.summary && (
          <Section icon={FileText} title="Project Overview">
            <p className="text-xs text-neutral-300 leading-relaxed font-sans">
              {selected.summary}
            </p>
          </Section>
        )}

        {/* Telemetry Stats Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div className="bg-[#050505] p-2.5 rounded-lg border border-[#1a1a1a]">
            <span className="text-[10px] text-neutral-500 block mb-0.5">
              Total Files
            </span>
            <span className="text-xs font-semibold text-white">
              {selected.file_count.toLocaleString()}
            </span>
          </div>

          <div className="bg-[#050505] p-2.5 rounded-lg border border-[#1a1a1a]">
            <span className="text-[10px] text-neutral-500 block mb-0.5">
              Total Size
            </span>
            <span className="text-xs font-semibold text-white">
              {formatBytes(selected.size_bytes)}
            </span>
          </div>

          <div className="bg-[#050505] p-2.5 rounded-lg border border-[#1a1a1a]">
            <span className="text-[10px] text-neutral-500 block mb-0.5">
              Architecture
            </span>
            <span className="text-xs font-semibold text-neutral-200 capitalize">
              {selected.architecture || "Modular"}
            </span>
          </div>

          <div className="bg-[#050505] p-2.5 rounded-lg border border-[#1a1a1a]">
            <span className="text-[10px] text-neutral-500 block mb-0.5">
              AST Call Nodes
            </span>
            <span className="text-xs font-semibold text-emerald-400">
              {callNodesCount > 0 ? `${callNodesCount} nodes` : "Extracted"}
            </span>
          </div>
        </div>

        {/* Languages */}
        {selected.languages && selected.languages.length > 0 && (
          <Section icon={Code} title="Languages Detected">
            <TagList items={selected.languages} />
          </Section>
        )}

        {/* Frameworks */}
        {selected.frameworks && selected.frameworks.length > 0 && (
          <Section icon={Package} title="Frameworks &amp; Libraries">
            <TagList items={selected.frameworks} />
          </Section>
        )}

        {/* Entry Points */}
        {selected.entry_points && selected.entry_points.length > 0 && (
          <Section icon={FolderGit2} title="Discovered Entry Points">
            <FileList items={selected.entry_points} />
          </Section>
        )}

        {/* Components */}
        {selected.components && selected.components.length > 0 && (
          <Section icon={Layers} title="Key Architectural Components">
            <TagList items={selected.components} />
          </Section>
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
