import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useSystemStore } from "../../stores/systemStore";

interface ModelProcessingPanelProps {
  startedAt: number;
}

function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

/**
 * Reports what the runtime can actually prove while a synthesis request is in
 * flight: elapsed wall-clock time plus the concurrency-guard state exposed by
 * /health. The provider contract exposes no token-level progress, so no
 * percentage is fabricated here.
 */
export const ModelProcessingPanel: React.FC<ModelProcessingPanelProps> = ({ startedAt }) => {
  const { health, backendOnline, pollHealth } = useSystemStore();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const tick = setInterval(() => setNow(Date.now()), 500);
    const poll = setInterval(() => {
      void pollHealth();
    }, 3000);
    void pollHealth();
    return () => {
      clearInterval(tick);
      clearInterval(poll);
    };
  }, [pollHealth]);

  const availableSlots = health?.concurrency_available_slots;
  const queueDepth = health?.concurrency_queue_depth;

  let runtimeState = "Waiting for the backend to begin retrieval";
  if (!backendOnline) {
    runtimeState = "Backend unreachable — runtime state unavailable";
  } else if (queueDepth !== undefined && queueDepth > 0) {
    runtimeState = "Queued — waiting for an execution slot on the model runtime";
  } else if (availableSlots !== undefined && availableSlots === 0) {
    runtimeState = "Model runtime is executing this request";
  }

  return (
    <div
      data-testid="model-processing-panel"
      className="flex flex-col gap-3 p-4 rounded-lg bg-[#0a0a0a] border border-[#262626]"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <Loader2 className="w-4 h-4 text-[#ededed] animate-spin shrink-0" />
          <span className="text-xs font-medium text-[#ededed]">Generating context</span>
        </div>
        <span className="text-[11px] font-mono text-[#707070] shrink-0">
          Elapsed {formatElapsed(Math.max(0, now - startedAt))}
        </span>
      </div>

      <div
        className="w-full h-1 bg-[#1a1a1a] rounded-full overflow-hidden"
        role="progressbar"
        aria-label="Context generation in progress"
      >
        <div className="h-full w-1/3 bg-[#ededed]/70 rounded-full animate-[retrack-indeterminate_1.4s_ease-in-out_infinite]" />
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-[11px] text-[#a1a1a1]">{runtimeState}</span>
        <span className="text-[10px] text-[#707070] leading-relaxed">
          The configured provider exposes no token-level progress, so this view reports elapsed time
          and runtime state instead of a synthetic percentage.
        </span>
      </div>
    </div>
  );
};
