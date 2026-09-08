/**
 * CallGraphView — Interactive force-directed call graph visualization.
 *
 * Renders the repository's extracted function/class/component dependency graph.
 * Pure React + SVG with a lightweight spring-force simulation.
 *
 * Supports:
 *  - 5 Explicit Graph States: "not_analyzed" | "analyzing" | "analyzed" | "zero_edges" | "failed"
 *  - Large-graph bounded presentation: Initial 50 nodes by degree with 1-hop caller/callee expansion
 *  - Node kinds: class (square), function/method (circle), component (diamond)
 *  - Edge kinds: calls (solid), imports (dashed), inherits (thick), renders (dotted)
 *  - Filtering by Node Kind & Edge Kind
 *  - Node search with live highlighting & automatic expansion
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
  RefreshCw,
  Network,
  AlertCircle,
  Maximize2,
  Minimize2,
  Info,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
const INITIAL_BOUNDED_LIMIT = 50;

function normalizeKind(kind?: string): string {
  if (!kind) return "function";
  const k = kind.toLowerCase().trim();
  if (k === "classes") return "class";
  if (k === "functions") return "function";
  if (k === "methods") return "method";
  if (k === "components") return "component";
  if (k === "modules") return "module";
  return k;
}

interface SimNode extends CallGraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export type CallGraphState = "not_analyzed" | "analyzing" | "analyzed" | "zero_edges" | "failed";

export interface CallGraphViewProps {
  nodes: CallGraphNode[];
  edges: CallGraphEdge[];
  width?: number;
  height?: number;
  selectedNodeId?: string | null;
  onSelectNode?: (node: CallGraphNode | null) => void;
  status?: CallGraphState;
  errorMessage?: string | null;
  onTriggerAnalyze?: () => void;
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
  status,
  errorMessage,
  onTriggerAnalyze,
}: CallGraphViewProps) {
  // Determine effective graph state
  const effectiveState: CallGraphState = useMemo(() => {
    if (status) return status;
    if (rawNodes.length === 0) return "not_analyzed";
    if (rawEdges.length === 0) return "zero_edges";
    return "analyzed";
  }, [status, rawNodes.length, rawEdges.length]);

  const [selectedKind, setSelectedKind] = useState<string>("all");
  const [selectedEdgeKind, setSelectedEdgeKind] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNode, setActiveNode] = useState<CallGraphNode | null>(null);

  // Large-graph bounding controls
  const isLargeGraph = rawNodes.length > INITIAL_BOUNDED_LIMIT;
  const [isBounded, setIsBounded] = useState<boolean>(isLargeGraph);
  const [expandedNeighborhoodIds, setExpandedNeighborhoodIds] = useState<Set<string>>(new Set());

  // Degree map (count of connections per node ID)
  const nodeDegrees = useMemo(() => {
    const degrees = new Map<string, number>();
    for (const edge of rawEdges) {
      degrees.set(edge.source, (degrees.get(edge.source) || 0) + 1);
      degrees.set(edge.target, (degrees.get(edge.target) || 0) + 1);
    }
    return degrees;
  }, [rawEdges]);

  // Expand 1-hop callers and callees when activeNode changes
  useEffect(() => {
    if (!activeNode) return;
    const directNeighbors = new Set<string>();
    directNeighbors.add(activeNode.id);
    for (const edge of rawEdges) {
      if (edge.source === activeNode.id || edge.source === activeNode.label) {
        directNeighbors.add(edge.target);
      }
      if (edge.target === activeNode.id || edge.target === activeNode.label) {
        directNeighbors.add(edge.source);
      }
    }
    setExpandedNeighborhoodIds((prev) => {
      const next = new Set(prev);
      directNeighbors.forEach((id) => next.add(id));
      return next;
    });
  }, [activeNode, rawEdges]);

  // Initial bounded 50 nodes by degree + search matches + 1-hop expansions
  const boundedNodeIdSet = useMemo(() => {
    if (!isBounded) return null; // all nodes allowed

    // Sort by degree descending, take first 50
    const sorted = [...rawNodes].sort((a, b) => {
      const degA = nodeDegrees.get(a.id) || 0;
      const degB = nodeDegrees.get(b.id) || 0;
      return degB - degA;
    });

    const allowed = new Set<string>(sorted.slice(0, INITIAL_BOUNDED_LIMIT).map((n) => n.id));

    // Always include expanded neighborhood IDs
    expandedNeighborhoodIds.forEach((id) => allowed.add(id));

    // Always include nodes matching search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      rawNodes.forEach((n) => {
        if (
          n.label.toLowerCase().includes(q) ||
          n.id.toLowerCase().includes(q) ||
          n.file.toLowerCase().includes(q)
        ) {
          allowed.add(n.id);
        }
      });
    }

    return allowed;
  }, [isBounded, rawNodes, nodeDegrees, expandedNeighborhoodIds, searchQuery]);

  // Filter nodes (kind + search + large-graph bounding)
  const filteredNodes = useMemo(() => {
    return rawNodes.filter((node) => {
      if (boundedNodeIdSet && !boundedNodeIdSet.has(node.id)) {
        return false;
      }
      const nodeKind = normalizeKind(node.kind);
      const matchesKind = selectedKind === "all" || nodeKind === selectedKind.toLowerCase();
      const matchesSearch =
        !searchQuery ||
        (node.label || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (node.file || "").toLowerCase().includes(searchQuery.toLowerCase());
      return matchesKind && matchesSearch;
    });
  }, [rawNodes, boundedNodeIdSet, selectedKind, searchQuery]);

  const activeNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  // Authoritative edge resolution: map edge source & target to verified node IDs
  const filteredEdges = useMemo(() => {
    const results: CallGraphEdge[] = [];
    for (const edge of rawEdges) {
      const edgeKind = (edge.kind || "").toLowerCase().trim();
      const matchesKind = selectedEdgeKind === "all" || edgeKind === selectedEdgeKind.toLowerCase();
      if (!matchesKind) continue;

      let sId: string | null = null;
      if (activeNodeIds.has(edge.source)) {
        sId = edge.source;
      } else {
        const matches = filteredNodes.filter((n) => n.label === edge.source);
        if (matches.length === 1) sId = matches[0].id;
      }

      let tId: string | null = null;
      if (activeNodeIds.has(edge.target)) {
        tId = edge.target;
      } else {
        const matches = filteredNodes.filter((n) => n.label === edge.target);
        if (matches.length === 1) tId = matches[0].id;
      }

      if (sId && tId && sId !== tId && activeNodeIds.has(sId) && activeNodeIds.has(tId)) {
        results.push({ ...edge, source: sId, target: tId });
      }
    }
    return results;
  }, [rawEdges, selectedEdgeKind, activeNodeIds, filteredNodes]);

  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ w: width, h: height });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 50 && entry.contentRect.height > 50) {
          setCanvasSize({
            w: Math.round(entry.contentRect.width),
            h: Math.round(entry.contentRect.height),
          });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const [simNodes, setSimNodes] = useState<SimNode[]>(() => initSim(filteredNodes, canvasSize.w, canvasSize.h));
  const [hovered, setHovered] = useState<string | null>(null);
  const [dragging, setDragging] = useState<{ id: string; ox: number; oy: number } | null>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [panDrag, setPanDrag] = useState<{ sx: number; sy: number; px: number; py: number } | null>(null);
  const panStartRef = useRef<{ x: number; y: number; time: number } | null>(null);

  const nodesRef = useRef<SimNode[]>(simNodes);
  const alphaRef = useRef(0.35);
  const idxRef = useRef<Map<string, number>>(new Map());

  // Sync external selectedNodeId prop with internal activeNode
  useEffect(() => {
    if (selectedNodeId === undefined) return;
    if (!selectedNodeId) {
      setActiveNode(null);
    } else {
      const found = rawNodes.find((n) => n.id === selectedNodeId);
      if (found) {
        setActiveNode(found);
      }
    }
  }, [selectedNodeId, rawNodes]);

  // Global Escape key listener to clear selection
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (activeNode || selectedNodeId) {
          setActiveNode(null);
          onSelectNode?.(null);
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeNode, selectedNodeId, onSelectNode]);

  // Re-sync simulation when filtered nodes or canvas dimensions change
  useEffect(() => {
    const map = new Map<string, number>();
    filteredNodes.forEach((n, i) => map.set(n.id, i));
    idxRef.current = map;
    const s = initSim(filteredNodes, canvasSize.w, canvasSize.h);
    nodesRef.current = s;
    setSimNodes([...s]);
    alphaRef.current = 0.35;
  }, [filteredNodes, canvasSize.w, canvasSize.h]);

  // Spring physics loop
  useEffect(() => {
    const id = setInterval(() => {
      if (alphaRef.current < 0.004) return;
      alphaRef.current *= 0.97;
      const ns = nodesRef.current.map((n) => ({ ...n }));
      const cx = canvasSize.w / 2,
        cy = canvasSize.h / 2;

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
        if (si !== undefined && ti !== undefined && si !== ti) {
          const dx = ns[ti].x - ns[si].x;
          const dy = ns[ti].y - ns[si].y;
          const dist = Math.hypot(dx, dy) || 1;
          const diff = dist - LINK_DISTANCE;
          const force = diff * 0.08 * alphaRef.current;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          ns[si].vx += fx;
          ns[si].vy += fy;
          ns[ti].vx -= fx;
          ns[ti].vy -= fy;
        }
      }

      for (const n of ns) {
        n.vx *= DAMPING;
        n.vy *= DAMPING;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(RADIUS + 10, Math.min(canvasSize.w - RADIUS - 10, n.x));
        n.y = Math.max(RADIUS + 10, Math.min(canvasSize.h - RADIUS - 10, n.y));
      }

      nodesRef.current = ns;
      setSimNodes(ns);
    }, 25);

    return () => clearInterval(id);
  }, [filteredEdges, canvasSize.w, canvasSize.h]);

  // Drag handlers
  const handleNodeMouseDown = useCallback(
    (e: React.MouseEvent, node: SimNode) => {
      e.stopPropagation();
      setDragging({ id: node.id, ox: e.clientX - node.x * zoom - pan.x, oy: e.clientY - node.y * zoom - pan.y });
    },
    [zoom, pan]
  );

  const handleSvgMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      panStartRef.current = { x: e.clientX, y: e.clientY, time: Date.now() };
      setPanDrag({ sx: e.clientX, sy: e.clientY, px: pan.x, py: pan.y });
    },
    [pan]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) {
        const nx = (e.clientX - dragging.ox - pan.x) / zoom;
        const ny = (e.clientY - dragging.oy - pan.y) / zoom;
        nodesRef.current = nodesRef.current.map((n) => (n.id === dragging.id ? { ...n, x: nx, y: ny, vx: 0, vy: 0 } : n));
        setSimNodes([...nodesRef.current]);
        alphaRef.current = 0.15;
      } else if (panDrag) {
        setPan({ x: panDrag.px + (e.clientX - panDrag.sx), y: panDrag.py + (e.clientY - panDrag.sy) });
      }
    },
    [dragging, panDrag, pan.x, pan.y, zoom]
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (panDrag && panStartRef.current) {
        const dx = Math.abs(e.clientX - panStartRef.current.x);
        const dy = Math.abs(e.clientY - panStartRef.current.y);
        const dt = Date.now() - panStartRef.current.time;
        if (dx < 4 && dy < 4 && dt < 250) {
          setActiveNode(null);
          onSelectNode?.(null);
        }
      }
      setDragging(null);
      setPanDrag(null);
      panStartRef.current = null;
    },
    [panDrag, onSelectNode]
  );

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((z) => Math.min(3, Math.max(0.2, z * factor)));
  }, []);

  const handleResetView = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
    alphaRef.current = 0.35;
  };

  const handleSelectNodeClick = (e: React.MouseEvent, node: SimNode) => {
    e.stopPropagation();
    setActiveNode(node);
    onSelectNode?.(node);
  };

  // Node position map
  const posMap = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    for (const n of simNodes) map.set(n.id, { x: n.x, y: n.y });
    return map;
  }, [simNodes]);

  // Callers and callees for the active node inspector
  const { activeIncoming, activeOutgoing } = useMemo(() => {
    if (!activeNode) return { activeIncoming: [], activeOutgoing: [] };
    const inc: CallGraphEdge[] = [];
    const out: CallGraphEdge[] = [];
    for (const edge of rawEdges) {
      if (edge.target === activeNode.id || edge.target === activeNode.label) {
        inc.push(edge);
      }
      if (edge.source === activeNode.id || edge.source === activeNode.label) {
        out.push(edge);
      }
    }
    return { activeIncoming: inc, activeOutgoing: out };
  }, [activeNode, rawEdges]);

  // =========================================================================
  // STATE 1: NOT ANALYZED
  // =========================================================================
  if (effectiveState === "not_analyzed") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#070707] h-full min-h-[400px]">
        <Network className="w-10 h-10 text-neutral-600 mb-3" />
        <h3 className="text-sm font-semibold text-white tracking-tight">AST Analysis Not Available</h3>
        <p className="text-xs text-neutral-500 max-w-sm mt-1 mb-4">
          Repository has not been parsed for AST symbols. Trigger re-indexing to extract the call graph.
        </p>
        {onTriggerAnalyze && (
          <Button
            size="sm"
            onClick={onTriggerAnalyze}
            className="h-8 px-4 text-xs font-mono bg-white text-black hover:bg-neutral-200 cursor-pointer"
          >
            Extract AST Now
          </Button>
        )}
      </div>
    );
  }

  // =========================================================================
  // STATE 2: ANALYZING
  // =========================================================================
  if (effectiveState === "analyzing") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#070707] h-full min-h-[400px]">
        <RefreshCw className="w-8 h-8 text-amber-400 animate-spin mb-3" />
        <h3 className="text-sm font-semibold text-white tracking-tight">Analyzing AST Call Graph</h3>
        <p className="text-xs text-neutral-500 max-w-sm mt-1">
          Extracting tree-sitter classes, methods, and functions...
        </p>
      </div>
    );
  }

  // =========================================================================
  // STATE 3: FAILED
  // =========================================================================
  if (effectiveState === "failed") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#070707] h-full min-h-[400px]">
        <AlertCircle className="w-10 h-10 text-red-500 mb-3" />
        <h3 className="text-sm font-semibold text-white tracking-tight">AST Analysis Failed</h3>
        <p className="text-xs text-red-400 max-w-sm mt-1 mb-4 font-mono">
          {errorMessage || "Tree-sitter AST extraction failed for this repository."}
        </p>
        {onTriggerAnalyze && (
          <Button
            size="sm"
            onClick={onTriggerAnalyze}
            className="h-8 px-4 text-xs font-mono bg-white text-black hover:bg-neutral-200 cursor-pointer"
          >
            Retry AST Extraction
          </Button>
        )}
      </div>
    );
  }

  // =========================================================================
  // STATES 4 & 5: ANALYZED & ZERO_EDGES (Full Interactive Graph Canvas)
  // =========================================================================
  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#070707] relative select-none">
      {/* Top Controls Toolbar */}
      <div className="px-4 py-2.5 border-b border-[#1e1e1e] bg-[#0a0a0a] flex flex-wrap items-center justify-between gap-3 shrink-0 z-10">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Node Kind Filter */}
          <div className="flex items-center gap-1 text-xs font-mono text-neutral-400">
            <span className="text-[11px] text-neutral-500">Kind:</span>
            {["all", "class", "function", "method", "component"].map((kind) => (
              <button
                key={kind}
                onClick={() => setSelectedKind(kind)}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] uppercase font-mono transition-colors cursor-pointer",
                  selectedKind === kind
                    ? "bg-white text-black font-bold"
                    : "text-neutral-400 hover:text-white hover:bg-[#1f1f1f]"
                )}
              >
                {kind}
              </button>
            ))}
          </div>

          {/* Edge Kind Filter */}
          <div className="flex items-center gap-1 text-xs font-mono text-neutral-400 ml-2">
            <span className="text-[11px] text-neutral-500">Edge:</span>
            {["all", "calls", "imports", "inherits", "renders"].map((ek) => (
              <button
                key={ek}
                onClick={() => setSelectedEdgeKind(ek)}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] uppercase font-mono transition-colors cursor-pointer",
                  selectedEdgeKind === ek
                    ? "bg-neutral-200 text-black font-bold"
                    : "text-neutral-400 hover:text-white hover:bg-[#1f1f1f]"
                )}
              >
                {ek}
              </button>
            ))}
          </div>
        </div>

        {/* Right Tools: Search, Zoom, Bounding */}
        <div className="flex items-center gap-2">
          {/* Search Box */}
          <div className="relative w-40 sm:w-48">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-500" />
            <input
              type="text"
              placeholder="Search symbols..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-7 pl-6 pr-6 text-xs font-mono bg-[#141414] border border-[#262626] rounded text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:border-neutral-400"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white p-0.5 cursor-pointer"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            )}
          </div>

          {/* Large-Graph Presentation Bounding Toggle */}
          {isLargeGraph && (
            <button
              onClick={() => setIsBounded(!isBounded)}
              className={cn(
                "h-7 px-2 text-[10px] font-mono rounded border transition-colors flex items-center gap-1 cursor-pointer",
                isBounded
                  ? "bg-amber-950/40 text-amber-300 border-amber-800/60 hover:bg-amber-950/60"
                  : "bg-[#141414] text-neutral-300 border-[#262626] hover:bg-[#1f1f1f]"
              )}
              title={
                isBounded
                  ? `Presentation bounded to top 50 nodes + 1-hop expansions. Click to show all ${rawNodes.length} nodes.`
                  : `Showing all ${rawNodes.length} nodes. Click to bound to top 50.`
              }
            >
              {isBounded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
              <span>{isBounded ? `Bounded (${filteredNodes.length}/${rawNodes.length})` : `All (${rawNodes.length})`}</span>
            </button>
          )}

          {/* Zoom & Reset Controls */}
          <div className="flex items-center border border-[#262626] rounded bg-[#141414] overflow-hidden">
            <button
              onClick={() => setZoom((z) => Math.min(3, z * 1.2))}
              className="p-1.5 text-neutral-400 hover:text-white hover:bg-[#202020] cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3 h-3" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.2, z * 0.8))}
              className="p-1.5 text-neutral-400 hover:text-white hover:bg-[#202020] cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3 h-3" />
            </button>
            <button
              onClick={handleResetView}
              className="p-1.5 text-neutral-400 hover:text-white hover:bg-[#202020] cursor-pointer"
              title="Reset View"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Notice Banner for Zero Edges State */}
      {effectiveState === "zero_edges" && (
        <div className="px-4 py-1.5 bg-[#141414] border-b border-[#222222] flex items-center justify-between text-xs font-mono text-neutral-400 shrink-0">
          <div className="flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-amber-400" />
            <span>Zero Call Graph Edges: Symbols are isolated or inter-procedural calls were not detected in AST parsing.</span>
          </div>
          <span className="text-[10px] text-neutral-500">{filteredNodes.length} symbols loaded</span>
        </div>
      )}

      {/* SVG Canvas Container */}
      <div
        ref={containerRef}
        className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing overflow-hidden"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onMouseDown={handleSvgMouseDown}
      >
        <svg className="w-full h-full block">
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Edge Definitions & Arrows */}
            <defs>
              <marker
                id="arrowhead-calls"
                markerWidth="8"
                markerHeight="8"
                refX="22"
                refY="4"
                orient="auto"
              >
                <polygon points="0 0, 8 4, 0 8" fill="#737373" />
              </marker>
              <marker
                id="arrowhead-imports"
                markerWidth="8"
                markerHeight="8"
                refX="22"
                refY="4"
                orient="auto"
              >
                <polygon points="0 0, 8 4, 0 8" fill="#3b82f6" />
              </marker>
            </defs>

            {/* Render Edges */}
            {filteredEdges.map((edge, idx) => {
              const sp = posMap.get(edge.source);
              const tp = posMap.get(edge.target);
              if (!sp || !tp) return null;

              const style = EDGE_KIND_STYLE[edge.kind] || EDGE_KIND_STYLE.calls;
              const isHighlighted =
                activeNode &&
                (edge.source === activeNode.id || edge.target === activeNode.id);

              return (
                <line
                  key={`${edge.source}-${edge.target}-${idx}`}
                  x1={sp.x}
                  y1={sp.y}
                  x2={tp.x}
                  y2={tp.y}
                  stroke={isHighlighted ? "#ffffff" : style.stroke}
                  strokeWidth={isHighlighted ? style.width + 1.2 : style.width}
                  strokeDasharray={style.dash === "none" ? undefined : style.dash}
                  markerEnd={edge.kind === "imports" ? "url(#arrowhead-imports)" : "url(#arrowhead-calls)"}
                  opacity={isHighlighted ? 1 : 0.6}
                />
              );
            })}

            {/* Render Nodes */}
            {simNodes.map((node) => {
              const kind = normalizeKind(node.kind);
              const fill = NODE_KIND_BG[kind] || "#171717";
              const stroke = NODE_KIND_STROKE[kind] || "#ffffff";
              const isSelected = activeNode?.id === node.id;
              const isHovered = hovered === node.id;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onMouseEnter={() => setHovered(node.id)}
                  onMouseLeave={() => setHovered(null)}
                  onMouseDown={(e) => handleNodeMouseDown(e, node)}
                  onClick={(e) => handleSelectNodeClick(e, node)}
                  className="cursor-pointer"
                >
                  {/* Selection Ring */}
                  {isSelected && (
                    <circle
                      r={RADIUS + 6}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={2}
                      strokeDasharray="3 3"
                    />
                  )}

                  {/* Node Shape */}
                  {kind === "class" ? (
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
                  ) : kind === "component" ? (
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
                    fill={isSelected ? "#ffffff" : NODE_KIND_COLOR[kind] || "#ffffff"}
                    fontSize={10}
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    {kind === "class"
                      ? "C"
                      : kind === "component"
                      ? "◇"
                      : kind === "method"
                      ? "m"
                      : kind === "module"
                      ? "M"
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
                    {(() => {
                      const text = node.label || node.id || "";
                      return text.length > 18 ? text.slice(0, 16) + "…" : text;
                    })()}
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
              onClick={(e) => e.stopPropagation()}
              onMouseDown={(e) => e.stopPropagation()}
              className="absolute right-4 top-4 w-72 sm:w-84 max-w-[calc(100%-2rem)] bg-black/95 backdrop-blur-md border border-[#333] rounded-xl shadow-2xl p-4 text-xs font-mono z-20 space-y-3"
            >
              <div className="flex items-start justify-between pb-2 border-b border-[#262626]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white tracking-tight">{activeNode.label}</span>
                    <Badge variant="outline" className="text-[10px] uppercase border-[#333] text-neutral-300">
                      {activeNode.kind}
                    </Badge>
                  </div>
                  <p className="text-[10px] text-neutral-500 font-mono mt-0.5 break-all">
                    {activeNode.id}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveNode(null);
                    onSelectNode?.(null);
                  }}
                  className="p-1 rounded hover:bg-[#222] text-neutral-400 hover:text-white cursor-pointer"
                  title="Close Inspector"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="space-y-1 text-[11px] text-neutral-400">
                <div>
                  <span className="text-neutral-500">File: </span>
                  <span className="text-neutral-200">{activeNode.file}</span>
                </div>
                {activeNode.line !== undefined && activeNode.line > 0 && (
                  <div>
                    <span className="text-neutral-500">Line: </span>
                    <span className="text-neutral-200">L{activeNode.line}</span>
                  </div>
                )}
              </div>

              {/* Incoming Callers */}
              <div>
                <span className="text-[10px] text-neutral-500 uppercase font-semibold block mb-1">
                  Called / Imported By ({activeIncoming.length}):
                </span>
                {activeIncoming.length === 0 ? (
                  <span className="text-[11px] text-neutral-500 italic">None (entry or root module)</span>
                ) : (
                  <div className="flex flex-col gap-1 max-h-28 overflow-y-auto">
                    {activeIncoming.map((edge, idx) => {
                      const matched = rawNodes.find((n) => n.id === edge.source || n.label === edge.source);
                      return (
                        <button
                          key={`${edge.source}-${idx}`}
                          onClick={() => matched && setActiveNode(matched)}
                          className="flex items-center justify-between px-2 py-1 rounded bg-[#141414] border border-[#2a2a2a] text-neutral-300 text-[10px] hover:border-neutral-400 text-left cursor-pointer"
                        >
                          <span className="truncate max-w-[160px]">{matched?.label || edge.source}</span>
                          <Badge variant="outline" className="text-[8px] uppercase border-[#333] text-neutral-400">
                            {edge.kind}
                          </Badge>
                        </button>
                      );
                    })}
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
                  <div className="flex flex-col gap-1 max-h-28 overflow-y-auto">
                    {activeOutgoing.map((edge, idx) => {
                      const matched = rawNodes.find((n) => n.id === edge.target || n.label === edge.target);
                      return (
                        <button
                          key={`${edge.target}-${idx}`}
                          onClick={() => matched && setActiveNode(matched)}
                          className="flex items-center justify-between px-2 py-1 rounded bg-[#141414] border border-[#2a2a2a] text-neutral-300 text-[10px] hover:border-neutral-400 text-left cursor-pointer"
                        >
                          <span className="truncate max-w-[160px]">{matched?.label || edge.target}</span>
                          <Badge variant="outline" className="text-[8px] uppercase border-[#333] text-neutral-400">
                            {edge.kind}
                          </Badge>
                        </button>
                      );
                    })}
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
            <span>Visible Nodes: {filteredNodes.length}</span>
            <span>Edges: {filteredEdges.length}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
