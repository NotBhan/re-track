import { ChevronDown, ChevronUp, Play, X, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";
import { useContextStore } from "@/stores/context-store";
import { useRepositoryStore } from "@/stores/repository-store";
import { Badge } from "@/components/ui/badge";

interface ContextPipelineInputsProps {
  repoPreselected?: boolean;
}

export function ContextPipelineInputs({ repoPreselected = false }: ContextPipelineInputsProps) {
  const {
    objective,
    setObjective,
    selectedRepo,
    setSelectedRepo,
    selectedRepoId,
    clearSelectedRepoId,
    topK,
    setTopK,
    advancedOptions,
    toggleAdvanced,
    loading,
    generatePackage,
  } = useContextStore();

  const repositories = useRepositoryStore((s) => s.repositories);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const preselectedRepo = selectedRepoId
    ? repositories.find((r) => r.id === selectedRepoId)
    : null;

  const handleClearSelection = () => {
    clearSelectedRepoId();
    setSelectedRepo(repositories[0]?.name || "");
  };

  return (
    <div className="w-1/3 flex flex-col bg-[#0a0a0a] rounded-xl border border-[#262626] overflow-y-auto shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-[#222222] bg-[#0c0c0c] sticky top-0 z-10">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 font-mono">
          <SlidersHorizontal className="w-4 h-4 text-white" />
          Input Parameters
        </h3>
      </div>

      <div className="p-5 flex flex-col gap-5 flex-1">
        {/* Objective */}
        <div className="space-y-2">
          <label className="text-xs font-mono font-medium text-neutral-400">
            Target Objective / Task Prompt
          </label>
          <textarea
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="e.g. How does the authentication middleware handle token refresh?"
            rows={4}
            className="w-full bg-black border border-[#262626] rounded-lg p-3 text-xs font-mono text-white placeholder:text-neutral-600 focus:outline-none focus:border-white transition-all resize-none"
          />
        </div>

        {/* Repository Selector */}
        <div className="space-y-2">
          <label className="text-xs font-mono font-medium text-neutral-400">
            Source Workspace
          </label>
          {repoPreselected && preselectedRepo ? (
            <div className="flex items-center justify-between bg-black border border-[#262626] rounded-lg p-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-bold font-mono text-white">
                  {preselectedRepo.name}
                </span>
                <Badge variant="outline" className="text-[10px] font-mono border-[#333333] bg-black text-neutral-300">
                  {preselectedRepo.status}
                </Badge>
              </div>
              <button
                onClick={handleClearSelection}
                className="p-1 text-neutral-500 hover:text-red-400 rounded transition-colors"
                title="Change Repository"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="relative">
              <select
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
                className="w-full bg-black border border-[#262626] rounded-lg p-3 text-xs font-mono text-white appearance-none focus:outline-none focus:border-white transition-all"
              >
                {repositories.map((repo) => (
                  <option key={repo.id} value={repo.name}>
                    {repo.name} ({repo.status})
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-3.5 w-4 h-4 text-neutral-500 pointer-events-none" />
            </div>
          )}
        </div>

        {/* Top-K Slider */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="text-xs font-mono font-medium text-neutral-400">
              Retrieval Depth (Top-K)
            </label>
            <span className="font-mono text-xs text-white bg-black border border-[#262626] px-2 py-0.5 rounded">
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
        <div className="border border-[#262626] rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full p-3 flex justify-between items-center bg-[#0e0e0e] hover:bg-[#141414] transition-colors text-left font-mono text-xs font-medium text-neutral-300"
          >
            <span>Advanced Processing Flags</span>
            {showAdvanced ? (
              <ChevronUp className="w-4 h-4 text-neutral-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-neutral-500" />
            )}
          </button>
          {showAdvanced && (
            <div className="p-3 bg-black space-y-3 border-t border-[#262626]">
              <label className="flex items-center gap-3 cursor-pointer group">
                <Checkbox
                  checked={advancedOptions.dedup}
                  onCheckedChange={() => toggleAdvanced("dedup")}
                />
                <span className="text-xs font-mono text-neutral-400 group-hover:text-white transition-colors">
                  Semantic Deduplication
                </span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <Checkbox
                  checked={advancedOptions.resolveRefs}
                  onCheckedChange={() => toggleAdvanced("resolveRefs")}
                />
                <span className="text-xs font-mono text-neutral-400 group-hover:text-white transition-colors">
                  Resolve Cross-References
                </span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer group">
                <Checkbox
                  checked={advancedOptions.aggressiveCompress}
                  onCheckedChange={() => toggleAdvanced("aggressiveCompress")}
                />
                <span className="text-xs font-mono text-neutral-400 group-hover:text-white transition-colors">
                  Aggressive Compression
                </span>
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Generate Button */}
      <div className="p-4 border-t border-[#222222] bg-[#0c0c0c] mt-auto">
        <button
          onClick={() => generatePackage()}
          disabled={loading || !objective.trim()}
          className="w-full bg-white hover:bg-neutral-200 text-black text-xs font-mono font-bold py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
        >
          {loading ? (
            <div className="animate-spin w-4 h-4 border-2 border-black border-t-transparent rounded-full" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-current" />
          )}
          <span>{loading ? "Synthesizing Context..." : "Generate Context Package"}</span>
        </button>
      </div>
    </div>
  );
}
