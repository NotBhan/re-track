/**
 * CallGraphView — Interactive force-directed call graph visualization.
 *
 * Renders the repository's extracted function/class/component dependency graph.
 * Pure React + SVG with a lightweight spring-force simulation.
 *
 * Supports:
 *  - Node kinds: class (square), function/method (circle), component (diamond)
 *  - Edge kinds: calls (solid), imports (dashed), inherits (thick), renders (dotted)
 *  - Filtering by Node Kind & Edge Kind
 *  - Node search with live highlighting
 *  - Interactive Node Inspector panel on click
 *  - Drag nodes, scroll to zoom, pan, reset view controls
 */

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import type { CallGraphEdge, CallGraphNode } from "@/types/repository";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

const NODE_KIND_COLOR: Record<string, string> = {
  class: "#ffffff",
  method: "#a3a3a3",
  function: "#e5e5e5",
  component: "#4ade80",
  module: "#facc15",
};

const NODE_KIND_BG: Record<string, string> = {
  class: "#1a1a1a",
  method: "#141414",
  function: "#171717",
  component: "#052e16",
  module: "#422006",
};

const NODE_KIND_STROKE: Record<string, string> = {
  class: "#ffffff",
  method: "#737373",
  function: "#a3a3a3",
  component: "#22c55e",
  module: "#eab308",
};

const EDGE_KIND_STYLE: Record<string, { stroke: string; dash: string; width: number }> = {
  calls:    { stroke: "#525252", dash: "none",  width: 1.2 },
  imports:  { stroke: "#3b82f6", dash: "4 3",   width: 1   },
  inherits: { stroke: "#e2e8f0", dash: "none",  width: 2   },
  renders:  { stroke: "#10b981", dash: "2 4",   width: 1.2 },
};

const RADIUS = 18;
const REPULSION = 4500;
const LINK_DISTANCE = 95;
const CENTERING = 0.05;
const DAMPING = 0.85;

interface SimNode extends CallGraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface Props {
  nodes: CallGraphNode[];
  edges: CallGraphEdge[];
  width?: number;
  height?: number;
  selectedNodeId?: string | null;
  onSelectNode?: (node: CallGraphNode | null) => void;
}

function initSim(nodes: CallGraphNode[], w: number, h: number): SimNode[] {
  const n = nodes.length || 1;
  return nodes.map((node, i) => {
    const angle = (2 * Math.PI * i) / n;
    const r = Math.min(w, h) * 0.32;
    return { ...node, x: w / 2 + r * Math.cos(angle), y: h / 2 + r * Math.sin(angle), vx: 0, vy: 0 };
  });
}

