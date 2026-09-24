import React, { useState } from "react";
import type { MemoryGraphResponse } from "../../types/api";
import { GitFork, Search } from "lucide-react";
import { Badge } from "../../components/Badge";
import { Input } from "../../components/Input";
import { formatNumber } from "../../lib/utils";

interface KnowledgeGraphViewProps {
  graph: MemoryGraphResponse | null;
  loading?: boolean;
}

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({ graph, loading }) => {
  const [search, setSearch] = useState("");

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-xs text-slate-400">
        Loading knowledge graph...
      </div>
    );
  }

  if (!graph || graph.status === "not_extracted" || graph.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center border border-white/[0.04] rounded-xl bg-white/[0.01]">
        <GitFork className="w-6 h-6 text-slate-500 mb-3" />
        <h4 className="text-sm font-semibold text-slate-200">Knowledge Graph Not Extracted</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1">
          Entity relationships have not been extracted into Kùzu graph storage yet. Click "Cognify" to run the extraction pipeline.
        </p>
      </div>
    );
  }

  const filteredNodes = graph.nodes.filter(
    (n) =>
      !search.trim() ||
      n.label.toLowerCase().includes(search.toLowerCase()) ||
      n.kind.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3 p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl">
        <div className="w-64">
          <Input
            placeholder="Search graph entities..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            icon={<Search className="w-3.5 h-3.5" />}
          />
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
          <span>{formatNumber(graph.total_nodes)} entities</span>
          <span className="text-white/[0.1]">•</span>
          <span>{formatNumber(graph.total_edges)} relationships</span>
        </div>
      </div>

      {/* Nodes & Edges split */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Nodes */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <h4 className="text-xs font-semibold text-slate-300 mb-2.5">Extracted Entities</h4>
          <div className="flex flex-col gap-1.5 max-h-[400px] overflow-y-auto pr-1">
            {filteredNodes.map((n) => (
              <div
                key={n.id}
                className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs"
              >
                <span className="font-semibold text-slate-200 font-mono truncate">{n.label}</span>
                <Badge variant="default" size="sm">
                  {n.kind}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        {/* Edges */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <h4 className="text-xs font-semibold text-slate-300 mb-2.5">Relationships</h4>
          <div className="flex flex-col gap-1.5 max-h-[400px] overflow-y-auto pr-1">
            {graph.edges.map((e, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs"
              >
                <div className="flex items-center gap-2 truncate font-mono text-slate-300 text-[11px]">
                  <span className="truncate">{e.source}</span>
                  <span className="text-sky-400 font-sans text-[10px]">→</span>
                  <span className="truncate">{e.target}</span>
                </div>
                <Badge variant="accent" size="sm">
                  {e.relationship_type || e.kind || "relates_to"}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
