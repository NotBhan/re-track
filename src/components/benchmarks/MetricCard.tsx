import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { BenchmarkMetric } from "@/lib/api";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  metric: BenchmarkMetric;
}

export function MetricCard({ metric }: MetricCardProps) {
  const TrendIcon =
    metric.trendDirection === "up"
      ? TrendingUp
      : metric.trendDirection === "down"
      ? TrendingDown
      : Minus;

  const trendColor =
    metric.trendDirection === "up"
      ? "text-emerald-400"
      : metric.trendDirection === "down"
      ? "text-red-400"
      : "text-neutral-500";

  return (
    <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-3.5 transition-colors hover:border-[#2a2a2a]">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-xs font-medium text-neutral-400">
          {metric.label}
        </h3>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-semibold font-mono text-white leading-none">
          {metric.value}
          {metric.unit && (
            <span className="text-xs font-normal text-neutral-500 ml-0.5">
              {metric.unit}
            </span>
          )}
        </span>
        {metric.trend && metric.trendDirection !== "stable" && (
          <span
            className={cn(
              "text-[11px] font-mono flex items-center gap-0.5",
              trendColor
            )}
          >
            <TrendIcon className="w-3 h-3" />
            {metric.trend}
          </span>
        )}
        {metric.trendDirection === "stable" && (
          <span className="text-[11px] font-mono text-neutral-500">
            stable
          </span>
        )}
      </div>
    </div>
  );
}
