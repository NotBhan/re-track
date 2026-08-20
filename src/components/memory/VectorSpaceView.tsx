import { useState, useMemo, useRef, useEffect } from "react";
import {
  Cpu,
  Database,
  Layers,
  Search,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RefreshCw,
  CheckCircle2,
  Hash,
  Activity,
  ChevronRight,
  Filter,
  FileCode,
  Sparkles,
  AlertCircle,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMemoryStore } from "@/stores/memory-store";
import { cn } from "@/lib/utils";
import type { VectorDatasetInfo } from "@/lib/api";

export function VectorSpaceView() {
  const {
    vectors,
    datasets,
    loadingVectors,
    fetchMemoryVectors,
    selectedDatasetId,
    selectDataset,
    cognifyActiveDataset,
    cognifying,
    cognifyingDataset,
    cognifyError,
  } = useMemoryStore();

  const [localSearch, setLocalSearch] = useState("");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    fetchMemoryVectors();
  }, [fetchMemoryVectors]);

  // Selected dataset object if one is actively chosen in the store
  const activeSelectedDataset = useMemo(() => {
    return datasets.find((d) => d.id === selectedDatasetId) || null;
  }, [datasets, selectedDatasetId]);

  // Active dataset partition list: filtered by global selectedDatasetId unless "all"
  const activeDatasets: VectorDatasetInfo[] = useMemo(() => {
    if (!vectors || !vectors.datasets) return [];
    if (!selectedDatasetId) return vectors.datasets;
    return vectors.datasets.filter(
      (d) => d.id === selectedDatasetId || (activeSelectedDataset && d.name === activeSelectedDataset.name)
    );
  }, [vectors, selectedDatasetId, activeSelectedDataset]);

  const filteredDatasets = useMemo(() => {
    if (!localSearch.trim()) return activeDatasets;
    const q = localSearch.toLowerCase();
    return activeDatasets.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.id.toLowerCase().includes(q) ||
        d.vector_status.toLowerCase().includes(q)
    );
  }, [activeDatasets, localSearch]);

  const totalSourceFiles = useMemo(() => {
    if (activeSelectedDataset) {
      return activeSelectedDataset.file_count || 0;
    }
    if (vectors?.total_files !== undefined && vectors.total_files > 0) {
      return vectors.total_files;
    }
    return datasets.reduce((acc, d) => acc + (d.file_count || 0), 0);
  }, [activeSelectedDataset, vectors, datasets]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsPanning(true);
    panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isPanning || !panStartRef.current) return;
    setPan({
      x: e.clientX - panStartRef.current.x,
      y: e.clientY - panStartRef.current.y,
    });
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    panStartRef.current = null;
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const formatBytes = (bytes: number) => {
    if (!bytes) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const hasVectorTables = (vectors?.total_vectors ?? 0) > 0;
  const isCurrentlyCognifying = cognifying && (cognifyingDataset === (activeSelectedDataset?.name || "all"));

  return (
    <div className="flex flex-col gap-4">
      {/* Active Dataset Context Banner */}
      {activeSelectedDataset && (
        <div className="p-2.5 bg-[#0d0d0d] border border-[#222222] rounded-lg flex items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-neutral-500">Active Target:</span>
            <span className="font-semibold text-white truncate">{activeSelectedDataset.name}</span>
            <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
              {activeSelectedDataset.file_count || 0} Files
            </Badge>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => cognifyActiveDataset(activeSelectedDataset.name)}
              disabled={cognifying}
              className="px-2.5 py-1 text-[11px] rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 hover:bg-purple-500/20 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Sparkles className={cn("w-3 h-3 text-purple-400", isCurrentlyCognifying && "animate-spin")} />
              <span>{isCurrentlyCognifying ? "Indexing Vectors..." : "Index Active Dataset"}</span>
            </button>
            <button
              type="button"
              onClick={() => selectDataset(null)}
              className="text-neutral-500 hover:text-white p-1 rounded hover:bg-[#1f1f1f] cursor-pointer"
              title="Show All Datasets"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Error Alert */}
      {cognifyError && (
        <div className="p-3 bg-red-950/30 border border-red-800/40 rounded-lg flex items-center gap-2.5 text-xs text-red-300 font-mono">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span className="flex-1">{cognifyError}</span>
        </div>
      )}

      {/* Top Telemetry Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center justify-between mb-1">
            <span className="flex items-center gap-1">
              <Database className="w-3 h-3 text-neutral-400" />
              <span>Vector Provider</span>
            </span>
            <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
              Active
            </Badge>
          </div>
          <div className="text-sm font-semibold text-white uppercase">
            {vectors?.vector_db_provider || "LanceDB"}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Local columnar vector engine</div>
        </div>

        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center gap-1 mb-1">
            <Cpu className="w-3 h-3 text-neutral-400" />
            <span>Embedding Model</span>
          </div>
          <div className="text-xs font-semibold text-white truncate" title={vectors?.embedding_model || "nomic-embed-text"}>
            {vectors?.embedding_model || "nomic-embed-text"}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">
            {vectors?.embedding_dimensions || 768} dimensions
          </div>
        </div>

        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center gap-1 mb-1">
            <Layers className="w-3 h-3 text-neutral-400" />
            <span>{activeSelectedDataset ? "Active Target" : "Partitions"}</span>
          </div>
          <div className="text-sm font-semibold text-white truncate">
            {activeSelectedDataset ? activeSelectedDataset.name : `${vectors?.total_datasets || datasets.length || 0} datasets`}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">
            {totalSourceFiles} source {totalSourceFiles === 1 ? "document" : "documents"}
          </div>
        </div>

        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center gap-1 mb-1">
            <Activity className="w-3 h-3 text-neutral-400" />
            <span>Vector Index Status</span>
          </div>
          <div className="text-xs font-semibold flex items-center gap-1">
            {hasVectorTables ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">{vectors?.total_vectors} vectors</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-blue-400">Staged In Memory</span>
              </>
            )}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5 truncate">
            {hasVectorTables ? "LanceDB indexed" : "Ready for vector indexing"}
          </div>
        </div>
      </div>

      {/* Main Vector Space Area & Vector Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 items-start">
        {/* Vector Canvas / Partitions View Container */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden flex flex-col h-[560px] relative select-none">
          {/* Controls Bar */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex flex-wrap items-center justify-between gap-2.5 z-10 font-mono">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Dataset Partition Filter (Synchronized with global memory store) */}
              <div className="flex items-center gap-1 bg-black p-1 rounded-md border border-[#222222]">
                <Filter className="w-3 h-3 text-neutral-500 ml-1" />
                <select
                  value={selectedDatasetId || "all"}
                  onChange={(e) => selectDataset(e.target.value === "all" ? null : e.target.value)}
                  className="bg-transparent text-xs text-neutral-300 focus:outline-none cursor-pointer pr-2 py-0.5 font-mono"
                >
                  <option value="all" className="bg-[#0a0a0a]">All Partitions ({datasets.length})</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id} className="bg-[#0a0a0a]">
                      {d.name} ({d.file_count || 0} files)
                    </option>
                  ))}
                </select>
              </div>

              {/* Point / Dataset Search */}
              <div className="relative w-44 sm:w-52">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-500" />
                <Input
                  type="text"
                  value={localSearch}
                  onChange={(e) => setLocalSearch(e.target.value)}
                  placeholder="Filter partitions..."
                  className="h-7 pl-7 pr-2 text-xs bg-black border-[#222222] text-white placeholder:text-neutral-500 font-mono rounded"
                />
              </div>
            </div>

            {/* Action & Zoom / Pan Controls */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => cognifyActiveDataset(activeSelectedDataset?.name)}
                disabled={cognifying}
                className="px-2.5 py-1 text-xs rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 hover:bg-purple-500/20 transition-colors flex items-center gap-1.5 cursor-pointer font-mono disabled:opacity-50"
              >
                <Sparkles className={cn("w-3 h-3 text-purple-400", cognifying && "animate-spin")} />
                <span>{cognifying ? "Indexing..." : "Index Vectors"}</span>
              </button>

              <div className="flex items-center gap-1 bg-black p-0.5 rounded-md border border-[#222222]">
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.max(z - 0.2, 0.4))}
                  className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[#1f1f1f] cursor-pointer"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <span className="text-[10px] font-mono text-neutral-400 px-1">
                  {Math.round(zoom * 100)}%
                </span>
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.min(z + 0.2, 2.5))}
                  className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[#1f1f1f] cursor-pointer"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={resetView}
                  className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[#1f1f1f] cursor-pointer"
                  title="Reset View"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Canvas or Staged Partitions Container */}
          <div
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing bg-radial from-[#0e0e0e] to-black overflow-hidden"
          >
            {/* Background Grid Pattern */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none opacity-20"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <pattern id="vector-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                  <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#333333" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#vector-grid)" />
            </svg>

            {loadingVectors ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/60 z-20">
                <RefreshCw className="w-5 h-5 text-neutral-400 animate-spin" />
                <span className="text-xs font-mono text-neutral-400">Reading LanceDB vector space...</span>
              </div>
            ) : filteredDatasets.length === 0 ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 pointer-events-none">
                <div className="w-10 h-10 rounded-lg bg-[#141414] border border-[#262626] flex items-center justify-center mb-2.5 text-neutral-400">
                  <Database className="w-5 h-5" />
                </div>
                <h4 className="text-xs font-semibold text-white font-mono">No Partitions Found</h4>
                <p className="text-[11px] text-neutral-500 max-w-xs mt-1 font-sans">
                  {activeSelectedDataset ? `Dataset "${activeSelectedDataset.name}" has no vector records yet.` : "Index a repository from Workspaces to populate Cognee memory partitions."}
                </p>
              </div>
            ) : (
              /* Authoritative Partition Cards Display */
              <div
                className="absolute inset-0 p-6 overflow-auto flex flex-col items-center justify-center"
                style={{
                  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  transformOrigin: "center center",
                }}
              >
                <div className="w-full max-w-lg space-y-3 font-mono">
                  {/* Status Banner */}
                  <div className="p-3 bg-[#0d0d0d] border border-[#222222] rounded-lg text-center space-y-1">
                    <div className="flex items-center justify-center gap-2 text-xs font-semibold text-white">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      <span>{totalSourceFiles} Source Documents Staged in Memory</span>
                    </div>
                    <p className="text-[11px] text-neutral-400 font-sans">
                      {vectors?.message || "Source documents are stored in Cognee SQLite memory. Vector embeddings are generated for semantic recall."}
                    </p>
                  </div>

                  {/* Partition Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {filteredDatasets.map((ds) => {
                      const isSelected = selectedDatasetId === ds.id;
                      return (
                        <div
                          key={ds.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            selectDataset(isSelected ? null : ds.id);
                          }}
                          className={cn(
                            "p-3 rounded-lg border border-[#1e1e1e] bg-[#070707] hover:border-[#333333] transition-all cursor-pointer space-y-2",
                            isSelected && "border-emerald-500/50 bg-[#111111] shadow-md ring-1 ring-emerald-500/20"
                          )}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="text-xs font-semibold text-white truncate" title={ds.name}>
                                {ds.name}
                              </div>
                              <div className="text-[10px] text-neutral-500 truncate" title={ds.id}>
                                ID: {ds.id.slice(0, 12)}...
                              </div>
                            </div>
                            <Badge
                              variant="outline"
                              className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10 shrink-0 py-0"
                            >
                              {ds.vector_status}
                            </Badge>
                          </div>

                          <div className="flex items-center justify-between text-[10px] text-neutral-400 pt-1 border-t border-[#161616]">
                            <span className="flex items-center gap-1">
                              <FileCode className="w-3 h-3 text-neutral-500" />
                              <span>{ds.file_count} {ds.file_count === 1 ? "file" : "files"}</span>
                            </span>
                            <span>{formatBytes(ds.size_bytes)}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Bottom Legend Overlay */}
            <div className="absolute bottom-3 left-3 bg-[#0a0a0a]/90 backdrop-blur-xs border border-[#222222] rounded-md px-3 py-1.5 flex items-center gap-3 text-[10px] font-mono text-neutral-400 z-10">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>LanceDB Provider</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                <span>{vectors?.embedding_dimensions || 768}-Dim Config</span>
              </div>
              <span className="text-neutral-600">|</span>
              <span>{filteredDatasets.length} {filteredDatasets.length === 1 ? "partition" : "partitions"}</span>
            </div>
          </div>
        </div>

        {/* Vector Inspector Sidebar */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 flex flex-col gap-3 font-mono">
          <div className="flex items-center justify-between border-b border-[#1a1a1a] pb-2.5">
            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-neutral-400" />
              <span>Vector Inspector</span>
            </span>
            {activeSelectedDataset ? (
              <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                Target Selected
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[9px] uppercase text-neutral-500">
                Telemetry
              </Badge>
            )}
          </div>

          {activeSelectedDataset ? (
            <div className="space-y-3">
              <div className="bg-[#050505] p-2.5 rounded border border-[#1a1a1a] space-y-1.5">
                <div className="text-[10px] text-neutral-500 uppercase">Selected Target</div>
                <div className="text-xs font-semibold text-white break-all">
                  {activeSelectedDataset.name}
                </div>
                <div className="text-[10px] text-neutral-400 flex items-center gap-1">
                  <span>UUID:</span>
                  <span className="text-neutral-200 truncate" title={activeSelectedDataset.id}>
                    {activeSelectedDataset.id}
                  </span>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Vector Status:</span>
                  <span className="text-emerald-400 font-medium capitalize">
                    {activeSelectedDataset.file_count > 0 ? "Staged / Ready" : "Empty"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Source Files:</span>
                  <span className="text-neutral-300 font-medium">
                    {activeSelectedDataset.file_count || 0} files
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Partition Size:</span>
                  <span className="text-neutral-300">{formatBytes(activeSelectedDataset.size_bytes || 0)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Embedding Model:</span>
                  <span className="text-neutral-300 truncate max-w-[130px]" title={vectors?.embedding_model}>
                    {vectors?.embedding_model || "nomic-embed-text"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Dimensions:</span>
                  <span className="text-neutral-300">{vectors?.embedding_dimensions || 768}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Vector Engine:</span>
                  <span className="text-neutral-300 uppercase">{vectors?.vector_db_provider || "LanceDB"}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-[#1a1a1a] space-y-2">
                <button
                  type="button"
                  onClick={() => cognifyActiveDataset(activeSelectedDataset.name)}
                  disabled={cognifying}
                  className="w-full py-1.5 text-xs rounded bg-purple-600 text-white hover:bg-purple-500 transition-colors flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50 font-medium"
                >
                  <Sparkles className={cn("w-3.5 h-3.5", isCurrentlyCognifying && "animate-spin")} />
                  <span>{isCurrentlyCognifying ? "Generating Vectors..." : "Index this Dataset"}</span>
                </button>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => selectDataset(null)}
                  className="w-full text-xs h-7 border-[#262626] text-neutral-400 hover:text-white cursor-pointer"
                >
                  Clear Selection
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-[11px] text-neutral-400 leading-relaxed font-sans">
                Select any memory partition card or choose a target from the dropdown to inspect its storage metrics, vector schema, and trigger vector indexing.
              </p>

              <div className="space-y-2 pt-2 border-t border-[#1a1a1a]">
                <div className="text-[10px] text-neutral-500 uppercase">Available Partitions</div>
                {datasets.map((ds) => (
                  <div
                    key={ds.id}
                    onClick={() => selectDataset(ds.id)}
                    className="p-2 rounded border border-[#1a1a1a] bg-[#050505] hover:border-[#333333] transition-colors cursor-pointer flex items-center justify-between"
                  >
                    <div className="min-w-0 pr-2">
                      <div className="text-xs text-white truncate font-semibold">{ds.name}</div>
                      <div className="text-[10px] text-neutral-500">
                        {ds.file_count || 0} files ({formatBytes(ds.size_bytes || 0)})
                      </div>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-neutral-500 shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
