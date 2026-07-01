import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { BenchmarkMetric } from "@/types";
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
      ? "text-secondary"
      : metric.trendDirection === "down"
      ? "text-secondary"
      : "text-on-surface-variant";

  return (
    <div className="bg-surface-container-low border border-outline-variant/50 rounded-xl p-5 relative overflow-hidden group hover:border-outline-variant transition-colors hover:scale-[1.01] duration-200">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant uppercase">
          {metric.label}
        </h3>
      </div>
      <div className="flex items-end gap-3">
        <span className="text-[32px] leading-[40px] tracking-[-0.02em] font-semibold text-on-surface leading-none">
          {metric.value}
          {metric.unit && (
            <span className="text-[20px] leading-[28px] text-on-surface-variant">
              {metric.unit}
            </span>
          )}
        </span>
        {metric.trend && metric.trendDirection !== "stable" && (
          <span
            className={cn(
              "text-[11px] leading-[12px] font-bold flex items-center gap-0.5 mb-1",
              trendColor
            )}
          >
            <TrendIcon className="w-3 h-3" />
            {metric.trend}
          </span>
        )}
        {metric.trendDirection === "stable" && (
          <span className="text-[11px] leading-[12px] font-bold text-on-surface-variant">
            stable
          </span>
        )}
      </div>

      {/* Gauge bar for quality score */}
      {metric.label === "Avg Quality Score" && (
        <div className="mt-6 relative h-2 bg-surface-variant rounded-full overflow-hidden">
          <div
            className="absolute top-0 left-0 h-full bg-primary rounded-full"
            style={{ width: `${metric.value}%` }}
          />
          <div className="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] animate-shimmer" />
        </div>
      )}

      {/* Sparkline for latency */}
      {metric.label === "Gen Latency (p95)" && (
        <div className="mt-4 h-8 flex items-end gap-1 opacity-70">
          {[40, 50, 30, 60, 45, 35, 25].map((h, i) => (
            <div
              key={i}
              className={cn(
                "w-full rounded-t-sm",
                i === 6 ? "bg-primary/60" : "bg-primary/20"
              )}
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      )}

      {/* Segmented progress for hallucination rate */}
      {metric.label === "Hallucination Rate" && (
        <div className="mt-6 h-1 flex gap-0.5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex-1 bg-secondary rounded-l-full" />
          ))}
          <div className="flex-1 bg-surface-variant rounded-r-full" />
        </div>
      )}

      {/* Min/Max for coverage */}
      {metric.label === "Context Coverage" && (
        <div className="mt-6 flex justify-between font-mono text-[13px] leading-[20px] text-outline">
          <span>Min: 72%</span>
          <span>Max: 99%</span>
        </div>
      )}
    </div>
  );
}
