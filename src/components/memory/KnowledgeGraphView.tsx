import { useState, useMemo, useRef, useEffect } from "react";
import {
  Share2,
  Search,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RefreshCw,
  Info,
  Layers,
  Sparkles,
  Filter,
  CheckCircle2,
  AlertCircle,
  Hash,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMemoryStore } from "@/stores/memory-store";
import type { MemoryGraphNode } from "@/lib/api";

interface GraphLayoutNode extends MemoryGraphNode {
  x: number;
  y: number;
}

export function KnowledgeGraphView() {
  const {
    graph,
    datasets,
    loadingGraph,
    fetchMemoryGraph,
    selectedNodeId,
    setSelectedNodeId,
  } = useMemoryStore();

  const [selectedKindFilter, setSelectedKindFilter] = useState<string>("all");
  const [localSearch, setLocalSearch] = useState("");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    fetchMemoryGraph();
  }, [fetchMemoryGraph]);

  // Compute node layout positions using circular/grid distribution
  const layoutNodes: GraphLayoutNode[] = useMemo(() => {
    if (!graph || !graph.nodes || graph.nodes.length === 0) return [];

    const count = graph.nodes.length;
    const centerX = 360;
    const centerY = 240;
    const radius = Math.min(220, 60 + count * 15);

    return graph.nodes.map((node, i) => {
      const angle = (i / count) * 2 * Math.PI;
      return {
        ...node,
        x: Math.round(centerX + Math.cos(angle) * radius),
        y: Math.round(centerY + Math.sin(angle) * radius),
      };
    });
  }, [graph]);

  const filteredNodes = useMemo(() => {
    return layoutNodes.filter((node) => {
      if (selectedKindFilter !== "all" && node.kind.toLowerCase() !== selectedKindFilter.toLowerCase()) {
        return false;
      }
      if (localSearch.trim()) {
        const q = localSearch.toLowerCase();
        return (
          node.label.toLowerCase().includes(q) ||
          node.id.toLowerCase().includes(q) ||
          (node.type && node.type.toLowerCase().includes(q))
        );
      }
      return true;
    });
  }, [layoutNodes, selectedKindFilter, localSearch]);

  const selectedNode = useMemo(() => {
    return layoutNodes.find((n) => n.id === selectedNodeId) || null;
  }, [layoutNodes, selectedNodeId]);

  // Inbound & outbound relationships for the selected node
  const relatedEdges = useMemo(() => {
    if (!selectedNode || !graph?.edges) return { inbound: [], outbound: [] };
    const inbound = graph.edges.filter((e) => e.target === selectedNode.id);
    const outbound = graph.edges.filter((e) => e.source === selectedNode.id);
    return { inbound, outbound };
  }, [selectedNode, graph]);

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
    setSelectedNodeId(null);
  };

  const isExtracted = graph && graph.status === "extracted" && graph.nodes.length > 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Top Telemetry Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center justify-between mb-1">
            <span className="flex items-center gap-1">
              <Share2 className="w-3 h-3 text-neutral-400" />
              <span>Graph Engine</span>
            </span>
            <Badge variant="outline" className="text-[9px] uppercase border-purple-500/30 text-purple-400 bg-purple-500/10">
              Kuzu
            </Badge>
          </div>
          <div className="text-sm font-semibold text-white uppercase">
            Cognee Graph
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Embedded Ladybug / Kùzu DB</div>
        </div>

        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center gap-1 mb-1">
            <Layers className="w-3 h-3 text-neutral-400" />
            <span>Entities</span>
          </div>
          <div className="text-sm font-semibold text-white">
            {graph?.total_nodes ?? 0}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Semantic entity nodes</div>
        </div>

        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center gap-1 mb-1">
            <Sparkles className="w-3 h-3 text-neutral-400" />
            <span>Relationships</span>
          </div>
          <div className="text-sm font-semibold text-white">
            {graph?.total_edges ?? 0}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Typed semantic edges</div>
        </div>

        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3">
          <div className="text-[10px] text-neutral-500 flex items-center gap-1 mb-1">
            <Info className="w-3 h-3 text-neutral-400" />
            <span>Extraction State</span>
          </div>
          <div className="text-xs font-semibold capitalize flex items-center gap-1">
            {isExtracted ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Extracted</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-amber-400">Not Extracted</span>
              </>
            )}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5 truncate">
            {isExtracted ? "Active topology" : "Vector store active"}
          </div>
        </div>
      </div>

      {/* Main Canvas + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 items-start">
        {/* Canvas Pane */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden flex flex-col h-[560px] relative select-none">
          {/* Controls Bar */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex flex-wrap items-center justify-between gap-2.5 z-10">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Kind Filter */}
              <div className="flex items-center gap-1 bg-black p-1 rounded-md border border-[#222222]">
                <Filter className="w-3 h-3 text-neutral-500 ml-1" />
                <select
                  value={selectedKindFilter}
                  onChange={(e) => setSelectedKindFilter(e.target.value)}
                  className="bg-transparent text-xs text-neutral-300 focus:outline-none cursor-pointer pr-2 py-0.5 font-mono"
                >
                  <option value="all" className="bg-[#0a0a0a]">All Entity Kinds</option>
                  <option value="entity" className="bg-[#0a0a0a]">Entity</option>
                  <option value="concept" className="bg-[#0a0a0a]">Concept</option>
                  <option value="document" className="bg-[#0a0a0a]">Document</option>
                  <option value="file" className="bg-[#0a0a0a]">File</option>
                </select>
              </div>

              {/* Node Search */}
              <div className="relative w-40 sm:w-48">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-500" />
                <Input
                  type="text"
                  value={localSearch}
                  onChange={(e) => setLocalSearch(e.target.value)}
                  placeholder="Filter entities & relations..."
                  className="h-7 pl-7 pr-2 text-xs bg-black border-[#222222] text-white placeholder:text-neutral-500 font-mono rounded"
                />
              </div>
            </div>

            {/* Canvas Actions */}
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

          {/* Canvas Area */}
          <div
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onClick={() => setSelectedNodeId(null)}
            className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing bg-radial from-[#0e0e0e] to-black overflow-hidden"
          >
            {/* Background Graph Pattern */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none opacity-20"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <pattern id="kg-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                  <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#333333" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#kg-grid)" />
            </svg>

            {loadingGraph ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/60 z-20">
                <RefreshCw className="w-5 h-5 text-neutral-400 animate-spin" />
                <span className="text-xs font-mono text-neutral-400">Loading knowledge graph...</span>
              </div>
            ) : !isExtracted ? (
              /* Truthful State Banner */
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center z-10 pointer-events-none">
                <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-3 text-purple-400">
                  <Share2 className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-semibold text-white font-mono">
                  Knowledge Graph Not Extracted
                </h4>
                <p className="text-xs text-neutral-400 max-w-md mt-1.5 leading-relaxed font-sans">
                  Raw vector ingestion is active in LanceDB. Knowledge graph entity extraction is an optional semantic enrichment phase that generates entity-relation triples from cognitive memory.
                </p>
                <div className="mt-4 flex items-center gap-2 font-mono text-[11px] text-neutral-500 bg-[#0d0d0d] border border-[#222222] px-3 py-1.5 rounded-md">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>Vector Index: Active</span>
                  <span className="text-neutral-700">|</span>
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  <span>KG Triples: 0</span>
                </div>
              </div>
            ) : null}

            {/* Graph Node Render */}
            {isExtracted && (
              <svg
                className="w-full h-full"
                viewBox="0 0 720 480"
                preserveAspectRatio="xMidYMid meet"
              >
                <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                  {/* Edges */}
                  {graph?.edges.map((edge, idx) => {
                    const src = layoutNodes.find((n) => n.id === edge.source);
                    const tgt = layoutNodes.find((n) => n.id === edge.target);
                    if (!src || !tgt) return null;

                    const isHighlight =
                      selectedNodeId === edge.source || selectedNodeId === edge.target;

                    return (
                      <g key={`edge-${idx}`}>
                        <line
                          x1={src.x}
                          y1={src.y}
                          x2={tgt.x}
                          y2={tgt.y}
                          stroke={isHighlight ? "#a855f7" : "#333333"}
                          strokeWidth={isHighlight ? 2 : 1}
                          strokeDasharray={isHighlight ? undefined : "3 3"}
                        />
                        {isHighlight && edge.relationship_type && (
                          <text
                            x={(src.x + tgt.x) / 2}
                            y={(src.y + tgt.y) / 2 - 6}
                            textAnchor="middle"
                            fill="#c084fc"
                            fontSize="8"
                            fontFamily="monospace"
                          >
                            {edge.relationship_type}
                          </text>
                        )}
                      </g>
                    );
                  })}

                  {/* Nodes */}
                  {filteredNodes.map((node) => {
                    const isSelected = selectedNodeId === node.id;
                    return (
                      <g
                        key={node.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedNodeId(node.id);
                        }}
                        className="cursor-pointer transition-transform duration-150"
                        transform={`translate(${node.x}, ${node.y})`}
                      >
                        {isSelected && (
                          <circle
                            r={18}
                            fill="none"
                            stroke="#a855f7"
                            strokeWidth="1.5"
                            className="animate-pulse"
                          />
                        )}
                        <circle
                          r={10}
                          fill="#18181b"
                          stroke={isSelected ? "#c084fc" : "#52525b"}
                          strokeWidth={isSelected ? 2 : 1}
                        />
                        <text
                          y={20}
                          textAnchor="middle"
                          fill={isSelected ? "#ffffff" : "#a1a1aa"}
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight={isSelected ? "bold" : "normal"}
                        >
                          {node.label}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            )}

            {/* Canvas Legend */}
            <div className="absolute bottom-3 left-3 bg-[#0a0a0a]/90 backdrop-blur-xs border border-[#222222] rounded-md px-3 py-1.5 flex items-center gap-3 text-[10px] font-mono text-neutral-400 z-10">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-purple-400" />
                <span>Entity Nodes</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-neutral-500" />
                <span>Kùzu Relations</span>
              </div>
              <span className="text-neutral-600">|</span>
              <span>{filteredNodes.length} entities visible</span>
            </div>
          </div>
        </div>

        {/* Entity Inspector Sidebar */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 flex flex-col gap-3 font-mono">
          <div className="flex items-center justify-between border-b border-[#1a1a1a] pb-2.5">
            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-neutral-400" />
              <span>Entity Inspector</span>
            </span>
            {selectedNode ? (
              <Badge variant="outline" className="text-[9px] uppercase border-purple-500/30 text-purple-400 bg-purple-500/10">
                Selected
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[9px] uppercase text-neutral-500">
                Status
              </Badge>
            )}
          </div>

          {selectedNode ? (
            <div className="space-y-3">
              <div className="bg-[#050505] p-2.5 rounded border border-[#1a1a1a] space-y-1">
                <div className="text-[10px] text-neutral-500 uppercase">Entity Label</div>
                <div className="text-xs font-semibold text-white break-all">
                  {selectedNode.label}
                </div>
                <div className="text-[10px] text-neutral-400 flex items-center gap-1">
                  <span>Kind:</span>
                  <span className="text-purple-300 uppercase">{selectedNode.kind}</span>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Entity ID:</span>
                  <span className="text-neutral-300 truncate max-w-[140px]" title={selectedNode.id}>
                    {selectedNode.id}
                  </span>
                </div>
                {selectedNode.type && (
                  <div className="flex items-center justify-between">
                    <span className="text-neutral-500">Type:</span>
                    <span className="text-neutral-300">{selectedNode.type}</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Inbound Relations:</span>
                  <span className="text-neutral-300">{relatedEdges.inbound.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-neutral-500">Outbound Relations:</span>
                  <span className="text-neutral-300">{relatedEdges.outbound.length}</span>
                </div>
              </div>

              {/* Properties */}
              {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-[#1a1a1a]">
                  <div className="text-[10px] text-neutral-500 uppercase">Attributes</div>
                  <div className="bg-[#050505] p-2 rounded border border-[#1a1a1a] max-h-28 overflow-y-auto space-y-1 text-[10px]">
                    {Object.entries(selectedNode.properties).map(([k, v]) => (
                      <div key={k} className="flex items-start justify-between gap-2">
                        <span className="text-neutral-500 shrink-0">{k}:</span>
                        <span className="text-neutral-300 break-all">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-2 border-t border-[#1a1a1a]">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedNodeId(null)}
                  className="w-full text-xs h-7 border-[#262626] text-neutral-400 hover:text-white"
                >
                  Clear Selection
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-[11px] text-neutral-400 leading-relaxed font-sans">
                {isExtracted
                  ? "Select any entity node on the canvas to inspect its semantic properties, entity kind, and inbound/outbound relations."
                  : "Knowledge Graph extraction is synchronized with Cognee's entity-relation pipeline. In RE:Track, vector embeddings handle instant semantic search while the AST Call Graph provides deterministic code topology."}
              </p>

              <div className="p-2.5 rounded bg-[#050505] border border-[#1a1a1a] space-y-2">
                <div className="text-[10px] text-neutral-500 uppercase font-semibold">
                  Memory Topology Layers
                </div>
                <div className="space-y-1.5 text-[11px]">
                  <div className="flex items-center justify-between text-neutral-400">
                    <span>1. Ingested Files:</span>
                    <span className="text-white font-medium">{datasets.length} datasets</span>
                  </div>
                  <div className="flex items-center justify-between text-neutral-400">
                    <span>2. Vector Index:</span>
                    <span className="text-emerald-400 font-medium">LanceDB Active</span>
                  </div>
                  <div className="flex items-center justify-between text-neutral-400">
                    <span>3. Knowledge Graph:</span>
                    <span className="text-amber-400 font-medium">
                      {graph?.status === "extracted" ? "Extracted" : "Not Extracted"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
