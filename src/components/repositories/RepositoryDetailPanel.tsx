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
    <div className="flex flex-col gap-2.5">
      <h4 className="flex items-center gap-2 text-xs font-mono font-semibold text-neutral-400 uppercase tracking-wider">
        <Icon className="w-3.5 h-3.5 text-white" />
        <span>{title}</span>
      </h4>
      <div className="bg-black p-4 rounded-xl border border-[#222222]">
        {children}
      </div>
    </div>
  );
}

function TagList({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="text-xs font-mono text-neutral-200 bg-[#141414] border border-[#2a2a2a] px-2.5 py-1 rounded-lg"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function FileList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2 font-mono text-xs text-neutral-300">
      {items.map((item) => (
        <li key={item} className="flex items-center gap-2 truncate">
          <span className="w-1.5 h-1.5 rounded-full bg-neutral-500 shrink-0" />
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
      <aside className="w-full h-full bg-[#0a0a0a] rounded-xl border border-[#262626] flex flex-col items-center justify-center p-8 text-center shadow-2xl min-h-0">
        <div className="w-14 h-14 rounded-xl bg-black border border-[#262626] flex items-center justify-center mb-4 text-neutral-500">
          <GitBranch className="w-7 h-7 text-neutral-400" />
        </div>
        <h4 className="text-base font-bold text-white tracking-tight">No Repository Selected</h4>
        <p className="text-xs font-mono text-neutral-400 mt-2 max-w-xs leading-relaxed">
          Select any workspace card from the catalog to inspect AST call graphs, file statistics, and synthesize context.
        </p>
      </aside>
    );
  }

  const callNodesCount = Array.isArray(selected.metadata?.call_graph_nodes)
    ? selected.metadata.call_graph_nodes.length
    : 0;

  return (
    <aside className="w-full h-full bg-[#0a0a0a] rounded-xl border border-[#262626] flex flex-col shadow-2xl overflow-hidden min-h-0">
      {/* Header */}
      <div className="p-5 border-b border-[#262626] flex items-start justify-between gap-3 bg-[#0d0d0d] shrink-0">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-bold text-white tracking-tight truncate">
              {selected.name}
            </h3>
            <Badge
              variant="outline"
              className={`text-[10px] font-mono uppercase px-2 py-0.5 ${
                selected.status === "indexed"
                  ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                  : selected.status === "error"
                  ? "border-red-500/30 text-red-400 bg-red-500/10"
                  : "border-[#333333] text-neutral-400 bg-black"
              }`}
            >
              {selected.status}
            </Badge>
          </div>
          <p className="font-mono text-xs text-neutral-400 truncate">
            {selected.local_path}
          </p>
        </div>

        <button
          onClick={() => select(null)}
          className="p-1.5 rounded-lg border border-[#262626] bg-black text-neutral-400 hover:text-white hover:border-[#404040] transition-colors shrink-0 cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Action Bar */}
      <div className="px-5 py-3 border-b border-[#262626] bg-[#0a0a0a] flex items-center gap-2 shrink-0 flex-wrap">
        <Button
          size="sm"
          onClick={() => setShowQuickContext(true)}
          className="h-8 px-3 text-xs font-mono font-semibold bg-[#1a1a1a] border border-[#333] text-white hover:bg-white hover:text-black gap-1.5 transition-all cursor-pointer"
        >
          <Zap className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
          <span>Quick Context</span>
        </Button>

        <Button
          size="sm"
          onClick={() => navigate(`/studio?repo=${selected.id}`)}
          className="h-8 px-3 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 gap-1.5 shadow-sm cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Studio</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/knowledge/${selected.id}`)}
          className="h-8 px-2.5 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white hover:bg-[#1a1a1a] gap-1 cursor-pointer"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>Knowledge</span>
        </Button>
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-5">
        {/* Purpose / Summary */}
        {selected.summary && (
          <Section icon={FileText} title="Project Overview">
            <p className="text-xs text-neutral-300 leading-relaxed font-sans">
              {selected.summary}
            </p>
          </Section>
        )}

        {/* Telemetry Stats Grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-black p-3 rounded-xl border border-[#222222]">
            <span className="text-[10px] font-mono text-neutral-400 uppercase block mb-0.5">
              Total Files
            </span>
            <span className="text-sm font-bold text-white font-mono">
              {selected.file_count.toLocaleString()}
            </span>
          </div>

          <div className="bg-black p-3 rounded-xl border border-[#222222]">
            <span className="text-[10px] font-mono text-neutral-400 uppercase block mb-0.5">
              Total Size
            </span>
            <span className="text-sm font-bold text-white font-mono">
              {formatBytes(selected.size_bytes)}
            </span>
          </div>

          <div className="bg-black p-3 rounded-xl border border-[#222222]">
            <span className="text-[10px] font-mono text-neutral-400 uppercase block mb-0.5">
              Architecture
            </span>
            <span className="text-xs font-semibold text-white font-mono capitalize">
              {selected.architecture || "Modular"}
            </span>
          </div>

          <div className="bg-black p-3 rounded-xl border border-[#222222]">
            <span className="text-[10px] font-mono text-neutral-400 uppercase block mb-0.5">
              AST Call Nodes
            </span>
            <span className="text-sm font-bold text-emerald-400 font-mono">
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
      <div className="p-4 border-t border-[#262626] bg-[#0d0d0d] flex items-center justify-between gap-2 shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            indexRepo(selected.id);
            setShowReindexModal(true);
          }}
          className="h-8 text-xs font-mono border-[#2a2a2a] bg-black text-neutral-300 hover:text-white hover:bg-[#1a1a1a] gap-1.5 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Re-index</span>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={() => removeRepo(selected.id)}
          className="h-8 text-xs font-mono border-red-500/20 text-red-400 hover:bg-red-500/10 hover:text-red-300 gap-1.5 cursor-pointer"
        >
          <Trash2 className="w-3.5 h-3.5" />
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
