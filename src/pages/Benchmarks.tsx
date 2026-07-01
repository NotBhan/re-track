import { Calendar, RefreshCw } from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { MetricCard } from "@/components/benchmarks/MetricCard";
import { LatencyChart } from "@/components/benchmarks/LatencyChart";
import { ThroughputChart } from "@/components/benchmarks/ThroughputChart";
import { mockBenchmarkMetrics } from "@/data/mock";

export default function Benchmarks() {
  return (
    <>
      <TopBar />
      <main className="flex-1 p-6 flex flex-col gap-6 max-w-[1440px] w-full mx-auto overflow-y-auto">
        {/* Page Header */}
        <div className="flex items-end justify-between border-b border-surface-variant pb-4">
          <div>
            <h2 className="text-[32px] leading-[40px] tracking-[-0.02em] font-semibold text-on-surface mb-1">
              Performance Benchmarks
            </h2>
            <p className="text-[16px] leading-[24px] text-on-surface-variant">
              Real-time telemetry and comparative analysis for AndesContext
              engine.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-outline-variant bg-transparent text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface hover:bg-surface-container-high transition-colors">
              <Calendar className="w-4 h-4" />
              Last 7 Days
            </button>
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary text-on-primary text-[12px] leading-[16px] tracking-[0.02em] font-medium hover:bg-primary-fixed transition-colors shadow-[0_0_10px_rgba(173,198,255,0.15)]">
              <RefreshCw className="w-4 h-4" />
              Run Suite
            </button>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {mockBenchmarkMetrics.map((metric, i) => (
            <MetricCard key={i} metric={metric} />
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-[400px]">
          <div className="lg:col-span-2">
            <LatencyChart />
          </div>
          <div>
            <ThroughputChart />
          </div>
        </div>
      </main>
    </>
  );
}
