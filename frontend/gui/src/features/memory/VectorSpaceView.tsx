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
      <div className="flex items-center justify-center p-12 text-xs text-slate-400">
        Inspecting vector index...
      </div>
    );
  }

  if (!vectors) {
    return (
      <div className="p-8 text-center border border-white/[0.04] rounded-xl text-slate-400 text-xs">
        No vector index metadata available.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Top summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Provider</div>
            <div className="text-sm font-semibold text-slate-100 uppercase tracking-wide">
              {vectors.vector_db_provider || "LanceDB"}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Binary className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Embedding Model</div>
            <div className="text-xs font-semibold text-slate-100 font-mono truncate max-w-[160px]">
              {vectors.embedding_model || "nomic-embed-text"}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Dimensions</div>
            <div className="text-sm font-semibold text-slate-100 font-mono">
              {vectors.embedding_dimensions || 768} dims
            </div>
          </div>
        </div>
      </div>

      {/* Datasets & Tables table */}
      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <h4 className="text-xs font-semibold text-slate-200 mb-3">Indexed Vector Partitions</h4>
        {vectors.datasets && vectors.datasets.length > 0 ? (
          <div className="flex flex-col gap-2">
            {vectors.datasets.map((ds) => (
              <div
                key={ds.id}
                className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs"
              >
                <div className="flex items-center gap-2.5">
                  <Database className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-semibold text-slate-200">{ds.name}</span>
                </div>
                <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
                  <span>{formatNumber(ds.chunk_count || 0)} chunks</span>
                  <Badge variant="accent" size="sm">
                    {ds.vector_status || "ready"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-xs text-slate-500 italic">No vector partitions generated yet.</div>
        )}
      </div>
    </div>
  );
};
