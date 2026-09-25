import React from "react";
import type { MemoryVectorsResponse } from "../../types/api";
import { Database, Binary, Layers } from "lucide-react";
import { formatNumber } from "../../lib/utils";
import { Badge } from "../../components/Badge";

interface VectorSpaceViewProps {
  vectors: MemoryVectorsResponse | null;
  loading?: boolean;
}

export const VectorSpaceView: React.FC<VectorSpaceViewProps> = ({ vectors, loading }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-xs text-[#a1a1a1]">
        Inspecting vector index...
      </div>
    );
  }

  if (!vectors) {
    return (
      <div className="p-8 text-center border border-[#262626] rounded-lg text-[#a1a1a1] text-xs">
        No vector index metadata available.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Top summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-[#a1a1a1] font-medium">Provider</div>
            <div className="text-sm font-semibold text-[#ededed] uppercase tracking-wide">
              {vectors.vector_db_provider || "LanceDB"}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
            <Binary className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-[#a1a1a1] font-medium">Embedding Model</div>
            <div className="text-xs font-semibold text-[#ededed] font-mono truncate max-w-[160px]">
              {vectors.embedding_model || "nomic-embed-text"}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-[#a1a1a1] font-medium">Dimensions</div>
            <div className="text-sm font-semibold text-[#ededed] font-mono">
              {vectors.embedding_dimensions || 768} dims
            </div>
          </div>
        </div>
      </div>

      {/* Datasets & Tables table */}
      <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626]">
        <h4 className="text-xs font-semibold text-[#ededed] mb-3">Indexed Vector Partitions</h4>
        {vectors.datasets && vectors.datasets.length > 0 ? (
          <div className="flex flex-col gap-2">
            {vectors.datasets.map((ds) => (
              <div
                key={ds.id}
                className="flex items-center justify-between p-3 rounded-lg bg-[#0a0a0a] border border-[#262626] text-xs"
              >
                <div className="flex items-center gap-2.5">
                  <Database className="w-3.5 h-3.5 text-[#a1a1a1]" />
                  <span className="font-semibold text-[#ededed]">{ds.name}</span>
                </div>
                <div className="flex items-center gap-4 text-[#a1a1a1] font-mono text-[11px]">
                  <span>{formatNumber(ds.chunk_count || 0)} chunks</span>
                  <Badge variant="accent" size="sm">
                    {ds.vector_status || "ready"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-xs text-[#707070] italic">No vector partitions generated yet.</div>
        )}
      </div>
    </div>
  );
};
