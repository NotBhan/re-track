import { Check, Loader2 } from "lucide-react";
import { useContextStore } from "@/stores/context-store";

export function PipelineVisualization() {
  const { loading, result } = useContextStore();

  return (
    <div className="w-1/3 flex flex-col gap-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface-container border border-outline-variant rounded-xl p-4 flex flex-col justify-center items-center relative overflow-hidden">
          <div className="absolute inset-0 bg-primary/5 opacity-50" />
          <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-1 z-10">
            Elapsed Time
          </span>
          <span className="font-mono text-[13px] leading-[20px] text-primary text-xl font-bold z-10">
            {result ? `${(result.total_time_ms / 1000).toFixed(1)}s` : "--"}
          </span>
        </div>
        <div className="bg-surface-container border border-outline-variant rounded-xl p-4 flex flex-col justify-center items-center relative overflow-hidden">
          <div className="absolute inset-0 bg-secondary/5 opacity-50" />
          <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-1 z-10">
            Est. Tokens
          </span>
          <span className="font-mono text-[13px] leading-[20px] text-secondary text-xl font-bold z-10">
            {result
              ? `~${result.token_estimate.toLocaleString()}`
              : "--"}
          </span>
        </div>
      </div>

      {/* Pipeline Visualization */}
      <div className="flex-1 bg-surface-container rounded-xl border border-outline-variant p-5 flex flex-col relative overflow-y-auto shadow-lg shadow-black/20">
        <h3 className="text-[20px] leading-[28px] font-medium text-on-surface mb-6 flex items-center gap-2">
          <span className="w-5 h-5 text-secondary">⚡</span>
          Processing Pipeline
        </h3>

        <div className="relative flex-1 pl-8 space-y-8">
          {/* Animated Pipeline Line */}
          <div className="pipeline-line" />

          {loading ? (
            <div className="relative z-10 flex items-start gap-4">
              <div className="w-8 h-8 rounded-full flex items-center justify-center -ml-[30px] mt-1 flex-shrink-0 bg-primary/20 border-2 border-primary glow-pulse">
                <Loader2 className="w-4 h-4 text-primary animate-spin" />
              </div>
              <div className="bg-surface-container-highest p-3 rounded-lg border border-primary/30 w-full shadow-[0_0_15px_rgba(173,198,255,0.05)]">
                <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-semibold text-primary font-bold">
                  Generating Context Package...
                </h4>
                <p className="text-[14px] leading-[20px] text-on-surface-variant text-sm mt-1">
                  Retrieving and compressing memories
                </p>
                <div className="mt-3 w-full bg-surface-container-lowest rounded-full h-1.5 overflow-hidden">
                  <div className="bg-primary h-1.5 rounded-full animate-pulse" style={{ width: "60%" }} />
                </div>
              </div>
            </div>
          ) : result ? (
            <div className="relative z-10 flex items-start gap-4">
              <div className="w-8 h-8 rounded-full flex items-center justify-center -ml-[30px] mt-1 flex-shrink-0 bg-secondary/20 border border-secondary">
                <Check className="w-4 h-4 text-secondary" />
              </div>
              <div className="p-3 rounded-lg w-full">
                <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-semibold text-secondary font-bold">
                  Complete
                </h4>
                <p className="text-[14px] leading-[20px] text-on-surface-variant text-sm mt-1">
                  {result.section_count} sections · {result.retrieved_memories} memories · {result.deduplicated_memories} deduplicated
                </p>
              </div>
            </div>
          ) : (
            <div className="relative z-10 opacity-40 text-center py-8">
              <p className="text-[14px] leading-[20px] text-on-surface-variant">
                Configure inputs and click Generate to start
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
