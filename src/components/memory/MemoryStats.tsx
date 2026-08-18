import { Database, Network, FileCode } from "lucide-react";
import { useMemoryStore } from "@/stores/memory-store";

export function MemoryStats() {
  const stats = useMemoryStore((s) => s.stats);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  return (
    <div className="w-full flex flex-col gap-3">
      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-3">
        <h3 className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-neutral-400" />
          <span>Memory Topology</span>
        </h3>

        <div className="space-y-2 font-mono">
          <div className="p-3 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-neutral-500 text-[10px] mb-0.5 flex items-center gap-1">
              <FileCode className="w-3 h-3 text-neutral-400" />
              <span>Total Stored Memory</span>
            </div>
            <div className="text-lg font-semibold text-white">
              {stats?.total_size_display || "0 files"}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
              <div className="text-neutral-500 text-[10px] mb-0.5 flex items-center gap-1">
                <Network className="w-3 h-3 text-neutral-400" />
                <span>Graph Nodes</span>
              </div>
              <div className="text-sm font-semibold text-white">
                {formatNumber(stats?.graph_nodes || 0)}
              </div>
            </div>

            <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
              <div className="text-neutral-500 text-[10px] mb-0.5 flex items-center gap-1">
                <Network className="w-3 h-3 text-neutral-400" />
                <span>Graph Edges</span>
              </div>
              <div className="text-sm font-semibold text-white">
                {formatNumber(stats?.graph_edges || 0)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
