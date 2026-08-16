import { useState } from "react";
import { Calendar, RefreshCw, BarChart3 } from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { MetricCard } from "@/components/benchmarks/MetricCard";
import { LatencyChart } from "@/components/benchmarks/LatencyChart";
import { ThroughputChart } from "@/components/benchmarks/ThroughputChart";
import { runBenchmark } from "@/lib/api";
import type { BenchmarkSuiteResponse } from "@/lib/api";
import type { BenchmarkMetric } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

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
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-background">
      <TopBar title="RE:Track | Benchmarks" />

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Page Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/80 pb-5">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  Retrieval & Context Benchmarks
                </h1>
                {suite && (
                  <Badge variant="secondary" className="text-xs font-mono">
                    Pass: {Math.round(suite.pass_rate)}%
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Real-time latency, token efficiency, and question-answering precision suite.
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <Button
                variant="outline"
                size="sm"
                className="gap-2 h-9 text-xs"
              >
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <span>Last 7 Days</span>
              </Button>
              <Button
                onClick={handleRunSuite}
                disabled={loading}
                size="sm"
                className="gap-2 h-9 text-xs font-semibold shadow-xs"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
                <span>{loading ? "Running Suite..." : "Execute Benchmark"}</span>
              </Button>
            </div>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="bg-destructive/10 text-destructive border border-destructive/30 rounded-lg p-3.5 text-xs font-mono">
              {error}
            </div>
          )}

          {/* Empty State */}
          {!suite && !loading && !error && (
            <div className="flex flex-col items-center justify-center py-20 text-center bg-card/40 rounded-xl border border-border/70 p-8">
              <div className="w-12 h-12 rounded-xl bg-secondary/80 flex items-center justify-center mb-3">
                <BarChart3 className="w-6 h-6 text-muted-foreground" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">
                No benchmarks executed yet
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm mt-1 mb-4">
                Run the test harness to evaluate latency, memory search quality, and token accuracy against local models.
              </p>
              <Button
                onClick={handleRunSuite}
                size="sm"
                className="gap-2 text-xs"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Run Benchmark Suite</span>
              </Button>
            </div>
          )}

          {/* Metrics Bento & Charts */}
          {suite && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
                {metrics.map((m, i) => (
                  <MetricCard key={i} metric={m} />
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <LatencyChart />
                <ThroughputChart />
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
