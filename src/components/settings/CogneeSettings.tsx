import { useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useHealthStore } from "@/stores/health-store";

export function CogneeSettings() {
  const [kgEnabled, setKgEnabled] = useState(true);
  const [autoLink, setAutoLink] = useState(false);
  const status = useHealthStore((s) => s.status);

  const inputCls =
    "w-full bg-[#0e0e0e] h-10 px-3 rounded-lg border border-[#262626] focus:border-white focus:outline-none text-white font-mono text-xs transition-colors";
  const rowCls =
    "flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-[#1c1c1c] pb-5";
  const labelCls = "text-xs font-mono font-medium text-white block";
  const subCls = "text-[11px] text-neutral-400 mt-0.5 block";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight mb-1">
          Cognee Integration
        </h2>
        <p className="text-xs text-neutral-400">
          Configure vector database and knowledge graph processing pipelines.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 space-y-5 shadow-2xl">
        {/* Vector DB */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Vector Database</label>
            <span className={subCls}>Embedded vector storage provider.</span>
          </div>
          <div className="md:w-2/3">
            <select
              defaultValue={status?.vector_db ?? "lancedb"}
              className={inputCls}
            >
              <option value="lancedb">LanceDB (Embedded Local)</option>
              <option value="qdrant">Qdrant (Local)</option>
              <option value="milvus">Milvus</option>
            </select>
          </div>
        </div>

        {/* Graph DB */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Graph Database</label>
            <span className={subCls}>Embedded property graph store.</span>
          </div>
          <div className="md:w-2/3">
            <select
              defaultValue={status?.graph_db ?? "kuzu"}
              className={inputCls}
            >
              <option value="kuzu">Kùzu (Embedded Local)</option>
              <option value="ladybug">Ladybug</option>
              <option value="networkx">NetworkX (In-Memory)</option>
            </select>
          </div>
        </div>

        {/* Graph Features */}
        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
          <div className="md:w-1/3">
            <label className={labelCls}>Graph Features</label>
            <span className={subCls}>Knowledge topology flags.</span>
          </div>
          <div className="md:w-2/3 space-y-3.5">
            <label className="flex items-center gap-3 cursor-pointer group">
              <div
                onClick={() => setKgEnabled(!kgEnabled)}
                className={cn(
                  "relative flex items-center justify-center w-5 h-5 rounded-md border cursor-pointer transition-colors",
                  kgEnabled
                    ? "border-white bg-white text-black font-bold"
                    : "border-[#333333] bg-[#0e0e0e]"
                )}
              >
                {kgEnabled && <Check className="w-3.5 h-3.5 stroke-[3]" />}
              </div>
              <span className="text-xs text-neutral-300 group-hover:text-white transition-colors font-mono">
                Enable Knowledge Graph extraction
              </span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer group">
              <div
                onClick={() => setAutoLink(!autoLink)}
                className={cn(
                  "relative flex items-center justify-center w-5 h-5 rounded-md border cursor-pointer transition-colors",
                  autoLink
                    ? "border-white bg-white text-black font-bold"
                    : "border-[#333333] bg-[#0e0e0e]"
                )}
              >
                {autoLink && <Check className="w-3.5 h-3.5 stroke-[3]" />}
              </div>
              <span className="text-xs text-neutral-300 group-hover:text-white transition-colors font-mono">
                Auto-link detected symbols & entities
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
