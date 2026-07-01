import { useState } from "react";
import {
  Database,
  MoreVertical,
  RefreshCw,
  Download,
  Trash2,
  Grid3X3,
  List,
  SortAsc,
} from "lucide-react";
import { useMemoryStore } from "@/stores/memory-store";
import { cn } from "@/lib/utils";

interface DatasetTableProps {
  onForget: (dataset: { id: string; name: string }) => void;
}

const filterOptions = [
  { key: "all" as const, label: "All", color: "bg-primary" },
  { key: "vectors" as const, label: "Vectors", color: "bg-primary" },
  { key: "graphs" as const, label: "Graphs", color: "bg-secondary" },
  { key: "document" as const, label: "Document", color: "bg-outline" },
];

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? "s" : ""} ago`;
  if (diffHours < 24)
    return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
  return date.toLocaleDateString();
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "N/A";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function DatasetTable({ onForget }: DatasetTableProps) {
  const { datasets, filterType, viewMode, setFilter, setViewMode, loading } =
    useMemoryStore();
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const filtered =
    filterType === "all"
      ? datasets
      : datasets.filter((d) => {
          const typeMap = {
            vectors: "vector_db",
            graphs: "graph",
            document: "document",
          };
          return d.type === typeMap[filterType];
        });

  const isEmpty = !loading && datasets.length === 0;

  if (isEmpty) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center py-12">
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
          <Database className="w-8 h-8 text-primary" />
        </div>
        <h3 className="text-[16px] leading-[24px] font-semibold text-on-surface mb-2">
          No datasets indexed yet
        </h3>
        <p className="text-[14px] leading-[20px] text-on-surface-variant">
          Index a repository to get started
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Filters */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mr-2">
            Filters:
          </span>
          {filterOptions.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                "px-3 py-1 rounded-full text-[12px] leading-[16px] tracking-[0.02em] font-medium flex items-center gap-1.5 transition-colors",
                filterType === f.key
                  ? "bg-[#1E293B] border border-primary/30 text-primary"
                  : "bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:border-outline-variant"
              )}
            >
              <span className={cn("w-1.5 h-1.5 rounded-full", f.color)} />
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("grid")}
            className={cn(
              "p-1 rounded transition-colors",
              viewMode === "grid"
                ? "text-primary bg-primary/10"
                : "text-on-surface-variant hover:text-on-surface"
            )}
          >
            <Grid3X3 className="w-5 h-5" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={cn(
              "p-1 rounded transition-colors",
              viewMode === "list"
                ? "text-primary bg-primary/10"
                : "text-on-surface-variant hover:text-on-surface"
            )}
          >
            <List className="w-5 h-5" />
          </button>
          <div className="w-px h-4 bg-outline-variant/50 mx-1" />
          <button className="text-on-surface-variant hover:text-on-surface p-1 rounded transition-colors flex items-center gap-1 text-[12px] leading-[16px] tracking-[0.02em] font-medium">
            <SortAsc className="w-4 h-4" />
            Date Added
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden flex-1 flex flex-col">
        {/* Header */}
        <div className="grid grid-cols-[2fr_1fr_1fr_1.5fr_auto] gap-4 p-4 border-b border-outline-variant bg-surface-container/50">
          <div className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant uppercase">
            Dataset / Source Repo
          </div>
          <div className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant uppercase">
            Type
          </div>
          <div className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant uppercase text-right">
            Size
          </div>
          <div className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant uppercase">
            Creation Date
          </div>
          <div className="w-8" />
        </div>

        {/* Rows */}
        <div className="overflow-y-auto flex-1">
          {filtered.map((dataset) => (
            <div
              key={dataset.id}
              className="grid grid-cols-[2fr_1fr_1fr_1.5fr_auto] gap-4 p-4 border-b border-outline-variant/50 items-center hover:bg-surface-variant/20 transition-colors group cursor-pointer relative"
            >
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary scale-y-0 group-hover:scale-y-100 transition-transform origin-left" />
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                  <Database className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[14px] leading-[20px] font-medium text-on-surface">
                    {dataset.name}
                  </div>
                  <div className="font-mono text-on-surface-variant/70 text-[11px] mt-0.5">
                    {dataset.source_path || "N/A"}
                  </div>
                </div>
              </div>
              <div>
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold bg-surface-variant text-on-surface-variant border border-outline-variant/30">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                  {dataset.type}
                </span>
              </div>
              <div className="font-mono text-[13px] leading-[20px] text-on-surface-variant text-right">
                {formatBytes(dataset.size_bytes)}
              </div>
              <div className="text-[14px] leading-[20px] text-on-surface-variant flex items-center gap-2">
                {formatDate(dataset.created_at)}
              </div>
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setOpenMenuId(
                      openMenuId === dataset.id ? null : dataset.id
                    );
                  }}
                  className="p-1.5 text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity hover:bg-surface-variant rounded"
                >
                  <MoreVertical className="w-4 h-4" />
                </button>
                {openMenuId === dataset.id && (
                  <div className="absolute right-0 top-8 w-40 bg-surface-container-high border border-outline-variant/50 rounded-md shadow-[0_10px_25px_-5px_rgba(0,0,0,0.5)] py-1 z-20">
                    <button className="w-full text-left px-3 py-1.5 text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface hover:bg-surface-variant flex items-center gap-2">
                      <RefreshCw className="w-4 h-4" />
                      Re-index
                    </button>
                    <button className="w-full text-left px-3 py-1.5 text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface hover:bg-surface-variant flex items-center gap-2">
                      <Download className="w-4 h-4" />
                      Export
                    </button>
                    <div className="h-px bg-outline-variant/30 my-1" />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(null);
                        onForget({ id: dataset.id, name: dataset.name });
                      }}
                      className="w-full text-left px-3 py-1.5 text-[12px] leading-[16px] tracking-[0.02em] font-medium text-error hover:bg-error/10 flex items-center gap-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      Forget Dataset
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
