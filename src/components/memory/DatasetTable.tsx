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

export function DatasetTable({ onForget }: DatasetTableProps) {
  const { datasets, filterType, viewMode, setFilter, setViewMode } =
    useMemoryStore();
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const filtered =
    filterType === "all"
      ? datasets
      : datasets.filter((d) => {
          const typeMap = {
            vectors: "Vector DB",
            graphs: "Graph",
            document: "Document",
          };
          return d.type === typeMap[filterType];
        });

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
                    {dataset.sourceRepo}
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
                {dataset.size}
              </div>
              <div className="text-[14px] leading-[20px] text-on-surface-variant flex items-center gap-2">
                {dataset.creationDate}
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
