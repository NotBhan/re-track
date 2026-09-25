import React from "react";
import { Play, Clock, Zap, Percent } from "lucide-react";
import { useSystemStore } from "../../stores/systemStore";
import { Button } from "../../components/Button";
import { Badge } from "../../components/Badge";
import { formatNumber, formatMs } from "../../lib/utils";

export const BenchmarkRunner: React.FC = () => {
  const { benchmarkResults, runningBenchmark, benchmarkError, executeBenchmark } = useSystemStore();

  return (
    <div className="flex flex-col gap-5 max-w-3xl">
      {/* Top Action Box */}
      <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center justify-between">
        <div>
          <h4 className="text-xs font-semibold text-[#ededed]">Retrieval & Context Benchmarks</h4>
          <p className="text-xs text-[#a1a1a1] mt-0.5">
            Evaluate end-to-end token reduction, latency, and AST retrieval accuracy across test prompts.
          </p>
        </div>

        <Button size="sm" loading={runningBenchmark} onClick={() => executeBenchmark()}>
          <Play className="w-3.5 h-3.5 mr-1" />
          <span>Run Suite</span>
        </Button>
      </div>

      {benchmarkError && (
        <div className="p-3.5 rounded-lg bg-[#180808] border border-[#451a1a] text-[#f87171] text-xs">
          {benchmarkError}
        </div>
      )}

      {/* Aggregate Averages */}
      {benchmarkResults && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
              <Clock className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-[#a1a1a1] block">Avg Latency</span>
              <span className="text-sm font-semibold text-[#ededed] font-mono">
                {benchmarkResults.avg_total_latency_ms
                  ? formatMs(benchmarkResults.avg_total_latency_ms)
                  : benchmarkResults.avg_latency_ms
                  ? formatMs(benchmarkResults.avg_latency_ms)
                  : "N/A"}
              </span>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
              <Percent className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-[#a1a1a1] block">Avg Token Savings</span>
              <span className="text-sm font-semibold text-[#10b981] font-mono">
                {benchmarkResults.avg_token_savings_percent !== undefined
                  ? `${benchmarkResults.avg_token_savings_percent.toFixed(1)}%`
                  : "N/A"}
              </span>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[11px] text-[#a1a1a1] block">Avg Compression</span>
              <span className="text-sm font-semibold text-[#ededed] font-mono">
                {benchmarkResults.avg_compression_ratio !== undefined
                  ? `${benchmarkResults.avg_compression_ratio.toFixed(2)}x`
                  : "N/A"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Results List */}
      {benchmarkResults?.results && benchmarkResults.results.length > 0 && (
        <div className="flex flex-col gap-2">
          <h5 className="text-xs font-semibold text-[#a1a1a1]">Test Cases ({benchmarkResults.results.length})</h5>
          <div className="flex flex-col gap-2 max-h-[400px] overflow-y-auto pr-1">
            {benchmarkResults.results.map((res, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-1.5 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-[#ededed]">{res.question}</span>
                  <Badge variant={res.passed ? "success" : "danger"} size="sm">
                    {res.passed ? "Passed" : "Failed"}
                  </Badge>
                </div>

                <div className="flex items-center gap-4 text-[11px] text-[#a1a1a1] font-mono pt-1">
                  <span>Context: {formatNumber(res.context_tokens || res.token_count || 0)} tokens</span>
                  {res.token_savings_percent !== undefined && (
                    <span className="text-[#10b981]">
                      Savings: {res.token_savings_percent.toFixed(1)}%
                    </span>
                  )}
                  {res.latency_ms !== undefined && (
                    <span>Time: {formatMs(res.latency_ms)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
