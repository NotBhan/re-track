import { useState } from "react";
import { Calendar, RefreshCw } from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { MetricCard } from "@/components/benchmarks/MetricCard";
import { LatencyChart } from "@/components/benchmarks/LatencyChart";
import { ThroughputChart } from "@/components/benchmarks/ThroughputChart";
import { runBenchmark } from "@/lib/api";
import type { BenchmarkSuiteResponse } from "@/lib/api";
import type { BenchmarkMetric } from "@/types";

export default function Benchmarks() {
  const [suite, setSuite] = useState<BenchmarkSuiteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunSuite = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await runBenchmark();
      setSuite(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Benchmark failed");
    } finally {
      setLoading(false);
    }
  };

  const metrics: BenchmarkMetric[] = suite
    ? [
        {
          label: "Avg Latency",
          value: Math.round(suite.avg_latency_ms).toString(),
          unit: "ms",
          trend: suite.avg_latency_ms < 2000 ? "fast" : undefined,
          trendDirection: suite.avg_latency_ms < 2000 ? "up" : "down",
        },
        {
          label: "Avg Tokens",
          value: Math.round(suite.avg_tokens).toString(),
          trendDirection: "stable",
        },
        {
          label: "Pass Rate",
          value: Math.round(suite.pass_rate).toString(),
          unit: "%",
          trendDirection: suite.pass_rate >= 80 ? "up" : "down",
          trend: suite.pass_rate >= 80 ? "good" : "low",
        },
        {
          label: "Questions",
          value: suite.total_questions.toString(),
          trendDirection: "stable",
        },
      ]
    : [];

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
              Real-time telemetry and comparative analysis for RE:Track (RefinedEngine Track)
              engine.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-outline-variant bg-transparent text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface hover:bg-surface-container-high transition-colors">
              <Calendar className="w-4 h-4" />
              Last 7 Days
            </button>
            <button
              onClick={handleRunSuite}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary text-on-primary text-[12px] leading-[16px] tracking-[0.02em] font-medium hover:bg-primary-fixed transition-colors shadow-[0_0_10px_rgba(173,198,255,0.15)] disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Running..." : "Run Suite"}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-error-container text-on-error-container border border-error/30 rounded-xl p-4 text-[14px]">
            {error}
          </div>
        )}

        {/* Empty State */}
        {!suite && !loading && !error && (
          <div className="flex-1 flex items-center justify-center text-on-surface-variant text-[16px]">
            No benchmarks have been run yet. Click "Run Suite" to start.
          </div>
        )}

        {/* Metric Cards */}
        {metrics.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {metrics.map((metric, i) => (
              <MetricCard key={i} metric={metric} />
            ))}
          </div>
        )}

        {/* Charts */}
        {suite && suite.results.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 h-[400px]">
            <div className="lg:col-span-2">
              <LatencyChart />
            </div>
            <div>
              <ThroughputChart />
            </div>
          </div>
        )}
      </main>
    </>
  );
}
