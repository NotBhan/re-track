import { ChevronDown, ChevronUp, Play } from "lucide-react";
import { useState } from "react";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { useContextStore } from "@/stores/context-store";

export function InputParameters() {
  const {
    objective,
    setObjective,
    selectedRepo,
    setSelectedRepo,
    topK,
    setTopK,
    advancedOptions,
    toggleAdvanced,
    loading,
    generatePackage,
  } = useContextStore();

  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="w-1/3 flex flex-col bg-surface-container rounded-xl border border-outline-variant overflow-y-auto shadow-lg shadow-black/20">
      {/* Header */}
      <div className="p-5 border-b border-outline-variant bg-surface-container-high/50 sticky top-0 z-10">
        <h3 className="text-[20px] leading-[28px] font-medium text-on-surface flex items-center gap-2">
          <span className="w-5 h-5 text-primary">⊞</span>
          Input Parameters
        </h3>
      </div>

      <div className="p-5 flex flex-col gap-6 flex-1">
        {/* Objective */}
        <div className="space-y-2">
          <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            Target Objective / Question
          </label>
          <textarea
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="e.g., How does the authentication middleware handle token refresh in the core-api repository?"
            rows={4}
            className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg p-3 text-[14px] leading-[20px] text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none"
          />
        </div>

        {/* Repository Selector */}
        <div className="space-y-2">
          <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            Source Repository
          </label>
          <div className="relative">
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg p-3 text-[14px] leading-[20px] text-on-surface appearance-none focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            >
              <option value="andes-core-api">andes-core-api</option>
              <option value="andes-web-client">andes-web-client</option>
              <option value="infra-deployments">infra-deployments</option>
            </select>
            <ChevronDown className="absolute right-3 top-3 w-5 h-5 text-on-surface-variant pointer-events-none" />
          </div>
        </div>

        {/* Top-K Slider */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
              Retrieval Depth (Top-K)
            </label>
            <span className="font-mono text-[13px] leading-[20px] text-primary bg-primary/10 px-2 py-0.5 rounded">
              {topK}
            </span>
          </div>
          <Slider
            value={[topK]}
            onValueChange={([v]) => setTopK(v)}
            min={1}
            max={100}
            className="w-full"
          />
        </div>

        {/* Advanced Options */}
        <div className="border border-outline-variant rounded-lg overflow-hidden">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full p-3 flex justify-between items-center bg-surface-container-high hover:bg-surface-bright transition-colors text-left"
          >
            <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface">
              Advanced Options
            </span>
            {showAdvanced ? (
              <ChevronUp className="w-5 h-5 text-on-surface-variant" />
            ) : (
              <ChevronDown className="w-5 h-5 text-on-surface-variant" />
            )}
          </button>
          {showAdvanced && (
            <div className="p-3 bg-surface-container-lowest space-y-3">
              <label className="flex items-center gap-3 cursor-pointer group">
                <Checkbox
                  checked={advancedOptions.dedup}
                  onCheckedChange={() => toggleAdvanced("dedup")}
                />
                <span className="text-[14px] leading-[20px] text-on-surface-variant group-hover:text-primary transition-colors">
                  Semantic Deduplication
                </span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <Checkbox
                  checked={advancedOptions.resolveRefs}
                  onCheckedChange={() => toggleAdvanced("resolveRefs")}
                />
                <span className="text-[14px] leading-[20px] text-on-surface-variant group-hover:text-primary transition-colors">
                  Resolve Cross-References
                </span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <Checkbox
                  checked={advancedOptions.aggressiveCompress}
                  onCheckedChange={() => toggleAdvanced("aggressiveCompress")}
                />
                <span className="text-[14px] leading-[20px] text-on-surface-variant group-hover:text-primary transition-colors">
                  Aggressive Compression
                </span>
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Generate Button */}
      <div className="p-5 border-t border-outline-variant bg-surface-container-high/50 mt-auto">
        <button
          onClick={() => generatePackage()}
          disabled={loading || !objective.trim()}
          className="w-full bg-primary hover:bg-primary-container text-surface-container-lowest text-[12px] leading-[16px] tracking-[0.02em] font-semibold py-3 rounded-lg transition-all active:scale-[0.98] shadow-[0_0_15px_rgba(173,198,255,0.2)] hover:shadow-[0_0_20px_rgba(173,198,255,0.4)] flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {loading ? "Generating..." : "Generate Context Package"}
        </button>
      </div>
    </div>
  );
}
