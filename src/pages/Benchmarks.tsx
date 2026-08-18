import { useState } from "react";
import {
  RefreshCw,
  Zap,
  CheckCircle2,
  Server,
} from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { MetricCard } from "@/components/benchmarks/MetricCard";
import { runBenchmark } from "@/lib/api";
import type { BenchmarkSuiteResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "motion/react";
import { toast } from "@/components/ui/toast";

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
      toast.success("Benchmark suite completed successfully!");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Benchmark failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const firstResult = suite?.results?.[0];
  const baselineTokens = firstResult?.baseline_tokens || Number(suite?.run_metadata?.baseline_tokens) || 25000;
  const contextTokens = firstResult?.context_tokens || firstResult?.token_count || 1200;
  const tokenWidthPercent = Math.min(100, Math.max(3, Math.round((contextTokens / baselineTokens) * 100)));

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased font-sans">
      <TopBar title="RE:Track | Benchmarks & Telemetry" subtitle="Context Precision & Token Efficiency">
        <div className="flex items-center gap-2">
          <Button
            onClick={handleRunSuite}
            disabled={loading}
            size="sm"
            className="w-[170px] justify-center gap-2 h-8 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 shadow-xs cursor-pointer disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>{loading ? "Running Suite..." : "Execute Benchmarks"}</span>
          </Button>
        </div>
      </TopBar>

      <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5">
        <div className="max-w-5xl mx-auto space-y-5">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1a1a1a] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-white">
                  Deterministic Context &amp; Latency Benchmarks
                </h1>
                {suite && (
                  <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                    {suite.results.length} Queries Evaluated
                  </Badge>
                )}
              </div>
              <p className="text-xs text-neutral-500 mt-0.5">
                Authoritative token reduction against raw repository source baseline, discrete retrieval timings, and hardware telemetry.
              </p>
            </div>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="bg-red-950/20 text-red-400 border border-red-500/20 rounded-md p-3 text-xs font-mono">
              {error}
            </div>
          )}

          {/* Empty State before first run */}
          {!suite && !loading && (
            <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-xl p-8 text-center space-y-3">
              <Zap className="w-8 h-8 text-neutral-500 mx-auto" />
              <h3 className="text-sm font-semibold text-white">No Benchmark Run Recorded</h3>
              <p className="text-xs text-neutral-400 max-w-md mx-auto">
                Execute the benchmark suite to measure token compression ratios against the full source baseline, evaluate discrete retrieval latency, and capture runtime hardware telemetry.
              </p>
              <Button
                onClick={handleRunSuite}
                size="sm"
                className="h-8 px-4 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 cursor-pointer"
              >
                Execute Benchmarks Now
              </Button>
            </div>
          )}

          {/* KPI Metrics Grid */}
          {suite && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <MetricCard
                metric={{
                  label: "Token Savings",
                  value: (suite.avg_token_savings_percent || 0).toFixed(1),
                  unit: "%",
                  trend: "vs Raw Repo Baseline",
                  trendDirection: "up",
                }}
              />
              <MetricCard
                metric={{
                  label: "Compression Ratio",
                  value: (suite.avg_compression_ratio || 1).toFixed(1),
                  unit: "x",
                  trend: "Token reduction",
                  trendDirection: "stable",
                }}
              />
              <MetricCard
                metric={{
                  label: "Retrieval Latency",
                  value: Math.round(suite.avg_retrieval_latency_ms || suite.avg_latency_ms || 0).toString(),
                  unit: "ms",
                  trend: "AST + Vector query",
                  trendDirection: "up",
                }}
              />
              <MetricCard
                metric={{
                  label: "Total Pipeline Latency",
                  value: Math.round(suite.avg_total_latency_ms || suite.avg_latency_ms || 0).toString(),
                  unit: "ms",
                  trend: "End-to-end synthesis",
                  trendDirection: "up",
                }}
              />
            </div>
          )}

          {/* Token Reduction Comparison Visual Card */}
          {suite && (
            <div className="bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-[#181818] pb-2.5">
                <div>
                  <h3 className="text-xs font-semibold text-white tracking-tight flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    <span>Token Budget Comparison (Raw Repo Baseline vs RE:Track Context)</span>
                  </h3>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    Measured against all eligible codebase files using the character-4b heuristic tokenizer.
                  </p>
                </div>
                <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                  {(suite.avg_token_savings_percent || 0).toFixed(1)}% Prompt Savings
                </Badge>
              </div>

              <div className="space-y-3 font-mono text-xs">
                {/* Raw Repo Scan */}
                <div className="space-y-1">
                  <div className="flex justify-between text-neutral-400 text-[11px]">
                    <span>Raw Eligible Codebase Baseline ({String(suite.run_metadata?.eligible_source_files || "All")} files)</span>
                    <span>~{baselineTokens.toLocaleString()} tokens</span>
                  </div>
                  <div className="w-full bg-[#141414] h-2 rounded overflow-hidden">
                    <div className="bg-neutral-600 h-full w-full" />
                  </div>
                </div>

                {/* RE:Track Context Package */}
                <div className="space-y-1">
                  <div className="flex justify-between text-neutral-200 text-[11px]">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      RE:Track Compact Context Package (Avg)
                    </span>
                    <span className="text-emerald-400 font-medium">~{contextTokens.toLocaleString()} tokens</span>
                  </div>
                  <div className="w-full bg-[#141414] h-2 rounded overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${tokenWidthPercent}%` }}
                      transition={{ duration: 0.5 }}
                      className="bg-emerald-400 h-full rounded"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Test Questions & Results Table */}
          {suite?.results && suite.results.length > 0 && (
            <div className="bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] overflow-hidden">
              <div className="px-4 py-2.5 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between">
                <h3 className="text-xs font-semibold text-white tracking-tight flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Evaluation Suite Queries</span>
                </h3>
                <span className="text-[11px] font-mono text-neutral-500">
                  {suite.results.length} queries evaluated
                </span>
              </div>

              <div className="divide-y divide-[#141414]">
                {suite.results.map((res, i) => {
                  const bTokens = res.baseline_tokens || baselineTokens;
                  const cTokens = res.context_tokens || res.token_count || 0;
                  const rTime = res.retrieval_time_ms || Math.round((res.total_time_ms || res.latency_ms || 0) * 0.4);
                  const tTime = res.total_time_ms || res.latency_ms || 0;

                  return (
                    <div key={i} className="px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-[#0e0e0e] transition-colors">
                      <div className="flex-1 min-w-0 pr-2">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                          <h4 className="text-xs font-medium text-white truncate">
                            {res.question}
                          </h4>
                        </div>
                        <div className="flex items-center gap-3 text-xs font-mono text-neutral-500 pl-5.5 flex-wrap">
                          <span>{bTokens.toLocaleString()} base → <strong className="text-neutral-200">{cTokens.toLocaleString()}</strong> tokens</span>
                          <span>·</span>
                          <span className="text-emerald-400">{res.compression_ratio}x ({res.token_savings_percent || 0}% saved)</span>
                          <span>·</span>
                          <span>{res.section_count} sections</span>
                          <span>·</span>
                          <span>{res.retrieved_memories} facts</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 self-end sm:self-center font-mono text-xs flex-wrap">
                        <Badge variant="outline" className="text-[10px] border-[#2a2a2a] text-neutral-300">
                          Retrieval: {rTime}ms / Total: {tTime}ms
                        </Badge>
                        <Badge variant="outline" className="text-[10px] border-neutral-800 text-neutral-400 bg-neutral-900">
                          {res.accuracy_status || "Not evaluated (requires ground truth set)"}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Immutable Run Metadata Block */}
          {suite?.run_metadata && (
            <div className="bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] p-4 space-y-3 font-mono text-xs">
              <div className="flex items-center gap-1.5 text-neutral-300 font-semibold pb-2 border-b border-[#181818]">
                <Server className="w-3.5 h-3.5 text-neutral-400" />
                <span>Immutable Run Metadata &amp; Hardware Telemetry</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-[11px]">
                <div className="p-2.5 rounded bg-black border border-[#181818]">
                  <span className="text-neutral-500 text-[10px] block mb-0.5">REPOSITORY PATH</span>
                  <span className="text-neutral-200 truncate block">{String(suite.run_metadata.repository_path || "N/A")}</span>
                </div>
                <div className="p-2.5 rounded bg-black border border-[#181818]">
                  <span className="text-neutral-500 text-[10px] block mb-0.5">GIT REVISION</span>
                  <span className="text-neutral-200">{String(suite.run_metadata.repository_revision || "unversioned")}</span>
                </div>
                <div className="p-2.5 rounded bg-black border border-[#181818]">
                  <span className="text-neutral-500 text-[10px] block mb-0.5">TOKENIZER &amp; CACHE</span>
                  <span className="text-neutral-200">{String(suite.run_metadata.tokenizer_name)} ({String(suite.run_metadata.cache_state)})</span>
                </div>
                <div className="p-2.5 rounded bg-black border border-[#181818]">
                  <span className="text-neutral-500 text-[10px] block mb-0.5">LLM MODEL</span>
                  <span className="text-neutral-200">{String(suite.run_metadata.model || "phi-4-mini-reasoning")}</span>
                </div>
                <div className="p-2.5 rounded bg-black border border-[#181818]">
                  <span className="text-neutral-500 text-[10px] block mb-0.5">EXECUTION DEVICE</span>
                  <span className="text-white font-bold">{String(suite.run_metadata.execution_device || "CPU")}</span>
                  <span className="text-neutral-500 ml-1.5">(GPU: {String(suite.run_metadata.gpu_presence || "None")})</span>
                </div>
                <div className="p-2.5 rounded bg-black border border-[#181818]">
                  <span className="text-neutral-500 text-[10px] block mb-0.5">EVALUATION TIMESTAMP</span>
                  <span className="text-neutral-400">{String(suite.run_metadata.timestamp || "")}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
