import { Database, Network, FileCode, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useMemoryStore } from "@/stores/memory-store";

export function MemoryStats() {
  const stats = useMemoryStore((s) => s.stats);

  const kgStatus = stats?.knowledge_graph_status || (
    stats?.graph_nodes && stats.graph_nodes > 0 ? "extracted" : "not_extracted"
  );

  return (
    <div className="w-full flex flex-col gap-3">
      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-3">
        <h3 className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-neutral-400" />
          <span>Memory Storage Layers</span>
        </h3>

        <div className="space-y-2.5 font-mono">
          {/* Layer 1: Ingested Source Files */}
          <div className="p-3 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-neutral-500 text-[10px] mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <FileCode className="w-3 h-3 text-neutral-400" />
                <span>Ingested Source Files</span>
              </span>
              <span className="text-neutral-400">{stats?.dataset_count || 0} datasets</span>
            </div>
            <div className="text-base font-semibold text-white">
              {stats?.total_size_display || "0 files"}
            </div>
          </div>

          {/* Layer 2: Vector Semantic Index */}
          <div className="p-3 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-neutral-500 text-[10px] mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <Cpu className="w-3 h-3 text-neutral-400" />
                <span>Vector Semantic Index</span>
              </span>
              <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                Ready
              </Badge>
            </div>
            <div className="text-xs text-neutral-300">
              LanceDB Vector Embeddings
            </div>
          </div>

          {/* Layer 3: Knowledge Graph Entities */}
          <div className="p-3 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-neutral-500 text-[10px] mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <Network className="w-3 h-3 text-neutral-400" />
                <span>Knowledge Graph</span>
              </span>
              {kgStatus === "extracted" ? (
                <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                  Extracted
                </Badge>
              ) : kgStatus === "extracting" ? (
                <Badge variant="outline" className="text-[9px] uppercase border-amber-500/30 text-amber-400 bg-amber-500/10">
                  Extracting
                </Badge>
              ) : kgStatus === "failed" ? (
                <Badge variant="outline" className="text-[9px] uppercase border-red-500/30 text-red-400 bg-red-500/10">
                  Failed
                </Badge>
              ) : (
                <Badge variant="outline" className="text-[9px] uppercase border-neutral-800 text-neutral-400 bg-neutral-900">
                  Not Extracted
                </Badge>
              )}
            </div>

            {kgStatus === "extracted" && stats?.graph_nodes !== undefined && stats?.graph_nodes !== null ? (
              <div className="text-xs text-white font-medium">
                {stats.graph_nodes} entities · {stats.graph_edges || 0} relationships
              </div>
            ) : (
              <div className="text-[10px] text-neutral-500 leading-tight">
                V1 Raw Ingestion (Graph entity extraction optional)
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
