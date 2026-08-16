/**
 * CallGraphView — Interactive force-directed call graph visualization.
 *
 * Renders the repository's extracted function/class/component dependency graph.
 * Pure React + SVG with a lightweight spring-force simulation — no external deps.
 *
 * Supports:
 *  - Node kinds: class (square), function/method (circle), component (diamond)
 *  - Edge kinds: calls (solid), imports (dashed), inherits (thick), renders (dotted)
 *  - Drag nodes, scroll to zoom, pan
 *  - Node tooltip on hover
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { CallGraphEdge, CallGraphNode } from "@/types/repository";

const NODE_KIND_COLOR: Record<string, string> = {
  class: "#e2e8f0",
  method: "#94a3b8",
  function: "#cbd5e1",
  component: "#d1fae5",
  module: "#fef3c7",
};

const NODE_KIND_STROKE: Record<string, string> = {
  class: "#ffffff",
  method: "#64748b",
  function: "#94a3b8",
  component: "#4ade80",
  module: "#facc15",
};

const EDGE_KIND_STYLE: Record<string, { stroke: string; dash: string; width: number }> = {
  calls:    { stroke: "#404040", dash: "none",  width: 1   },
  imports:  { stroke: "#334155", dash: "4 3",   width: 1   },
  inherits: { stroke: "#e2e8f0", dash: "none",  width: 1.5 },
  renders:  { stroke: "#16a34a", dash: "2 4",   width: 1   },
};

const RADIUS = 18;
const REPULSION = 4000;
const LINK_DISTANCE = 90;
const CENTERING = 0.04;
const DAMPING = 0.86;

interface SimNode extends CallGraphNode {
  x: number; y: number; vx: number; vy: number;
}

interface Props {
  nodes: CallGraphNode[];
  edges: CallGraphEdge[];
  width?: number;
  height?: number;
}

function initSim(nodes: CallGraphNode[], w: number, h: number): SimNode[] {
  const n = nodes.length || 1;
  return nodes.map((node, i) => {
    const angle = (2 * Math.PI * i) / n;
    const r = Math.min(w, h) * 0.3;
    return { ...node, x: w / 2 + r * Math.cos(angle), y: h / 2 + r * Math.sin(angle), vx: 0, vy: 0 };
  });
}

export function CallGraphView({ nodes: rawNodes, edges: rawEdges, width = 800, height = 560 }: Props) {
  const [simNodes, setSimNodes] = useState<SimNode[]>(() => initSim(rawNodes, width, height));
  const [hovered, setHovered] = useState<string | null>(null);
  const [dragging, setDragging] = useState<{ id: string; ox: number; oy: number } | null>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [panDrag, setPanDrag] = useState<{ sx: number; sy: number; px: number; py: number } | null>(null);

  const nodesRef = useRef<SimNode[]>(simNodes);
  const alphaRef = useRef(0.3);
  const idxRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    const map = new Map<string, number>();
    rawNodes.forEach((n, i) => map.set(n.id, i));
    idxRef.current = map;
    const s = initSim(rawNodes, width, height);
    nodesRef.current = s;
    setSimNodes([...s]);
    alphaRef.current = 0.3;
  }, [rawNodes, width, height]);

  useEffect(() => {
    const id = setInterval(() => {
      if (alphaRef.current < 0.005) return;
      alphaRef.current *= 0.97;
      const ns = nodesRef.current.map(n => ({ ...n }));
      const cx = width / 2, cy = height / 2;

      for (const n of ns) {
        n.vx += (cx - n.x) * CENTERING * alphaRef.current;
        n.vy += (cy - n.y) * CENTERING * alphaRef.current;
      }

      for (let i = 0; i < ns.length; i++) {
        for (let j = i + 1; j < ns.length; j++) {
          const dx = ns[j].x - ns[i].x, dy = ns[j].y - ns[i].y;
          const d2 = dx * dx + dy * dy || 1;
          const f = REPULSION / d2;
          ns[i].vx -= f * dx; ns[i].vy -= f * dy;
          ns[j].vx += f * dx; ns[j].vy += f * dy;
        }
      }

      for (const edge of rawEdges) {
        const si = idxRef.current.get(edge.source), ti = idxRef.current.get(edge.target);
        if (si == null || ti == null || !ns[si] || !ns[ti]) continue;
        const dx = ns[ti].x - ns[si].x, dy = ns[ti].y - ns[si].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const diff = (dist - LINK_DISTANCE) / dist * 0.5 * alphaRef.current;
        ns[si].vx += dx * diff; ns[si].vy += dy * diff;
        ns[ti].vx -= dx * diff; ns[ti].vy -= dy * diff;
      }

      for (const n of ns) {
        if (dragging?.id === n.id) continue;
        n.vx *= DAMPING; n.vy *= DAMPING;
        n.x = Math.max(RADIUS + 4, Math.min(width - RADIUS - 4, n.x + n.vx));
        n.y = Math.max(RADIUS + 4, Math.min(height - RADIUS - 4, n.y + n.vy));
      }

      nodesRef.current = ns;
      setSimNodes([...ns]);
    }, 16);
    return () => clearInterval(id);
  }, [rawEdges, width, height, dragging]);

  const posMap = useRef(new Map<string, { x: number; y: number }>());
  useEffect(() => {
    const m = new Map<string, { x: number; y: number }>();
    for (const n of simNodes) m.set(n.id, { x: n.x, y: n.y });
    posMap.current = m;
  }, [simNodes]);

  const onNodeDown = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const n = nodesRef.current.find(x => x.id === id);
    if (!n) return;
    setDragging({ id, ox: e.clientX - n.x, oy: e.clientY - n.y });
    alphaRef.current = 0.3;
  }, []);

  const onMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (dragging) {
      const ns = nodesRef.current.map(n =>
        n.id === dragging.id ? { ...n, x: e.clientX - dragging.ox, y: e.clientY - dragging.oy, vx: 0, vy: 0 } : n
      );
      nodesRef.current = ns;
      setSimNodes([...ns]);
    } else if (panDrag) {
      setPan({ x: panDrag.px + e.clientX - panDrag.sx, y: panDrag.py + e.clientY - panDrag.sy });
    }
  }, [dragging, panDrag]);

  const onUp = useCallback(() => { setDragging(null); setPanDrag(null); }, []);

  const onSvgDown = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    setPanDrag({ sx: e.clientX, sy: e.clientY, px: pan.x, py: pan.y });
  }, [pan]);

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom(z => Math.max(0.25, Math.min(3, z - e.deltaY * 0.001)));
  }, []);

  function renderShape(n: SimNode) {
    const fill = NODE_KIND_COLOR[n.kind] ?? "#e2e8f0";
    const stroke = NODE_KIND_STROKE[n.kind] ?? "#ffffff";
    const hl = hovered === n.id;
    if (n.kind === "class") {
      const s = RADIUS * 1.4;
      return <rect x={n.x - s / 2} y={n.y - s / 2} width={s} height={s} rx={3} fill={fill} stroke={stroke} strokeWidth={hl ? 2 : 1} />;
    }
    if (n.kind === "component") {
      const d = RADIUS * 1.3;
      return <polygon points={`${n.x},${n.y - d} ${n.x + d},${n.y} ${n.x},${n.y + d} ${n.x - d},${n.y}`} fill={fill} stroke={stroke} strokeWidth={hl ? 2 : 1} />;
    }
    return <circle cx={n.x} cy={n.y} r={hl ? RADIUS + 2 : RADIUS} fill={fill} stroke={stroke} strokeWidth={hl ? 2 : 1} />;
  }

  function renderEdge(edge: CallGraphEdge, i: number) {
    const sp = posMap.current.get(edge.source);
    const tp = posMap.current.get(edge.target);
    if (!sp || !tp) return null;
    const s = EDGE_KIND_STYLE[edge.kind] ?? EDGE_KIND_STYLE.calls;
    const dx = tp.x - sp.x, dy = tp.y - sp.y;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    return (
      <line key={i}
        x1={sp.x} y1={sp.y}
        x2={tp.x - dx / len * (RADIUS + 3)} y2={tp.y - dy / len * (RADIUS + 3)}
        stroke={s.stroke} strokeWidth={s.width}
        strokeDasharray={s.dash === "none" ? undefined : s.dash}
        opacity={0.55}
      />
    );
  }

  if (rawNodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
        <span className="font-mono text-xs">No call graph — re-index repository to extract symbols.</span>
      </div>
    );
  }

  const LEGEND_NODES = [
    { kind: "class", label: "Class / Model" },
    { kind: "function", label: "Function" },
    { kind: "component", label: "Component" },
  ];
  const LEGEND_EDGES = [
    { kind: "calls", label: "calls" },
    { kind: "imports", label: "imports" },
    { kind: "inherits", label: "inherits" },
    { kind: "renders", label: "renders" },
  ];

  const hNode = simNodes.find(x => x.id === hovered);

  return (
    <div className="relative w-full h-full bg-black rounded-xl overflow-hidden border border-[#1f1f1f]">
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
          className="px-2.5 py-1 rounded-md bg-[#141414] border border-[#2a2a2a] text-[10px] font-mono text-neutral-400 hover:text-white transition-colors">
          Reset
        </button>
        <span className="text-[10px] font-mono text-[#404040]">
          {rawNodes.length} nodes · {rawEdges.length} edges · scroll=zoom · drag=pan
        </span>
      </div>

      <div className="absolute bottom-3 left-3 z-10 flex flex-col gap-1.5 bg-[#0a0a0a]/90 border border-[#1f1f1f] rounded-lg p-2.5">
        <span className="text-[9px] font-mono uppercase tracking-wider text-[#404040] mb-0.5">Legend</span>
        {LEGEND_NODES.map(l => (
          <div key={l.kind} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm shrink-0"
              style={{ background: NODE_KIND_COLOR[l.kind], border: `1px solid ${NODE_KIND_STROKE[l.kind]}` }} />
            <span className="text-[10px] font-mono text-neutral-500">{l.label}</span>
          </div>
        ))}
        <div className="h-px bg-[#1f1f1f] my-0.5" />
        {LEGEND_EDGES.map(l => {
          const s = EDGE_KIND_STYLE[l.kind];
          return (
            <div key={l.kind} className="flex items-center gap-2">
              <svg width="20" height="6" className="shrink-0">
                <line x1="0" y1="3" x2="20" y2="3" stroke={s.stroke} strokeWidth={s.width}
                  strokeDasharray={s.dash === "none" ? undefined : s.dash} />
              </svg>
              <span className="text-[10px] font-mono text-neutral-500">{l.label}</span>
            </div>
          );
        })}
      </div>

      {hovered && hNode && (
        <div className="absolute z-20 pointer-events-none px-3 py-2 rounded-lg bg-[#0f0f0f] border border-[#2a2a2a] shadow-xl"
          style={{ left: Math.min(hNode.x * zoom + pan.x + RADIUS + 8, width - 200), top: Math.max(hNode.y * zoom + pan.y - 36, 8) }}>
          <p className="text-xs font-mono text-white font-semibold">{hNode.label}</p>
          <p className="text-[10px] font-mono text-neutral-500 mt-0.5">{hNode.kind} · {hNode.file.split("/").slice(-2).join("/")}</p>
          {hNode.line > 0 && <p className="text-[10px] font-mono text-neutral-600">line {hNode.line}</p>}
        </div>
      )}

      <svg width={width} height={height}
        className="cursor-grab active:cursor-grabbing select-none"
        onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}
        onMouseDown={onSvgDown} onWheel={onWheel}>
        <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
          <g opacity={0.6}>{rawEdges.map((e, i) => renderEdge(e, i))}</g>
          {simNodes.map(n => (
            <g key={n.id}
              onMouseDown={e => onNodeDown(e, n.id)}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: "grab" }}>
              {renderShape(n)}
              <text x={n.x} y={n.y + RADIUS + 11} textAnchor="middle" fontSize={9}
                fontFamily="'Geist Mono', monospace"
                fill={hovered === n.id ? "#ffffff" : "#555555"}
                style={{ pointerEvents: "none", userSelect: "none" }}>
                {n.label.length > 14 ? n.label.slice(0, 13) + "…" : n.label}
              </text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
