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
    <div className="w-full flex flex-col gap-4">
      <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 shadow-2xl space-y-4">
        <h3 className="text-xs font-mono font-semibold text-neutral-400 uppercase tracking-wider flex items-center gap-2">
          <Database className="w-4 h-4 text-white" />
          <span>Memory Topology</span>
        </h3>

        <div className="space-y-4">
          <div className="p-3.5 bg-black rounded-lg border border-[#222222]">
            <div className="font-mono text-neutral-500 text-[11px] uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <FileCode className="w-3.5 h-3.5 text-white" />
              <span>Total Stored Memory</span>
            </div>
            <div className="text-2xl font-bold text-white font-mono">
              {stats?.total_size_display || "0 files"}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-3 bg-black rounded-lg border border-[#222222]">
              <div className="font-mono text-neutral-500 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1">
                <Network className="w-3 h-3 text-neutral-400" />
                <span>Graph Nodes</span>
              </div>
              <div className="text-lg font-bold text-white font-mono">
                {formatNumber(stats?.graph_nodes || 0)}
              </div>
            </div>

            <div className="p-3 bg-black rounded-lg border border-[#222222]">
              <div className="font-mono text-neutral-500 text-[10px] uppercase tracking-wider mb-1 flex items-center gap-1">
                <Network className="w-3 h-3 text-neutral-400" />
                <span>Graph Edges</span>
              </div>
              <div className="text-lg font-bold text-white font-mono">
                {formatNumber(stats?.graph_edges || 0)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
