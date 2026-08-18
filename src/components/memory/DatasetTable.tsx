import { useState } from "react";
import {
  Database,
  MoreVertical,
  RefreshCw,
  Download,
  Trash2,
  Grid3X3,
  List,
} from "lucide-react";
import { useMemoryStore } from "@/stores/memory-store";
import { useRepositoryStore } from "@/stores/repository-store";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface DatasetTableProps {
  onForget: (dataset: { id: string; name: string }) => void;
}

const filterOptions = [
  { key: "all" as const, label: "All Datasets" },
  { key: "vectors" as const, label: "Vector Spaces" },
  { key: "graphs" as const, label: "Knowledge Graphs" },
];

function formatDate(dateString: string): string {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 30) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return "N/A";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function DatasetTable({ onForget }: DatasetTableProps) {
  const { datasets, filterType, viewMode, setFilter, setViewMode, loading } =
    useMemoryStore();
  const { repositories, indexRepo } = useRepositoryStore();
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const filtered =
    filterType === "all"
      ? datasets
      : datasets.filter((d) => {
          if (filterType === "vectors") return d.type === "vector_db" || d.type === "vectors";
          if (filterType === "graphs") return d.type === "graph" || d.type === "knowledge_graph";
          return true;
        });

  const isEmpty = !loading && datasets.length === 0;

  if (isEmpty) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center py-16 bg-[#050505] rounded-lg border border-[#1e1e1e] p-8">
        <div className="w-12 h-12 rounded-lg bg-[#0f0f0f] border border-[#222222] flex items-center justify-center mb-3 text-neutral-400">
          <Database className="w-5 h-5 text-neutral-300" />
        </div>
        <h3 className="text-sm font-semibold text-white tracking-tight mb-1">
          No datasets indexed yet
        </h3>
        <p className="text-xs text-neutral-500 max-w-sm leading-relaxed">
          Index a repository to populate Cognee vector embeddings and AST graph topologies.
        </p>
      </div>
    );
  }

  const handleExport = (datasetName: string) => {
    const data = JSON.stringify({ dataset: datasetName, exported_at: new Date().toISOString() }, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${datasetName}-memory-export.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleReindex = (datasetName: string) => {
    const matching = repositories.find((r) => r.name === datasetName || r.id === datasetName);
    if (matching) {
      indexRepo(matching.id);
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 bg-[#0a0a0a] p-0.5 rounded-md border border-[#222222] overflow-x-auto">
          {filterOptions.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setFilter(opt.key)}
              className={cn(
                "px-2.5 py-1 text-xs rounded transition-colors whitespace-nowrap cursor-pointer",
                filterType === opt.key
                  ? "bg-white text-black font-medium shadow-xs"
                  : "text-neutral-400 hover:text-white"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 bg-[#0a0a0a] p-0.5 rounded-md border border-[#222222]">
          <button
            onClick={() => setViewMode("list")}
            className={cn(
              "p-1 rounded transition-colors cursor-pointer",
              viewMode === "list"
                ? "bg-[#222222] text-white"
                : "text-neutral-400 hover:text-white"
            )}
            title="List view"
          >
            <List className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={cn(
              "p-1 rounded transition-colors cursor-pointer",
              viewMode === "grid"
                ? "bg-[#222222] text-white"
                : "text-neutral-400 hover:text-white"
            )}
            title="Grid view"
          >
            <Grid3X3 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Table Container with Horizontal Scroll on Narrow Viewports */}
      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <div className="min-w-[620px]">
            {/* Header */}
            <div className="grid grid-cols-[2fr_1fr_1fr_1.5fr_auto] gap-4 px-4 py-2.5 border-b border-[#1a1a1a] bg-[#080808] text-xs font-medium text-neutral-400">
              <div>Dataset / Workspace</div>
              <div>Type</div>
              <div className="text-right">Files / Size</div>
              <div>Created</div>
              <div className="w-7" />
            </div>

            {/* Rows */}
            <div className="divide-y divide-[#141414]">
              {filtered.map((dataset) => (
                <div
                  key={dataset.id}
                  className="grid grid-cols-[2fr_1fr_1fr_1.5fr_auto] gap-4 px-4 py-3 items-center hover:bg-[#0e0e0e] transition-colors group relative"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-7 h-7 rounded-md bg-[#0f0f0f] border border-[#222222] flex items-center justify-center text-neutral-300 shrink-0">
                      <Database className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0 pr-2">
                      <div className="text-xs font-semibold text-white truncate">
                        {dataset.name}
                      </div>
                      <div className="font-mono text-neutral-500 text-[10px] truncate">
                        {dataset.source_path || `ID: ${dataset.id}`}
                      </div>
                    </div>
                  </div>

                  <div>
                    <Badge
                      variant="outline"
                      className="text-[10px] font-mono uppercase px-1.5 py-0"
                    >
                      {dataset.type || "Vector DB"}
                    </Badge>
                  </div>

                  <div className="font-mono text-xs text-neutral-300 text-right">
                    {dataset.file_count ? `${dataset.file_count} files` : formatBytes(dataset.size_bytes)}
                  </div>

                  <div className="text-xs text-neutral-400 font-mono">
                    {formatDate(dataset.created_at)}
                  </div>

                  <div className="relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(openMenuId === dataset.id ? null : dataset.id);
                      }}
                      className="p-1 text-neutral-400 hover:text-white rounded border border-[#222222] bg-[#0a0a0a] hover:border-[#333333] transition-colors cursor-pointer"
                    >
                      <MoreVertical className="w-3.5 h-3.5" />
                    </button>

                    {openMenuId === dataset.id && (
                      <div className="absolute right-0 top-8 w-40 bg-[#0a0a0a] border border-[#262626] rounded-md shadow-xl py-1 z-20 text-xs animate-in fade-in zoom-in-95 duration-100">
                        <button
                          onClick={() => {
                            setOpenMenuId(null);
                            handleReindex(dataset.name);
                          }}
                          className="w-full text-left px-3 py-1.5 text-neutral-300 hover:text-white hover:bg-[#141414] flex items-center gap-2 cursor-pointer"
                        >
                          <RefreshCw className="w-3 h-3" />
                          <span>Re-index</span>
                        </button>
                        <button
                          onClick={() => {
                            setOpenMenuId(null);
                            handleExport(dataset.name);
                          }}
                          className="w-full text-left px-3 py-1.5 text-neutral-300 hover:text-white hover:bg-[#141414] flex items-center gap-2 cursor-pointer"
                        >
                          <Download className="w-3 h-3" />
                          <span>Export Metadata</span>
                        </button>
                        <div className="h-px bg-[#1e1e1e] my-1" />
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setOpenMenuId(null);
                            onForget({ id: dataset.id, name: dataset.name });
                          }}
                          className="w-full text-left px-3 py-1.5 text-red-400 hover:bg-red-950/20 flex items-center gap-2 cursor-pointer"
                        >
                          <Trash2 className="w-3 h-3" />
                          <span>Forget Dataset</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
