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
    <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 relative overflow-hidden group hover:border-[#404040] transition-colors shadow-lg">
      <div className="flex justify-between items-start mb-3">
        <h3 className="text-xs font-mono font-medium text-neutral-400 uppercase tracking-wider">
          {metric.label}
        </h3>
      </div>
      <div className="flex items-end gap-2.5">
        <span className="text-2xl font-bold font-mono text-white leading-none">
          {metric.value}
          {metric.unit && (
            <span className="text-sm font-normal text-neutral-400 ml-1">
              {metric.unit}
            </span>
          )}
        </span>
        {metric.trend && metric.trendDirection !== "stable" && (
          <span
            className={cn(
              "text-xs font-mono font-bold flex items-center gap-0.5 mb-0.5",
              trendColor
            )}
          >
            <TrendIcon className="w-3.5 h-3.5" />
            {metric.trend}
          </span>
        )}
        {metric.trendDirection === "stable" && (
          <span className="text-xs font-mono text-neutral-500 mb-0.5">
            stable
          </span>
        )}
      </div>
    </div>
  );
}