export function CallGraphView({
  nodes: rawNodes,
  edges: rawEdges,
  width = 800,
  height = 560,
  selectedNodeId,
  onSelectNode,
}: Props) {
  const [selectedKind, setSelectedKind] = useState<string>("all");
  const [selectedEdgeKind, setSelectedEdgeKind] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNode, setActiveNode] = useState<CallGraphNode | null>(null);

  // Filter nodes & edges
  const filteredNodes = useMemo(() => {
    return rawNodes.filter((node) => {
      const matchesKind = selectedKind === "all" || node.kind === selectedKind;
      const matchesSearch =
        !searchQuery ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.file.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesKind && matchesSearch;
    });
  }, [rawNodes, selectedKind, searchQuery]);

  const activeNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return rawEdges.filter((edge) => {
      const matchesKind = selectedEdgeKind === "all" || edge.kind === selectedEdgeKind;
      const nodesExist = activeNodeIds.has(edge.source) && activeNodeIds.has(edge.target);
      return matchesKind && nodesExist;
    });
  }, [rawEdges, selectedEdgeKind, activeNodeIds]);

  const [simNodes, setSimNodes] = useState<SimNode[]>(() => initSim(filteredNodes, width, height));
  const [hovered, setHovered] = useState<string | null>(null);
  const [dragging, setDragging] = useState<{ id: string; ox: number; oy: number } | null>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [panDrag, setPanDrag] = useState<{ sx: number; sy: number; px: number; py: number } | null>(null);

  const nodesRef = useRef<SimNode[]>(simNodes);
  const alphaRef = useRef(0.35);
  const idxRef = useRef<Map<string, number>>(new Map());

  // Re-sync simulation when filtered nodes change
  useEffect(() => {
    const map = new Map<string, number>();
    filteredNodes.forEach((n, i) => map.set(n.id, i));
    idxRef.current = map;
    const s = initSim(filteredNodes, width, height);
    nodesRef.current = s;
    setSimNodes([...s]);
    alphaRef.current = 0.35;
  }, [filteredNodes, width, height]);

  // Spring physics loop
  useEffect(() => {
    const id = setInterval(() => {
      if (alphaRef.current < 0.004) return;
      alphaRef.current *= 0.97;
      const ns = nodesRef.current.map((n) => ({ ...n }));
      const cx = width / 2,
        cy = height / 2;

      for (const n of ns) {
        n.vx += (cx - n.x) * CENTERING * alphaRef.current;
        n.vy += (cy - n.y) * CENTERING * alphaRef.current;
      }

      for (let i = 0; i < ns.length; i++) {
        for (let j = i + 1; j < ns.length; j++) {
          const dx = ns[j].x - ns[i].x;
          const dy = ns[j].y - ns[i].y;
          const dist = Math.hypot(dx, dy) || 1;
          if (dist < 260) {
            const force = (REPULSION / (dist * dist)) * alphaRef.current;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            ns[i].vx -= fx;
            ns[i].vy -= fy;
            ns[j].vx += fx;
            ns[j].vy += fy;
          }
        }
      }

      for (const e of filteredEdges) {
        const si = idxRef.current.get(e.source);
        const ti = idxRef.current.get(e.target);
        if (si === undefined || ti === undefined) continue;
        const sn = ns[si],
          tn = ns[ti];
        const dx = tn.x - sn.x;
        const dy = tn.y - sn.y;
        const dist = Math.hypot(dx, dy) || 1;
        const force = (dist - LINK_DISTANCE) * 0.06 * alphaRef.current;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        sn.vx += fx;
        sn.vy += fy;
        tn.vx -= fx;
        tn.vy -= fy;
      }

      for (const n of ns) {
        n.vx *= DAMPING;
        n.vy *= DAMPING;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(RADIUS, Math.min(width - RADIUS, n.x));
        n.y = Math.max(RADIUS, Math.min(height - RADIUS, n.y));
      }

      nodesRef.current = ns;
      setSimNodes(ns);
    }, 16);

    return () => clearInterval(id);
  }, [filteredEdges, width, height]);

  // Drag interaction
  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent, node: SimNode) => {
      e.stopPropagation();
      setDragging({ id: node.id, ox: e.clientX - node.x, oy: e.clientY - node.y });
      alphaRef.current = 0.2;
    },
    []
  );

  const handleNodeClick = useCallback(
    (node: CallGraphNode) => {
      setActiveNode(node);
      onSelectNode?.(node);
    },
    [onSelectNode]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) {
        const nx = (e.clientX - dragging.ox - pan.x) / zoom;
        const ny = (e.clientY - dragging.oy - pan.y) / zoom;
        nodesRef.current = nodesRef.current.map((n) =>
          n.id === dragging.id ? { ...n, x: nx, y: ny, vx: 0, vy: 0 } : n
        );
        setSimNodes([...nodesRef.current]);
      } else if (panDrag) {
        setPan({
          x: panDrag.px + (e.clientX - panDrag.sx),
          y: panDrag.py + (e.clientY - panDrag.sy),
        });
      }
    },
    [dragging, panDrag, pan, zoom]
  );

  const handleMouseUp = useCallback(() => {
    setDragging(null);
    setPanDrag(null);
  }, []);

  const handleSvgMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).tagName === "svg" || (e.target as HTMLElement).tagName === "rect") {
        setPanDrag({ sx: e.clientX, sy: e.clientY, px: pan.x, py: pan.y });
      }
    },
    [pan]
  );

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.max(0.4, Math.min(2.5, z - e.deltaY * 0.001)));
  }, []);

  const resetView = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
    alphaRef.current = 0.35;
  };

  const posMap = useMemo(() => {
    const m = new Map<string, { x: number; y: number }>();
    for (const n of simNodes) m.set(n.id, { x: n.x, y: n.y });
    return m;
  }, [simNodes]);

  // Connected edges for the active/selected node
  const activeIncoming = useMemo(() => {
    if (!activeNode) return [];
    return rawEdges.filter((e) => e.target === activeNode.id);
  }, [activeNode, rawEdges]);

  const activeOutgoing = useMemo(() => {
    if (!activeNode) return [];
    return rawEdges.filter((e) => e.source === activeNode.id);
  }, [activeNode, rawEdges]);

  return (
    <div className="relative w-full h-full select-none bg-black rounded-xl border border-[#262626] overflow-hidden flex flex-col">
      {/* Top Filter & Search Controls Bar */}
      <div className="p-3 border-b border-[#222222] bg-[#0c0c0c] flex flex-wrap items-center justify-between gap-3 shrink-0 z-10">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Node Kind Filter */}
          <div className="flex items-center gap-1 bg-black p-1 rounded-lg border border-[#262626]">
            {["all", "class", "function", "method", "component"].map((kind) => (
              <button
                key={kind}
                onClick={() => setSelectedKind(kind)}
                className={cn(
                  "text-[11px] font-mono px-2 py-0.5 rounded capitalize transition-all cursor-pointer",
                  selectedKind === kind
                    ? "bg-white text-black font-semibold shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                {kind}
              </button>
            ))}
          </div>

          {/* Edge Kind Filter */}
          <div className="hidden sm:flex items-center gap-1 bg-black p-1 rounded-lg border border-[#262626]">
            {["all", "calls", "imports", "renders"].map((ek) => (
              <button
                key={ek}
                onClick={() => setSelectedEdgeKind(ek)}
                className={cn(
                  "text-[11px] font-mono px-2 py-0.5 rounded capitalize transition-all cursor-pointer",
                  selectedEdgeKind === ek
                    ? "bg-white text-black font-semibold shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                {ek}
              </button>
            ))}
          </div>
        </div>

        {/* Search & Zoom Controls */}
        <div className="flex items-center gap-2">
          <div className="relative w-40 sm:w-48">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-400" />
            <input
              type="text"
              placeholder="Search symbols..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-7 w-full pl-7 text-xs font-mono bg-black border border-[#262626] rounded-md text-white placeholder:text-neutral-500 focus:outline-none focus:border-white"
            />
          </div>

          <div className="flex items-center gap-1 bg-black p-0.5 rounded-lg border border-[#262626]">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}
              title="Zoom in"
              className="p-1 rounded hover:bg-[#222] text-neutral-400 hover:text-white cursor-pointer"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
              title="Zoom out"
              className="p-1 rounded hover:bg-[#222] text-neutral-400 hover:text-white cursor-pointer"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={resetView}
              title="Reset View"
              className="p-1 rounded hover:bg-[#222] text-neutral-400 hover:text-white cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main SVG Visualization Canvas */}
      <div
        className="relative flex-1 min-h-0 w-full overflow-hidden cursor-grab active:cursor-grabbing"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
      >
        <svg
          width="100%"
          height="100%"
          onMouseDown={handleSvgMouseDown}
          className="w-full h-full"
        >
          <defs>
            <marker
              id="cg-arrow"
              viewBox="0 0 10 10"
              refX="14"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#737373" />
            </marker>
            <marker
              id="cg-arrow-renders"
              viewBox="0 0 10 10"
              refX="14"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10b981" />
            </marker>
          </defs>

          <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
            {/* Edges */}
            {filteredEdges.map((edge, i) => {
              const sp = posMap.get(edge.source);
              const tp = posMap.get(edge.target);
              if (!sp || !tp) return null;

              const style = EDGE_KIND_STYLE[edge.kind] || EDGE_KIND_STYLE.calls;
              const isHighlight =
                hovered === edge.source ||
                hovered === edge.target ||
                activeNode?.id === edge.source ||
                activeNode?.id === edge.target;

              return (
                <line
                  key={`${edge.source}-${edge.target}-${i}`}
                  x1={sp.x}
                  y1={sp.y}
                  x2={tp.x}
                  y2={tp.y}
                  stroke={isHighlight ? "#ffffff" : style.stroke}
                  strokeWidth={isHighlight ? style.width + 1.2 : style.width}
                  strokeDasharray={style.dash === "none" ? undefined : style.dash}
                  markerEnd={edge.kind === "renders" ? "url(#cg-arrow-renders)" : "url(#cg-arrow)"}
                  opacity={isHighlight ? 1 : 0.45}
                />
              );
            })}

            {/* Nodes */}
            {simNodes.map((node) => {
              const isHovered = hovered === node.id;
              const isSelected = activeNode?.id === node.id || selectedNodeId === node.id;
              const fill = NODE_KIND_BG[node.kind] || "#171717";
              const stroke = isSelected
                ? "#ffffff"
                : isHovered
                ? "#ffffff"
                : NODE_KIND_STROKE[node.kind] || "#737373";

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x},${node.y})`}
                  onMouseDown={(e) => handleNodeMouseDown(e, node)}
                  onClick={() => handleNodeClick(node)}
                  onMouseEnter={() => setHovered(node.id)}
                  onMouseLeave={() => setHovered(null)}
                  className="cursor-pointer"
                >
                  {/* Selection halo */}
                  {isSelected && (
                    <circle
                      r={RADIUS + 6}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={1.5}
                      strokeDasharray="3 3"
                      className="animate-spin"
                      style={{ animationDuration: "12s" }}
                    />
                  )}

                  {/* Node Shape */}
                  {node.kind === "class" ? (
                    <rect
                      x={-RADIUS}
                      y={-RADIUS}
                      width={RADIUS * 2}
                      height={RADIUS * 2}
                      rx={5}
                      fill={fill}
                      stroke={stroke}
                      strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1.2}
                    />
                  ) : node.kind === "component" ? (
                    <polygon
                      points={`0,${-RADIUS - 2} ${RADIUS + 2},0 0,${RADIUS + 2} ${-RADIUS - 2},0`}
                      fill={fill}
                      stroke={stroke}
                      strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1.2}
                    />
                  ) : (
                    <circle
                      r={RADIUS}
                      fill={fill}
                      stroke={stroke}
                      strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1.2}
                    />
                  )}

                  {/* Icon or Letter in Node Center */}
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill={isSelected ? "#ffffff" : NODE_KIND_COLOR[node.kind] || "#ffffff"}
                    fontSize={10}
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    {node.kind === "class"
                      ? "C"
                      : node.kind === "component"
                      ? "◇"
                      : node.kind === "method"
                      ? "m"
                      : "ƒ"}
                  </text>

                  {/* Node Label Below */}
                  <text
                    y={RADIUS + 13}
                    textAnchor="middle"
                    fill={isSelected ? "#ffffff" : isHovered ? "#ffffff" : "#a3a3a3"}
                    fontSize={10}
                    fontFamily="monospace"
                    fontWeight={isSelected ? "bold" : "normal"}
                    className="pointer-events-none"
                  >
                    {node.label.length > 18 ? node.label.slice(0, 16) + "…" : node.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {/* Floating Node Details Drawer / Popover */}
        <AnimatePresence>
          {activeNode && (
            <motion.div
              initial={{ opacity: 0, x: 20, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="absolute right-4 top-4 w-72 sm:w-80 bg-black/95 backdrop-blur-md border border-[#333] rounded-xl shadow-2xl p-4 text-xs font-mono z-20 space-y-3"
            >
              <div className="flex items-start justify-between pb-2 border-b border-[#262626]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white tracking-tight">{activeNode.label}</span>
                    <Badge variant="outline" className="text-[10px] uppercase border-[#333] text-neutral-300">
                      {activeNode.kind}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-neutral-400 mt-0.5 truncate max-w-[220px]">
                    {activeNode.file}
                  </p>
                </div>
                <button
                  onClick={() => setActiveNode(null)}
                  className="p-1 rounded hover:bg-[#222] text-neutral-400 hover:text-white cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              {activeNode.line && (
                <div className="text-[11px] text-neutral-400">
                  <span>Line Definition: </span>
                  <span className="text-white font-bold">L{activeNode.line}</span>
                </div>
              )}

              {/* Incoming Callers */}
              <div>
                <span className="text-[10px] text-neutral-500 uppercase font-semibold block mb-1">
                  Called / Imported By ({activeIncoming.length}):
                </span>
                {activeIncoming.length === 0 ? (
                  <span className="text-[11px] text-neutral-500 italic">None (entry or root module)</span>
                ) : (
                  <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                    {activeIncoming.map((edge) => (
                      <span
                        key={edge.source}
                        className="px-1.5 py-0.5 rounded bg-[#141414] border border-[#2a2a2a] text-neutral-300 text-[10px]"
                      >
                        {edge.source}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Outgoing Callees */}
              <div>
                <span className="text-[10px] text-neutral-500 uppercase font-semibold block mb-1">
                  Calls / Renders Out ({activeOutgoing.length}):
                </span>
                {activeOutgoing.length === 0 ? (
                  <span className="text-[11px] text-neutral-500 italic">None (leaf node)</span>
                ) : (
                  <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                    {activeOutgoing.map((edge) => (
                      <span
                        key={edge.target}
                        className="px-1.5 py-0.5 rounded bg-[#141414] border border-[#2a2a2a] text-neutral-300 text-[10px]"
                      >
                        {edge.target}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Legend */}
        <div className="absolute bottom-3 left-3 bg-black/85 backdrop-blur-sm border border-[#262626] rounded-lg px-3 py-1.5 text-[10px] font-mono text-neutral-400 flex items-center gap-3 z-10 pointer-events-none">
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-black border border-white" />
            <span>Class</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#171717] border border-[#a3a3a3]" />
            <span>Function</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rotate-45 bg-[#052e16] border border-[#22c55e]" />
            <span>Component</span>
          </div>
          <div className="hidden sm:flex items-center gap-1">
            <span className="text-neutral-500">|</span>
            <span>Nodes: {filteredNodes.length}</span>
            <span>Edges: {filteredEdges.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
