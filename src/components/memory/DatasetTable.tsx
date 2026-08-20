import { useState, useMemo, useRef, useEffect } from "react";
import {
  Database,
  MoreVertical,
  RefreshCw,
  Download,
  Trash2,
  Eye,
  FileCode,
  FolderOpen,
  X,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { useMemoryStore } from "@/stores/memory-store";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { DatasetItemsModal } from "./DatasetItemsModal";

interface DatasetTableProps {
  onForget: (dataset: { id: string; name: string }) => void;
}

function formatDate(dateString?: string | null): string {
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

function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "0 B";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function DatasetTable({ onForget }: DatasetTableProps) {
  const {
    datasets,
    loading,
    loadingItems,
    searchQuery,
    selectedDatasetId,
    selectedDatasetItems,
    selectDataset,
    reindexDataset,
    reindexingDatasetId,
    reindexError,
    cognifyActiveDataset,
    cognifying,
    cognifyingDataset,
  } = useMemoryStore();

  const [openMenu, setOpenMenu] = useState<{
    id: string;
    name: string;
    top: number;
    right: number;
  } | null>(null);

  const [inspectingModalDataset, setInspectingModalDataset] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on click outside or Escape key
  useEffect(() => {
    if (!openMenu) return;

    const handleMouseDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpenMenu(null);
      }
    };

    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openMenu]);

  const filtered = useMemo(() => {
    return datasets.filter((d) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          d.name.toLowerCase().includes(q) ||
          (d.source_path && d.source_path.toLowerCase().includes(q)) ||
          d.id.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [datasets, searchQuery]);

  const selectedDataset = useMemo(() => {
    return datasets.find((d) => d.id === selectedDatasetId) || null;
  }, [datasets, selectedDatasetId]);

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
          Index a repository in Workspaces to populate Cognee vector embeddings and memory partitions.
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

  const handleToggleMenu = (e: React.MouseEvent<HTMLButtonElement>, dataset: { id: string; name: string }) => {
    e.stopPropagation();
    if (openMenu?.id === dataset.id) {
      setOpenMenu(null);
      return;
    }

    const rect = e.currentTarget.getBoundingClientRect();
    setOpenMenu({
      id: dataset.id,
      name: dataset.name,
      top: rect.bottom + 4,
      right: window.innerWidth - rect.right,
    });
  };

  return (
    <div className="space-y-4">
      {/* Reindex / Extraction Error Banner */}
      {reindexError && (
        <div className="p-3 bg-red-950/30 border border-red-800/40 rounded-lg flex items-center gap-2.5 text-xs text-red-300 font-mono">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span className="flex-1">{reindexError}</span>
        </div>
      )}

      {/* Table Container */}
      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden flex flex-col shadow-sm">
        <div className="overflow-x-auto">
          <div className="min-w-[620px]">
            {/* Header */}
            <div className="grid grid-cols-[2fr_1fr_1.2fr_1.2fr_auto] gap-4 px-4 py-2.5 border-b border-[#1a1a1a] bg-[#080808] text-xs font-medium text-neutral-400 font-mono">
              <div>Dataset / Workspace</div>
              <div>Memory Type</div>
              <div className="text-right">Files / Size</div>
              <div>Created</div>
              <div className="w-7" />
            </div>

            {/* Rows */}
            <div className="divide-y divide-[#141414]">
              {filtered.map((dataset) => {
                const isSelected = selectedDatasetId === dataset.id;
                const isReindexing = reindexingDatasetId === dataset.name;
                const isCognifying = cognifying && cognifyingDataset === dataset.name;

                return (
                  <div
                    key={dataset.id}
                    onClick={() => selectDataset(isSelected ? null : dataset.id)}
                    className={cn(
                      "grid grid-cols-[2fr_1fr_1.2fr_1.2fr_auto] gap-4 px-4 py-3 items-center hover:bg-[#0e0e0e] transition-colors group relative cursor-pointer",
                      isSelected && "bg-[#121212] border-l-2 border-l-white"
                    )}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div
                        className={cn(
                          "w-7 h-7 rounded-md bg-[#0f0f0f] border border-[#222222] flex items-center justify-center text-neutral-300 shrink-0 transition-colors",
                          isSelected && "border-white/40 text-white bg-[#1a1a1a]"
                        )}
                      >
                        {isReindexing || isCognifying ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                        ) : (
                          <Database className="w-3.5 h-3.5" />
                        )}
                      </div>
                      <div className="min-w-0 pr-2">
                        <div className="text-xs font-semibold text-white truncate flex items-center gap-1.5">
                          <span>{dataset.name}</span>
                          {isSelected && (
                            <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10 py-0 px-1 font-mono">
                              Active Target
                            </Badge>
                          )}
                          {isReindexing && (
                            <Badge variant="outline" className="text-[9px] uppercase border-blue-500/30 text-blue-400 bg-blue-500/10 py-0 px-1 font-mono animate-pulse">
                              Re-indexing...
                            </Badge>
                          )}
                        </div>
                        <div
                          className="font-mono text-neutral-500 text-[10px] truncate"
                          title={dataset.source_path || `ID: ${dataset.id}`}
                        >
                          {dataset.source_path || `ID: ${dataset.id}`}
                        </div>
                      </div>
                    </div>

                    <div>
                      <Badge
                        variant="outline"
                        className="text-[10px] font-mono uppercase px-1.5 py-0 border-neutral-800 text-neutral-300 bg-neutral-900"
                      >
                        Repository
                      </Badge>
                    </div>

                    <div className="font-mono text-xs text-neutral-300 text-right">
                      {dataset.file_count > 0 ? (
                        <span>
                          {dataset.file_count} {dataset.file_count === 1 ? "file" : "files"} ({formatBytes(dataset.size_bytes)})
                        </span>
                      ) : (
                        <span className="text-neutral-500">0 files (0 B)</span>
                      )}
                    </div>

                    <div className="text-xs text-neutral-400 font-mono">
                      {formatDate(dataset.created_at)}
                    </div>

                    <div>
                      <button
                        type="button"
                        onClick={(e) => handleToggleMenu(e, { id: dataset.id, name: dataset.name })}
                        title="Dataset options"
                        aria-label="Dataset options"
                        className="p-1 text-neutral-400 hover:text-white rounded border border-[#222222] bg-[#0a0a0a] hover:border-[#333333] transition-colors cursor-pointer"
                      >
                        <MoreVertical className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Floating Three-Dot Menu Portal (Decoupled from table overflow to eliminate scrollbars/layout shifts) */}
      {openMenu && (
        <div
          ref={menuRef}
          style={{
            position: "fixed",
            top: `${openMenu.top}px`,
            right: `${openMenu.right}px`,
            zIndex: 9999,
          }}
          className="w-48 bg-[#0a0a0a] border border-[#262626] rounded-md shadow-2xl py-1 text-xs animate-in fade-in zoom-in-95 duration-100 font-mono"
        >
          <button
            type="button"
            onClick={() => {
              const ds = openMenu;
              setOpenMenu(null);
              selectDataset(ds.id);
              setInspectingModalDataset({ id: ds.id, name: ds.name });
            }}
            className="w-full text-left px-3 py-1.5 text-neutral-300 hover:text-white hover:bg-[#141414] flex items-center gap-2 cursor-pointer"
          >
            <Eye className="w-3.5 h-3.5 text-neutral-400" />
            <span>Inspect Files Modal</span>
          </button>

          <button
            type="button"
            disabled={reindexingDatasetId === openMenu.name}
            onClick={async () => {
              const dsName = openMenu.name;
              setOpenMenu(null);
              await reindexDataset(dsName);
            }}
            className="w-full text-left px-3 py-1.5 text-neutral-300 hover:text-white hover:bg-[#141414] flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", reindexingDatasetId === openMenu.name && "animate-spin text-blue-400")} />
            <span>Re-index Repository</span>
          </button>

          <button
            type="button"
            disabled={cognifying}
            onClick={async () => {
              const dsName = openMenu.name;
              setOpenMenu(null);
              await cognifyActiveDataset(dsName);
            }}
            className="w-full text-left px-3 py-1.5 text-purple-300 hover:text-purple-100 hover:bg-[#141414] flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <Sparkles className={cn("w-3.5 h-3.5 text-purple-400", cognifying && "animate-spin")} />
            <span>Extract KG & Vectors</span>
          </button>

          <button
            type="button"
            onClick={() => {
              const dsName = openMenu.name;
              setOpenMenu(null);
              handleExport(dsName);
            }}
            className="w-full text-left px-3 py-1.5 text-neutral-300 hover:text-white hover:bg-[#141414] flex items-center gap-2 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Metadata</span>
          </button>

          <div className="h-px bg-[#1e1e1e] my-1" />

          <button
            type="button"
            onClick={() => {
              const ds = openMenu;
              setOpenMenu(null);
              onForget(ds);
            }}
            className="w-full text-left px-3 py-1.5 text-red-400 hover:bg-red-950/20 flex items-center gap-2 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Forget Dataset</span>
          </button>
        </div>
      )}

      {/* Selected Dataset Docked Detail Panel */}
      {selectedDataset ? (
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 font-mono space-y-3 animate-in fade-in duration-150">
          <div className="flex items-center justify-between border-b border-[#1a1a1a] pb-2.5">
            <div className="flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-neutral-400" />
              <span className="text-xs font-semibold text-white">
                Ingested Files & Chunks for "{selectedDataset.name}"
              </span>
              <Badge variant="outline" className="text-[10px] border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                {selectedDatasetItems.length} {selectedDatasetItems.length === 1 ? "document" : "documents"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => cognifyActiveDataset(selectedDataset.name)}
                disabled={cognifying}
                className="px-2.5 py-1 text-[11px] rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 hover:bg-purple-500/20 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <Sparkles className={cn("w-3 h-3 text-purple-400", cognifying && "animate-spin")} />
                <span>{cognifying ? "Extracting..." : "Extract Memory"}</span>
              </button>
              <button
                type="button"
                onClick={() => selectDataset(null)}
                className="text-neutral-500 hover:text-white p-1 rounded hover:bg-[#1f1f1f] cursor-pointer"
                title="Deselect Dataset"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {loadingItems ? (
            <div className="flex items-center justify-center py-6 text-neutral-500 text-xs gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-neutral-400" />
              <span>Loading stored document items...</span>
            </div>
          ) : selectedDatasetItems.length === 0 ? (
            <div className="text-center py-6 text-neutral-500 text-xs">
              No files or documents stored in this partition.
            </div>
          ) : (
            <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
              {selectedDatasetItems.map((item) => (
                <div
                  key={item.id}
                  className="p-2 rounded bg-[#050505] border border-[#1a1a1a] flex items-center justify-between gap-3 text-xs hover:border-[#2a2a2a] transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <FileCode className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-white font-medium truncate" title={item.name}>
                        {item.name}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-neutral-500 mt-0.5">
                        <span>{item.mime_type}</span>
                        {item.content_hash && (
                          <>
                            <span>•</span>
                            <span className="truncate max-w-[140px]" title={item.content_hash}>
                              hash: {item.content_hash.slice(0, 12)}...
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0 text-[11px]">
                    <span className="text-neutral-400">{formatBytes(item.data_size)}</span>
                    <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/20 text-emerald-400 bg-emerald-500/5">
                      Ingested
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="p-3 bg-[#050505] rounded-lg border border-[#1a1a1a] text-center text-xs text-neutral-500 font-mono">
          Click any dataset row above to select it as the active target across Datasets, Vector Space, and Knowledge Graph.
        </div>
      )}

      {inspectingModalDataset && (
        <DatasetItemsModal
          datasetId={inspectingModalDataset.id}
          datasetName={inspectingModalDataset.name}
          isOpen={!!inspectingModalDataset}
          onClose={() => setInspectingModalDataset(null)}
        />
      )}
    </div>
  );
}
