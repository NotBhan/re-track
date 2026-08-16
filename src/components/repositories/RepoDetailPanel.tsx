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
  ArrowRightLeft,
  Box,
  Package,
  FileText,
  GitBranch,
  Clock,
  HardDrive,
} from "lucide-react";
import { useRepositoryStore } from "@/stores/repository-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ReindexModal } from "./ReindexModal";

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
    <div className="flex flex-wrap gap-2">
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

export function RepoDetailPanel() {
  const { selected, select, indexRepo, removeRepo } = useRepositoryStore();
  const navigate = useNavigate();
  const [showReindexModal, setShowReindexModal] = useState(false);

  if (!selected) {
    return (
      <aside className="w-full h-full bg-[#0a0a0a] rounded-xl border border-[#262626] flex flex-col items-center justify-center p-8 text-center shadow-2xl">
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

  return (
    <aside className="w-full h-full bg-[#0a0a0a] rounded-xl border border-[#262626] flex flex-col overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="p-6 border-b border-[#262626] bg-[#0c0c0c]">
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1 min-w-0 pr-3">
            <div className="flex items-center gap-2.5 mb-1.5">
              <div className="w-8 h-8 rounded-lg bg-black border border-[#2a2a2a] flex items-center justify-center text-white shrink-0">
                <GitBranch className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-base font-bold text-white tracking-tight truncate">
                {selected.name}
              </h3>
            </div>
            <p className="font-mono text-xs text-neutral-400 truncate pl-0.5">
              {selected.local_path}
            </p>
          </div>
          <button
            onClick={() => select(null)}
            className="p-1.5 rounded-lg border border-transparent text-neutral-400 hover:text-white hover:border-[#262626] hover:bg-black transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2.5 font-mono text-xs pt-1">
          <Badge
            variant="outline"
            className={`text-[10px] uppercase px-2.5 py-0.5 border ${
              selected.status === "indexed"
                ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                : selected.status === "error"
                ? "border-red-500/30 text-red-400 bg-red-500/10"
                : "border-[#333333] text-neutral-400 bg-black"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5" />
            {selected.status}
          </Badge>
          <span className="text-neutral-600">|</span>
          <span className="text-neutral-400 capitalize">{selected.source_type} repository</span>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1 p-6">
        <div className="flex flex-col gap-6">
          {/* Quick KPI Stat Matrix */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3.5 bg-black rounded-xl border border-[#222222] flex items-center gap-3">
              <HardDrive className="w-4 h-4 text-neutral-400 shrink-0" />
              <div className="min-w-0">
                <span className="text-[10px] font-mono text-neutral-500 uppercase block">Size on Disk</span>
                <span className="text-xs font-mono font-bold text-white truncate block">
                  {formatBytes(selected.size_bytes)}
                </span>
              </div>
            </div>

            <div className="p-3.5 bg-black rounded-xl border border-[#222222] flex items-center gap-3">
              <FolderGit2 className="w-4 h-4 text-neutral-400 shrink-0" />
              <div className="min-w-0">
                <span className="text-[10px] font-mono text-neutral-500 uppercase block">Indexed Files</span>
                <span className="text-xs font-mono font-bold text-white truncate block">
                  {selected.file_count.toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          {/* Summary */}
          {selected.summary && (
            <div className="flex flex-col gap-2.5">
              <h4 className="text-xs font-mono font-semibold text-neutral-400 uppercase tracking-wider">
                Summary
              </h4>
              <p className="text-xs text-neutral-300 bg-black p-4 rounded-xl border border-[#222222] leading-relaxed font-sans">
                {selected.summary}
              </p>
            </div>
          )}

          {/* Languages */}
          {selected.languages.length > 0 && (
            <Section icon={Code} title="Languages">
              <TagList items={selected.languages} />
            </Section>
          )}

          {/* Frameworks */}
          {selected.frameworks.length > 0 && (
            <Section icon={Layers} title="Frameworks">
              <TagList items={selected.frameworks} />
            </Section>
          )}

          {/* Architecture */}
          {selected.architecture && (
            <Section icon={ArrowRightLeft} title="Architecture">
              <p className="text-xs font-sans text-neutral-300 leading-relaxed">
                {selected.architecture}
              </p>
            </Section>
          )}

          {/* Entry Points */}
          {selected.entry_points.length > 0 && (
            <Section icon={FileText} title="Entry Points">
              <FileList items={selected.entry_points} />
            </Section>
          )}

          {/* Components */}
          {selected.components.length > 0 && (
            <Section icon={Box} title="Components">
              <FileList items={selected.components} />
            </Section>
          )}

          {/* Dependencies */}
          {selected.dependencies.length > 0 && (
            <Section icon={Package} title="Dependencies">
              <TagList items={selected.dependencies} />
            </Section>
          )}

          {/* Last indexed timestamp */}
          {selected.indexed_at && (
            <div className="flex items-center gap-2 text-xs font-mono text-neutral-500 pt-1">
              <Clock className="w-3.5 h-3.5" />
              <span>Last indexed {new Date(selected.indexed_at).toLocaleDateString()}</span>
            </div>
          )}

          {/* Action Controls */}
          <div className="pt-2 flex flex-col gap-3">
            <Button
              onClick={() => navigate(`/studio?repo=${selected.id}`)}
              className="w-full h-11 text-xs font-bold uppercase tracking-wider font-mono gap-2 bg-white text-black hover:bg-neutral-200 shadow-md rounded-xl"
            >
              <Sparkles className="w-4 h-4" />
              <span>Launch Context Studio</span>
            </Button>

            <Button
              variant="outline"
              onClick={() => navigate(`/knowledge/${selected.id}`)}
              className="w-full h-10 text-xs font-medium gap-2 border-[#262626] bg-black text-neutral-300 hover:text-white hover:bg-[#1a1a1a] rounded-xl"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Explore Knowledge Graph</span>
            </Button>

            <div className="flex gap-2.5 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  indexRepo(selected.id);
                  setShowReindexModal(true);
                }}
                className="flex-1 h-9 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white rounded-xl"
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                Re-index
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  if (confirm("Delete this repository?")) {
                    removeRepo(selected.id);
                    select(null);
                  }
                }}
                className="flex-1 h-9 text-xs font-mono bg-red-600/20 text-red-400 hover:bg-red-600 hover:text-white border border-red-600/30 rounded-xl"
              >
                <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                Delete
              </Button>
            </div>
          </div>
        </div>

        {/* Live Re-index Progress Modal */}
        <ReindexModal
          repoId={selected.id}
          open={showReindexModal}
          onOpenChange={setShowReindexModal}
        />
      </ScrollArea>
    </aside>
  );
}
