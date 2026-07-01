import { useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function CogneeSettings() {
  const [kgEnabled, setKgEnabled] = useState(true);
  const [autoLink, setAutoLink] = useState(false);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface mb-2">
          Cognee Integration
        </h2>
        <p className="text-[14px] leading-[20px] text-on-surface-variant">
          Configure vector database and knowledge graph processing pipelines.
        </p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 shadow-sm">
        <div className="space-y-6">
          {/* Vector DB */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Vector Database
              </label>
            </div>
            <div className="md:w-2/3">
              <select className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface text-[14px] leading-[20px] transition-colors appearance-none">
                <option value="qdrant">Qdrant (Local)</option>
                <option value="milvus">Milvus</option>
                <option value="weaviate">Weaviate</option>
              </select>
            </div>
          </div>

          {/* Graph Features */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Graph Features
              </label>
            </div>
            <div className="md:w-2/3 space-y-4">
              <label className="flex items-center gap-3 cursor-pointer group">
                <div
                  onClick={() => setKgEnabled(!kgEnabled)}
                  className={cn(
                    "relative flex items-center justify-center w-5 h-5 rounded border cursor-pointer transition-colors",
                    kgEnabled
                      ? "border-primary bg-primary/20"
                      : "border-outline-variant bg-surface-container"
                  )}
                >
                  {kgEnabled && <Check className="w-3.5 h-3.5 text-primary" />}
                </div>
                <span className="text-[14px] leading-[20px] text-on-surface group-hover:text-primary transition-colors">
                  Enable Knowledge Graph extraction
                </span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <div
                  onClick={() => setAutoLink(!autoLink)}
                  className={cn(
                    "relative flex items-center justify-center w-5 h-5 rounded border cursor-pointer transition-colors",
                    autoLink
                      ? "border-primary bg-primary/20"
                      : "border-outline-variant bg-surface-container"
                  )}
                >
                  {autoLink && <Check className="w-3.5 h-3.5 text-primary" />}
                </div>
                <span className="text-[14px] leading-[20px] text-on-surface group-hover:text-primary transition-colors">
                  Auto-link detected entities
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
