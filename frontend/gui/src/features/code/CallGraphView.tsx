import React, { useState, useMemo } from "react";
import { Network, AlertCircle, Loader2, Search, Info, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import type { CallGraphNode, CallGraphEdge } from "../../types/api";
import { Input } from "../../components/Input";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { cn } from "../../lib/utils";

interface CallGraphViewProps {
  status?: "not_analyzed" | "analyzing" | "analyzed" | "zero_edges" | "failed";
  nodes?: CallGraphNode[];
  edges?: CallGraphEdge[];
  error?: string | null;
  onAnalyze?: () => void;
}

export const CallGraphView: React.FC<CallGraphViewProps> = ({
  status = "not_analyzed",
  nodes = [],
  edges = [],
  error,
  onAnalyze,
}) => {
  const [search, setSearch] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  // Filter nodes according to search query
  const filteredNodes = useMemo(() => {
    if (!search.trim()) return nodes.slice(0, 50);
    const q = search.toLowerCase();
    return nodes.filter(
      (n) => n.label.toLowerCase().includes(q) || n.file.toLowerCase().includes(q)
    ).slice(0, 50);
  }, [nodes, search]);

  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  // Compute incoming callers and outgoing callees for the selected node
  const { callers, callees } = useMemo(() => {
    if (!selectedNodeId) return { callers: [], callees: [] };
    const inEdges = edges.filter((e) => e.target === selectedNodeId);
    const outEdges = edges.filter((e) => e.source === selectedNodeId);

    const inNodes = inEdges
      .map((e) => nodes.find((n) => n.id === e.source))
      .filter((n): n is CallGraphNode => Boolean(n));
    const outNodes = outEdges
      .map((e) => nodes.find((n) => n.id === e.target))
      .filter((n): n is CallGraphNode => Boolean(n));

    return { callers: inNodes, callees: outNodes };
  }, [nodes, edges, selectedNodeId]);

  // 1. Not Analyzed State
  if (status === "not_analyzed") {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center border border-white/[0.04] rounded-xl bg-white/[0.01]">
        <div className="p-3.5 rounded-xl bg-white/[0.04] text-slate-400 border border-white/[0.06] mb-3">
          <Network className="w-5 h-5 text-sky-400" />
        </div>
        <h4 className="text-sm font-semibold text-slate-200">AST Call Graph Not Analyzed</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1 mb-4">
          Index this repository to extract deterministic function calls, class hierarchies, and symbol relationships.
        </p>
        {onAnalyze && (
          <Button size="sm" onClick={onAnalyze}>
            Index Repository
          </Button>
        )}
      </div>
    );
  }

  // 2. Analyzing State
  if (status === "analyzing") {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center border border-white/[0.04] rounded-xl bg-white/[0.01]">
        <Loader2 className="w-6 h-6 text-sky-400 animate-spin mb-3" />
        <h4 className="text-sm font-semibold text-slate-200">Analyzing Call Graph...</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1">
          Parsing deterministic AST nodes across Python and TypeScript source files.
        </p>
      </div>
    );
  }

  // 3. Failed State
  if (status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center border border-rose-500/20 rounded-xl bg-rose-500/[0.02]">
        <AlertCircle className="w-6 h-6 text-rose-400 mb-3" />
        <h4 className="text-sm font-semibold text-rose-200">AST Analysis Failed</h4>
        <p className="text-xs text-rose-400/80 max-w-sm mt-1 mb-4">
          {error || "An error occurred while parsing the syntax tree."}
        </p>
        {onAnalyze && (
          <Button size="sm" variant="danger" onClick={onAnalyze}>
            Retry Analysis
          </Button>
        )}
      </div>
    );
  }

  // 4. Zero Edges State
  if (status === "zero_edges" || nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center border border-white/[0.04] rounded-xl bg-white/[0.01]">
        <Info className="w-6 h-6 text-amber-400 mb-3" />
        <h4 className="text-sm font-semibold text-slate-200">No Call Graph Edges Discovered</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1">
          The syntax tree contains no cross-function calls or relations matching the deterministic parser rules.
        </p>
      </div>
    );
  }

  // 5. Analyzed State: Render interactive node-edge graph view
  return (
    <div className="flex flex-col gap-3">
      {/* Top Toolbar: Search + Stats + Zoom controls */}
      <div className="flex items-center justify-between gap-4 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]">
        <div className="w-64">
          <Input
            placeholder="Filter symbols..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            icon={<Search className="w-3.5 h-3.5" />}
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <span>
              <strong className="text-slate-200 font-mono">{nodes.length}</strong> nodes
            </span>
            <span className="text-white/[0.1]">•</span>
            <span>
              <strong className="text-slate-200 font-mono">{edges.length}</strong> edges
            </span>
          </div>

          <div className="flex items-center gap-1 border-l border-white/[0.06] pl-3">
            <button
              onClick={() => setZoom((z) => Math.min(z + 0.15, 2))}
              className="p-1 text-slate-400 hover:text-white rounded-md hover:bg-white/[0.06]"
              title="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(z - 0.15, 0.5))}
              className="p-1 text-slate-400 hover:text-white rounded-md hover:bg-white/[0.06]"
              title="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="p-1 text-slate-400 hover:text-white rounded-md hover:bg-white/[0.06]"
              title="Reset view"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Graph Grid: Left Canvas + Right Symbol Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 min-h-[380px]">
        {/* Graph Canvas */}
        <div className="lg:col-span-2 relative bg-[#0c0e14] border border-white/[0.06] rounded-xl overflow-hidden p-4 flex flex-col justify-between">
          <div
            className="flex-1 grid grid-cols-2 sm:grid-cols-3 gap-2 overflow-y-auto max-h-[420px] p-1 content-start transition-transform duration-100"
            style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}
          >
            {filteredNodes.map((node) => {
              const isSelected = node.id === selectedNodeId;
              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  className={cn(
                    "flex flex-col p-2.5 rounded-lg border text-left cursor-pointer transition-all duration-150 select-none",
                    isSelected
                      ? "bg-sky-500/10 border-sky-400/50 shadow-xs shadow-sky-500/10"
                      : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.05] hover:border-white/[0.12]"
                  )}
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="text-xs font-semibold text-slate-200 truncate font-mono">
                      {node.label}
                    </span>
                    <Badge variant={node.kind === "function" ? "accent" : "default"} size="sm">
                      {node.kind}
                    </Badge>
                  </div>
                  <span className="text-[11px] text-slate-400 truncate font-mono">
                    {node.file}
                  </span>
                  {node.line !== undefined && (
                    <span className="text-[10px] text-slate-500 mt-1">line {node.line}</span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="text-[11px] text-slate-400 pt-2 border-t border-white/[0.04] flex items-center justify-between">
            <span>Showing top {filteredNodes.length} symbols</span>
            <span>Click any node to inspect call relationships</span>
          </div>
        </div>

        {/* Right Inspector: Details of Selected Symbol */}
        <div className="bg-[#0c0e14] border border-white/[0.06] rounded-xl p-4 flex flex-col justify-between">
          {selectedNode ? (
            <div className="flex flex-col gap-4 overflow-y-auto max-h-[420px]">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h5 className="text-sm font-semibold text-slate-100 font-mono">
                    {selectedNode.label}
                  </h5>
                  <Badge variant="accent">{selectedNode.kind}</Badge>
                </div>
                <p className="text-xs text-slate-400 font-mono break-all">{selectedNode.file}</p>
                {selectedNode.line && (
                  <p className="text-[11px] text-slate-500 mt-0.5">Line: {selectedNode.line}</p>
                )}
              </div>

              {/* Callers */}
              <div className="flex flex-col gap-1.5">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Callers ({callers.length})
                </span>
                {callers.length === 0 ? (
                  <span className="text-xs text-slate-500 italic">No incoming calls in bounded graph</span>
                ) : (
                  <div className="flex flex-col gap-1">
                    {callers.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => setSelectedNodeId(c.id)}
                        className="text-left text-xs p-1.5 rounded-md bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.06] text-slate-300 font-mono truncate"
                      >
                        {c.label} <span className="text-[10px] text-slate-400">({c.file})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Callees */}
              <div className="flex flex-col gap-1.5">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Callees ({callees.length})
                </span>
                {callees.length === 0 ? (
                  <span className="text-xs text-slate-500 italic">No outgoing calls in bounded graph</span>
                ) : (
                  <div className="flex flex-col gap-1">
                    {callees.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => setSelectedNodeId(c.id)}
                        className="text-left text-xs p-1.5 rounded-md bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.06] text-slate-300 font-mono truncate"
                      >
                        {c.label} <span className="text-[10px] text-slate-400">({c.file})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-400">
              <Network className="w-8 h-8 mb-2 opacity-30" />
              <p className="text-xs">Select any node on the left to inspect call relationships</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
