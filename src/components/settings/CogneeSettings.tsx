import { useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useHealthStore } from "@/stores/health-store";

export function CogneeSettings() {
  const [kgEnabled, setKgEnabled] = useState(true);
  const [autoLink, setAutoLink] = useState(false);
  const status = useHealthStore((s) => s.status);

  const inputCls =
    "w-full bg-[#050505] h-8 px-3 rounded-md border border-[#222222] focus:border-white focus:outline-none text-neutral-200 font-mono text-xs transition-colors";
  const rowCls =
    "flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-[#181818] pb-4";
  const labelCls = "text-xs font-medium text-neutral-200 block";
  const subCls = "text-xs text-neutral-500 mt-0.5 block";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white tracking-tight mb-0.5">
          Cognee Integration
        </h2>
        <p className="text-xs text-neutral-500">
          Configure vector database and knowledge graph processing pipelines.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-4">
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
          <div className="md:w-2/3 space-y-2.5">
            <label className="flex items-center gap-2.5 cursor-pointer group">
              <div
                onClick={() => setKgEnabled(!kgEnabled)}
                className={cn(
                  "relative flex items-center justify-center w-4 h-4 rounded border cursor-pointer transition-colors",
                  kgEnabled
                    ? "border-white bg-white text-black font-bold"
                    : "border-[#333333] bg-[#0e0e0e]"
                )}
              >
                {kgEnabled && <Check className="w-3 h-3 stroke-[3]" />}
              </div>
              <span className="text-xs text-neutral-300 group-hover:text-white transition-colors">
                Enable Knowledge Graph extraction
              </span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer group">
              <div
                onClick={() => setAutoLink(!autoLink)}
                className={cn(
                  "relative flex items-center justify-center w-4 h-4 rounded border cursor-pointer transition-colors",
                  autoLink
                    ? "border-white bg-white text-black font-bold"
                    : "border-[#333333] bg-[#0e0e0e]"
                )}
              >
                {autoLink && <Check className="w-3 h-3 stroke-[3]" />}
              </div>
              <span className="text-xs text-neutral-300 group-hover:text-white transition-colors">
                Auto-link detected symbols &amp; entities
              </span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
