import { useEffect } from "react";
import { Check, CheckCircle2, AlertCircle, Loader2, Save } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/stores/settings-store";
import { Button } from "@/components/ui/button";

export function CogneeSettings() {
  const {
    vectorDb,
    graphDb,
    enableKgExtraction,
    autoLinkEntities,
    caching,
    saving,
    saveSuccess,
    statusMessage,
    setVectorDb,
    setGraphDb,
    setEnableKgExtraction,
    setAutoLinkEntities,
    setCaching,
    fetchSettings,
    saveCogneeSettings,
  } = useSettingsStore();

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const inputCls =
    "w-full bg-[#050505] h-8 px-3 rounded-md border border-[#222222] focus:border-white focus:outline-none text-neutral-200 font-mono text-xs transition-colors cursor-pointer";
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
          Configure vector database, property graph store, and knowledge graph processing pipelines.
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
              value={vectorDb}
              onChange={(e) => setVectorDb(e.target.value)}
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
              value={graphDb}
              onChange={(e) => setGraphDb(e.target.value)}
              className={inputCls}
            >
              <option value="kuzu">Kùzu (Embedded Local)</option>
              <option value="ladybug">Ladybug</option>
              <option value="networkx">NetworkX (In-Memory)</option>
            </select>
          </div>
        </div>

        {/* Session Memory / Caching */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Session Caching</label>
            <span className={subCls}>Cache Cognee session memories across requests.</span>
          </div>
          <div className="md:w-2/3">
            <label className="flex items-center gap-2.5 cursor-pointer group">
              <div
                onClick={() => setCaching(!caching)}
                className={cn(
                  "relative flex items-center justify-center w-4 h-4 rounded border cursor-pointer transition-colors",
                  caching
                    ? "border-white bg-white text-black font-bold"
                    : "border-[#333333] bg-[#0e0e0e]"
                )}
              >
                {caching && <Check className="w-3 h-3 stroke-[3]" />}
              </div>
              <span className="text-xs text-neutral-300 group-hover:text-white transition-colors">
                Enable session memory caching
              </span>
            </label>
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
                onClick={() => setEnableKgExtraction(!enableKgExtraction)}
                className={cn(
                  "relative flex items-center justify-center w-4 h-4 rounded border cursor-pointer transition-colors",
                  enableKgExtraction
                    ? "border-white bg-white text-black font-bold"
                    : "border-[#333333] bg-[#0e0e0e]"
                )}
              >
                {enableKgExtraction && <Check className="w-3 h-3 stroke-[3]" />}
              </div>
              <span className="text-xs text-neutral-300 group-hover:text-white transition-colors">
                Enable Knowledge Graph extraction
              </span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer group">
              <div
                onClick={() => setAutoLinkEntities(!autoLinkEntities)}
                className={cn(
                  "relative flex items-center justify-center w-4 h-4 rounded border cursor-pointer transition-colors",
                  autoLinkEntities
                    ? "border-white bg-white text-black font-bold"
                    : "border-[#333333] bg-[#0e0e0e]"
                )}
              >
                {autoLinkEntities && <Check className="w-3 h-3 stroke-[3]" />}
              </div>
              <span className="text-xs text-neutral-300 group-hover:text-white transition-colors">
                Auto-link detected symbols &amp; entities
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Footer: status feedback + save action */}
      <div className="flex items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2 min-h-[24px]">
          {saving && (
            <>
              <Loader2 className="w-3.5 h-3.5 text-neutral-400 animate-spin" />
              <span className="text-xs font-mono text-neutral-400">Saving &amp; configuring…</span>
            </>
          )}
          {!saving && statusMessage && (
            <>
              {saveSuccess ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
              )}
              <span
                className={cn(
                  "text-xs font-mono",
                  saveSuccess ? "text-emerald-400" : "text-red-400"
                )}
              >
                {statusMessage}
              </span>
            </>
          )}
        </div>

        <Button
          onClick={() => saveCogneeSettings()}
          disabled={saving}
          size="sm"
          className="w-[140px] justify-center gap-1.5 h-7.5 px-3 text-xs bg-white text-black font-medium hover:bg-neutral-200 rounded-md cursor-pointer shadow-xs disabled:opacity-60 transition-colors"
        >
          {saving ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Save className="w-3 h-3" />
          )}
          <span>{saving ? "Saving..." : "Save Settings"}</span>
        </Button>
      </div>
    </div>
  );
}
