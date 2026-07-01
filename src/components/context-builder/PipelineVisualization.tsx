import { Check, Loader2, Circle } from "lucide-react";
import { useContextStore } from "@/stores/context-store";
import { cn } from "@/lib/utils";

export function PipelineVisualization() {
  const { pipelineSteps, result } = useContextStore();

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
            {result ? `${(result.total_time_ms / 1000).toFixed(1)}s` : "02.4s"}
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
              : "~4,250"}
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

          {pipelineSteps.map((step) => (
            <div key={step.id} className="relative z-10 flex items-start gap-4">
              {/* Step Indicator */}
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center -ml-[30px] mt-1 flex-shrink-0",
                  step.status === "completed" &&
                    "bg-secondary/20 border border-secondary",
                  step.status === "active" &&
                    "bg-primary/20 border-2 border-primary glow-pulse",
                  step.status === "pending" &&
                    "bg-surface-variant border border-outline-variant"
                )}
              >
                {step.status === "completed" && (
                  <Check className="w-4 h-4 text-secondary" />
                )}
                {step.status === "active" && (
                  <Loader2 className="w-4 h-4 text-primary animate-spin" />
                )}
                {step.status === "pending" && (
                  <Circle className="w-4 h-4 text-on-surface-variant" />
                )}
              </div>

              {/* Step Content */}
              <div
                className={cn(
                  step.status === "active" &&
                    "bg-surface-container-highest p-3 rounded-lg border border-primary/30 w-full shadow-[0_0_15px_rgba(173,198,255,0.05)]",
                  step.status === "pending" && "opacity-40"
                )}
              >
                <h4
                  className={cn(
                    "text-[12px] leading-[16px] tracking-[0.02em] font-semibold",
                    step.status === "active"
                      ? "text-primary font-bold"
                      : "text-on-surface"
                  )}
                >
                  {step.label}
                </h4>
                <p className="text-[14px] leading-[20px] text-on-surface-variant text-sm mt-1">
                  {step.description}
                </p>
                {step.status === "active" && step.progress !== undefined && (
                  <div className="mt-3 w-full bg-surface-container-lowest rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-primary h-1.5 rounded-full transition-all duration-500"
                      style={{ width: `${step.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
