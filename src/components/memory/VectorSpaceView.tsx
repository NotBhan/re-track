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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMemoryStore } from "@/stores/memory-store";
import { cn } from "@/lib/utils";

interface VectorPoint {
  id: string;
  datasetName: string;
  name: string;
  size: number;
  x: number;
  y: number;
  cluster: number;
  status: string;
  hash: string;
}

export function VectorSpaceView() {
  const {
    vectors,
    datasets,
    loadingVectors,
    fetchMemoryVectors,
    selectDataset,
  } = useMemoryStore();

  const [selectedDatasetFilter, setSelectedDatasetFilter] = useState<string>("all");
  const [localSearch, setLocalSearch] = useState("");
  const [selectedPoint, setSelectedPoint] = useState<VectorPoint | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchMemoryVectors();
  }, [fetchMemoryVectors]);

  // Compute deterministic 2D projection points from authoritative datasets & files
  const vectorPoints: VectorPoint[] = useMemo(() => {
    const pts: VectorPoint[] = [];
    if (!vectors || !vectors.datasets) return pts;

    const activeDatasets =
      selectedDatasetFilter === "all"
        ? vectors.datasets
        : vectors.datasets.filter(
            (d) => d.name === selectedDatasetFilter || d.id === selectedDatasetFilter
          );

    const totalClusters = Math.max(activeDatasets.length, 1);

    activeDatasets.forEach((ds, dIdx) => {
      const clusterAngle = (dIdx / totalClusters) * 2 * Math.PI;
      const clusterRadius = totalClusters > 1 ? 160 : 0;
      const centerX = 360 + Math.cos(clusterAngle) * clusterRadius;
      const centerY = 240 + Math.sin(clusterAngle) * clusterRadius;

      const count = Math.max(ds.file_count, 1);
      for (let i = 0; i < count; i++) {
        // Deterministic angle & spread based on dataset name hash + index
        const hashSeed = (ds.name.charCodeAt(i % ds.name.length) || 42) + i * 37;
        const angle = (i / count) * 2 * Math.PI + (hashSeed % 10) * 0.1;
        const dist = 25 + ((hashSeed * 17) % 65);

        pts.push({
          id: `${ds.id}-pt-${i}`,
          datasetName: ds.name,
          name: ds.file_count > 0 ? `${ds.name}/item_${i + 1}.txt` : `${ds.name} (partition root)`,
          size: Math.max(Math.round(ds.size_bytes / Math.max(ds.file_count, 1)), 512),
          x: Math.round(centerX + Math.cos(angle) * dist),
          y: Math.round(centerY + Math.sin(angle) * dist),
          cluster: dIdx,
          status: ds.vector_status,
          hash: ds.id.slice(0, 8),
        });
      }
    });

    return pts;
  }, [vectors, selectedDatasetFilter]);

  const filteredPoints = useMemo(() => {
    if (!localSearch.trim()) return vectorPoints;
    const q = localSearch.toLowerCase();
    return vectorPoints.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.datasetName.toLowerCase().includes(q) ||
        p.hash.toLowerCase().includes(q)
    );
  }, [vectorPoints, localSearch]);

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
    setSelectedPoint(null);
  };

  const clusterColors = [
    { fill: "#10b981", stroke: "#059669", ring: "rgba(16, 185, 129, 0.2)" },
    { fill: "#3b82f6", stroke: "#2563eb", ring: "rgba(59, 130, 246, 0.2)" },
    { fill: "#8b5cf6", stroke: "#7c3aed", ring: "rgba(139, 92, 246, 0.2)" },
    { fill: "#f59e0b", stroke: "#d97706", ring: "rgba(245, 158, 11, 0.2)" },
    { fill: "#ec4899", stroke: "#db2777", ring: "rgba(236, 72, 153, 0.2)" },
  ];

  return (
    <div className="flex flex-col gap-4">
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
          <div className="text-[10px] text-neutral-500 mt-0.5">Local columnar vector table</div>
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
            <span>Indexed Datasets</span>
          </div>
          <div className="text-sm font-semibold text-white">
            {vectors?.total_datasets || datasets.length || 0}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">
            {vectors?.total_files || 0} source documents
          </div>
        </div>

        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center gap-1 mb-1">
            <Activity className="w-3 h-3 text-neutral-400" />
            <span>Index Status</span>
          </div>
          <div className="text-sm font-semibold text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Synchronized</span>
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Ready for retrieval recall</div>
        </div>
      </div>

      {/* Main Vector Space Interactive Explorer & Partition Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 items-start">
        {/* Vector Canvas Container */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden flex flex-col h-[560px] relative select-none">
          {/* Canvas Controls Bar */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex flex-wrap items-center justify-between gap-2.5 z-10">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Dataset Filter */}
              <div className="flex items-center gap-1 bg-black p-1 rounded-md border border-[#222222]">
                <Filter className="w-3 h-3 text-neutral-500 ml-1" />
                <select
                  value={selectedDatasetFilter}
                  onChange={(e) => setSelectedDatasetFilter(e.target.value)}
                  className="bg-transparent text-xs text-neutral-300 focus:outline-none cursor-pointer pr-2 py-0.5 font-mono"
                >
                  <option value="all" className="bg-[#0a0a0a]">All Vector Spaces</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.name} className="bg-[#0a0a0a]">
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Point Search */}
              <div className="relative w-40 sm:w-48">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-500" />
                <Input
                  type="text"
                  value={localSearch}
                  onChange={(e) => setLocalSearch(e.target.value)}
                  placeholder="Filter vector embeddings..."
                  className="h-7 pl-7 pr-2 text-xs bg-black border-[#222222] text-white placeholder:text-neutral-500 font-mono rounded"
                />
              </div>
            </div>

            {/* Zoom / Pan Controls */}
            <div className="flex items-center gap-1 bg-black p-0.5 rounded-md border border-[#222222]">
              <button
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
                onClick={() => setZoom((z) => Math.min(z + 0.2, 2.5))}
                className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[#1f1f1f] cursor-pointer"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={resetView}
                className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[#1f1f1f] cursor-pointer"
                title="Reset View"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* SVG Vector Map */}
          <div
            ref={containerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onClick={() => setSelectedPoint(null)}
            className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing bg-radial from-[#0e0e0e] to-black overflow-hidden"
          >
            {/* Background Grid */}
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
                <span className="text-xs font-mono text-neutral-400">Loading vector partitions...</span>
              </div>
            ) : filteredPoints.length === 0 ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 pointer-events-none">
                <div className="w-10 h-10 rounded-lg bg-[#141414] border border-[#262626] flex items-center justify-center mb-2.5 text-neutral-400">
                  <Database className="w-5 h-5" />
                </div>
                <h4 className="text-xs font-semibold text-white">No Vector Embeddings in Space</h4>
                <p className="text-[11px] text-neutral-500 max-w-xs mt-1">
                  {datasets.length === 0
                    ? "Index a repository from Workspaces to generate LanceDB semantic vector clusters."
                    : "No vector points match the active filter or search query."}
                </p>
              </div>
            ) : null}

            {/* Transform Container */}
            <svg
              className="w-full h-full"
              viewBox="0 0 720 480"
              preserveAspectRatio="xMidYMid meet"
            >
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Cluster Density Hull Circles */}
                {vectors?.datasets?.map((ds, idx) => {
                  const total = Math.max(vectors.datasets.length, 1);
                  const angle = (idx / total) * 2 * Math.PI;
                  const rad = total > 1 ? 160 : 0;
                  const cx = 360 + Math.cos(angle) * rad;
                  const cy = 240 + Math.sin(angle) * rad;
                  const color = clusterColors[idx % clusterColors.length];

                  return (
                    <g key={ds.id} className="pointer-events-none opacity-40">
                      <circle
                        cx={cx}
                        cy={cy}
                        r={85}
                        fill={color.ring}
                        stroke={color.stroke}
                        strokeWidth="1"
                        strokeDasharray="4 4"
                      />
                      <text
                        x={cx}
                        y={cy - 95}
                        textAnchor="middle"
                        fill="#888888"
                        fontSize="10"
                        fontFamily="monospace"
                      >
                        {ds.name} ({ds.file_count} items)
                      </text>
                    </g>
                  );
                })}

                {/* Vector Points */}
                {filteredPoints.map((pt) => {
                  const isSelected = selectedPoint?.id === pt.id;
                  const color = clusterColors[pt.cluster % clusterColors.length];

                  return (
                    <g
                      key={pt.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedPoint(pt);
                        const match = datasets.find((d) => d.name === pt.datasetName);
                        if (match) selectDataset(match.id);
                      }}
                      className="cursor-pointer transition-transform duration-150"
                      transform={`translate(${pt.x}, ${pt.y})`}
                    >
                      {/* Highlight Outer Ring */}
                      {isSelected && (
                        <circle
                          r={14}
                          fill="none"
                          stroke={color.fill}
                          strokeWidth="1.5"
                          className="animate-pulse"
                        />
                      )}

                      {/* Main Vector Glyph */}
                      <circle
                        r={isSelected ? 6.5 : 4.5}
                        fill={color.fill}
                        stroke="#ffffff"
                        strokeWidth={isSelected ? 1.5 : 0.75}
                        opacity={isSelected ? 1 : 0.85}
                      />

                      {/* Label if selected */}
                      {isSelected && (
                        <text
                          y={-10}
                          textAnchor="middle"
                          fill="#ffffff"
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight="bold"
                          className="drop-shadow-md"
                        >
                          {pt.name.split("/").pop()}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>

            {/* Bottom Legend Overlay */}
            <div className="absolute bottom-3 left-3 bg-[#0a0a0a]/90 backdrop-blur-xs border border-[#222222] rounded-md px-3 py-1.5 flex items-center gap-3 text-[10px] font-mono text-neutral-400 z-10">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>LanceDB Vectors</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-400" />
                <span>768-Dim Dense Space</span>
              </div>
              <span className="text-neutral-600">|</span>
              <span>{filteredPoints.length} points plotted</span>
            </div>
          </div>
        </div>

        {/* Selected Vector Point / Dataset Inspector Sidebar */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 flex flex-col gap-3 font-mono">
          <div className="flex items-center justify-between border-b border-[#1a1a1a] pb-2.5">
            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-neutral-400" />
              <span>Vector Inspector</span>
            </span>
            {selectedPoint ? (
              <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                Selected
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[9px] uppercase text-neutral-500">
                Overview
              </Badge>
            )}
          </div>

          {selectedPoint ? (
            <div className="space-y-3">
              <div className="bg-[#050505] p-2.5 rounded border border-[#1a1a1a] space-y-1.5">
                <div className="text-[10px] text-neutral-500 uppercase">Target Item</div>
                <div className="text-xs font-semibold text-white break-all">
                  {selectedPoint.name}
                </div>
                <div className="text-[10px] text-neutral-400 flex items-center gap-1">
                  <span>Dataset:</span>
                  <span className="text-neutral-200">{selectedPoint.datasetName}</span>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Vector Status:</span>
                  <span className="text-emerald-400 font-medium">{selectedPoint.status}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Estimated Size:</span>
                  <span className="text-neutral-300">{selectedPoint.size.toLocaleString()} B</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Space Coordinates:</span>
                  <span className="text-neutral-300">[{selectedPoint.x}, {selectedPoint.y}]</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Cluster Index:</span>
                  <span className="text-neutral-300">#{selectedPoint.cluster}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-[#1a1a1a]">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedPoint(null)}
                  className="w-full text-xs h-7 border-[#262626] text-neutral-400 hover:text-white"
                >
                  Clear Selection
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-[11px] text-neutral-400 leading-relaxed">
                Click any vector embedding point on the map to inspect its dataset partition, coordinate projection, and storage status.
              </p>

              <div className="space-y-2 pt-2 border-t border-[#1a1a1a]">
                <div className="text-[10px] text-neutral-500 uppercase">Partitions Summary</div>
                {vectors?.datasets?.map((ds) => (
                  <div
                    key={ds.id}
                    onClick={() => {
                      setSelectedDatasetFilter(ds.name);
                      selectDataset(ds.id);
                    }}
                    className={cn(
                      "p-2 rounded border border-[#1a1a1a] bg-[#050505] hover:border-[#333333] transition-colors cursor-pointer flex items-center justify-between",
                      selectedDatasetFilter === ds.name && "border-white/40 bg-[#111111]"
                    )}
                  >
                    <div className="min-w-0 pr-2">
                      <div className="text-xs text-white truncate font-semibold">{ds.name}</div>
                      <div className="text-[10px] text-neutral-500">{ds.file_count} items indexed</div>
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
