import { Check, Loader2, Sparkles } from "lucide-react";
import { useContextStore } from "@/stores/context-store";

export function ContextPipelineVisualization() {
  const { loading, result } = useContextStore();

  return (
    <div className="w-1/3 flex flex-col gap-4">
      {/* Stats Overview */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-4 flex flex-col justify-center items-center shadow-lg">
          <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 mb-1">
            Elapsed Time
          </span>
          <span className="font-mono text-xl font-bold text-white">
            {result ? `${(result.total_time_ms / 1000).toFixed(2)}s` : "--"}
          </span>
        </div>
        <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-4 flex flex-col justify-center items-center shadow-lg">
          <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 mb-1">
            Est. Tokens
          </span>
          <span className="font-mono text-xl font-bold text-white">
            {result
              ? `~${result.token_estimate.toLocaleString()}`
              : "--"}
          </span>
        </div>
      </div>

      {/* Pipeline Visualization */}
      <div className="flex-1 bg-[#0a0a0a] rounded-xl border border-[#262626] p-5 flex flex-col relative overflow-y-auto shadow-2xl">
        <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider mb-6 flex items-center gap-2 font-mono">
          <Sparkles className="w-4 h-4 text-white" />
          Processing Pipeline
        </h3>

        <div className="relative flex-1 pl-6 space-y-6">
          {loading ? (
            <div className="relative z-10 flex items-start gap-3">
              <div className="w-7 h-7 rounded-full flex items-center justify-center -ml-[26px] mt-0.5 flex-shrink-0 bg-white text-black">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              </div>
              <div className="bg-black p-3.5 rounded-lg border border-[#262626] w-full">
                <h4 className="text-xs font-mono font-bold text-white">
                  Generating Context Package...
                </h4>
                <p className="text-xs font-mono text-neutral-400 mt-1">
                  Retrieving vector memories and traversing AST symbols
                </p>
                <div className="mt-3 w-full bg-[#141414] rounded-full h-1 overflow-hidden">
                  <div className="bg-white h-1 rounded-full animate-pulse" style={{ width: "65%" }} />
                </div>
              </div>
            </div>
          ) : result ? (
            <div className="relative z-10 flex items-start gap-3">
              <div className="w-7 h-7 rounded-full flex items-center justify-center -ml-[26px] mt-0.5 flex-shrink-0 bg-emerald-500 text-black">
                <Check className="w-3.5 h-3.5 stroke-[3]" />
              </div>
              <div className="p-3.5 rounded-lg w-full bg-black border border-[#262626]">
                <h4 className="text-xs font-mono font-bold text-white">
                  {result.model_invoked ? "Model Synthesis Complete" : "Deterministic Retrieval Complete"}
                </h4>
                <p className="text-xs font-mono text-neutral-400 mt-1">
                  {result.section_count} sections · {result.retrieved_memories} memories retrieved · {result.model_invoked ? `${result.model_name || "Model"} (${result.provider_identity || "LLM"})` : "model-free AST"}
                </p>
              </div>
            </div>
          ) : (
            <div className="relative z-10 text-center py-12 text-neutral-600">
              <p className="text-xs font-mono">
                Configure parameters and click Generate
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
