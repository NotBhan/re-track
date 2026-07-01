import { Database } from "lucide-react";
import { mockMemoryTopology } from "@/data/mock";

export function MemoryStats() {
  return (
    <div className="w-full xl:w-80 flex flex-col gap-6">
      <div className="bg-surface-container border border-outline-variant rounded-lg p-5 relative overflow-hidden group">
        {/* Ambient Glow */}
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-primary/10 rounded-full blur-3xl group-hover:bg-primary/20 transition-all duration-700" />

        <h3 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant uppercase tracking-wider mb-4 flex items-center gap-2">
          <Database className="w-4 h-4" />
          Memory Topology
        </h3>
        <div className="space-y-4">
          <div>
            <div className="font-mono text-on-surface-variant/70 text-[11px] mb-1">
              Total Stored Data
            </div>
            <div className="text-[32px] leading-[40px] tracking-[-0.02em] font-semibold text-on-surface flex items-baseline gap-1">
              1.2{" "}
              <span className="text-[20px] leading-[28px] font-medium text-on-surface-variant">
                TB
              </span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 pt-3 border-t border-outline-variant/50">
            <div>
              <div className="font-mono text-on-surface-variant/70 text-[11px] mb-1">
                Graph Nodes
              </div>
              <div className="text-[20px] leading-[28px] font-semibold text-on-surface">
                {mockMemoryTopology.graphNodes}
              </div>
            </div>
            <div>
              <div className="font-mono text-on-surface-variant/70 text-[11px] mb-1">
                Graph Edges
              </div>
              <div className="text-[20px] leading-[28px] font-semibold text-secondary">
                {mockMemoryTopology.graphEdges}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
