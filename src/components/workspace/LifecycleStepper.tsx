import { RefreshCw, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Repository } from "@/types/repository";

interface LifecycleStepperProps {
  repository: Repository;
  fileCount: number;
  symbolCount: number;
  scanning: boolean;
  onTriggerScan: () => void;
  onOpenReindex: () => void;
}

export function LifecycleStepper({
  repository,
  fileCount,
  symbolCount,
  scanning,
  onTriggerScan,
  onOpenReindex,
}: LifecycleStepperProps) {
  const isScanning = scanning || repository.status === "scanning";
  const isIndexing = repository.status === "indexing";
  const astStatus = repository.call_graph_status || (symbolCount > 0 ? "analyzed" : "not_analyzed");

  return (
    <div className="p-4 sm:p-6 max-w-5xl w-full mx-auto space-y-6">
      <div>
        <h3 className="text-base font-bold text-white tracking-tight mb-1">
          Repository Ingestion Lifecycle
        </h3>
        <p className="text-xs text-neutral-400">
          The four sequential phases of repository analysis, truth extraction, and selective cognification.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {/* Phase 1: Scan */}
        <div className="p-4 rounded-xl bg-[#0a0a0a] border border-[#1e1e1e]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={cn(
                "w-6 h-6 rounded-full border flex items-center justify-center text-xs font-mono font-bold",
                isScanning
                  ? "bg-amber-950/60 border-amber-600 text-amber-300"
                  : "bg-[#161616] border-[#2a2a2a] text-neutral-300"
              )}>
                1
              </span>
              <h4 className="text-sm font-semibold text-white font-mono">Scan</h4>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-mono capitalize",
                isScanning
                  ? "bg-amber-950/50 text-amber-400 border-amber-800/60"
                  : repository.status === "indexed" || fileCount > 0
                  ? "bg-emerald-950/50 text-emerald-400 border-emerald-800/60"
                  : "bg-neutral-900 text-neutral-500 border-neutral-800"
              )}
            >
              {isScanning ? "Scanning..." : fileCount > 0 ? "Completed" : "Pending"}
            </Badge>
          </div>
          <p className="text-xs text-neutral-400 ml-8 leading-relaxed">
            Traverses repository folders, parses ignore rules (<code className="text-neutral-300">.gitignore</code>, <code className="text-neutral-300">.agentignore</code>), and registers {fileCount} active source files without mutating file contents.
          </p>
        </div>

        {/* Phase 2: Manifest */}
        <div className="p-4 rounded-xl bg-[#0a0a0a] border border-[#1e1e1e]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-[#161616] border border-[#2a2a2a] flex items-center justify-center text-xs font-mono font-bold text-neutral-300">
                2
              </span>
              <h4 className="text-sm font-semibold text-white font-mono">Manifest</h4>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-mono capitalize",
                fileCount > 0
                  ? "bg-emerald-950/50 text-emerald-400 border-emerald-800/60"
                  : "bg-neutral-900 text-neutral-500 border-neutral-800"
              )}
            >
              {fileCount > 0 ? "Up-to-date" : "Uncomputed"}
            </Badge>
          </div>
          <p className="text-xs text-neutral-400 ml-8 leading-relaxed">
            Computes cryptographic SHA-256 digests via <code className="text-neutral-300">ManifestService</code>. Detects added, modified, or deleted files without relying solely on filesystem timestamps.
          </p>
        </div>

        {/* Phase 3: AST Extraction */}
        <div className="p-4 rounded-xl bg-[#0a0a0a] border border-[#1e1e1e]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={cn(
                "w-6 h-6 rounded-full border flex items-center justify-center text-xs font-mono font-bold",
                astStatus === "analyzing"
                  ? "bg-amber-950/60 border-amber-600 text-amber-300"
                  : astStatus === "failed"
                  ? "bg-red-950/60 border-red-600 text-red-300"
                  : "bg-[#161616] border-[#2a2a2a] text-neutral-300"
              )}>
                3
              </span>
              <h4 className="text-sm font-semibold text-white font-mono">AST Extraction</h4>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-mono capitalize",
                astStatus === "analyzed"
                  ? "bg-emerald-950/50 text-emerald-400 border-emerald-800/60"
                  : astStatus === "analyzing"
                  ? "bg-amber-950/50 text-amber-400 border-amber-800/60"
                  : astStatus === "failed"
                  ? "bg-red-950/50 text-red-400 border-red-800/60"
                  : "bg-neutral-900 text-neutral-500 border-neutral-800"
              )}
            >
              {astStatus === "analyzing"
                ? "Analyzing..."
                : astStatus === "analyzed"
                ? `Analyzed (${symbolCount} symbols)`
                : astStatus === "failed"
                ? "Failed"
                : "Not Analyzed"}
            </Badge>
          </div>
          <p className="text-xs text-neutral-400 ml-8 leading-relaxed">
            Executes Tree-sitter parsers across Python and TypeScript files to construct the deterministic call graph, function definitions, classes, and import topology ({symbolCount} symbols).
          </p>
        </div>

        {/* Phase 4: Cognification */}
        <div className="p-4 rounded-xl bg-[#0a0a0a] border border-[#1e1e1e]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={cn(
                "w-6 h-6 rounded-full border flex items-center justify-center text-xs font-mono font-bold",
                isIndexing
                  ? "bg-amber-950/60 border-amber-600 text-amber-300"
                  : "bg-[#161616] border-[#2a2a2a] text-neutral-300"
              )}>
                4
              </span>
              <h4 className="text-sm font-semibold text-white font-mono">Cognification</h4>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-mono capitalize",
                repository.status === "indexed"
                  ? "bg-emerald-950/50 text-emerald-400 border-emerald-800/60"
                  : isIndexing
                  ? "bg-amber-950/50 text-amber-400 border-amber-800/60"
                  : "bg-neutral-900 text-neutral-500 border-neutral-800"
              )}
            >
              {repository.status === "indexed" ? "Ready" : isIndexing ? "Projecting..." : "Pending"}
            </Badge>
          </div>
          <p className="text-xs text-neutral-400 ml-8 leading-relaxed mb-3">
            Synthesizes derived artifacts across three independent storage projections. Generation is selective and incremental: not every run creates every artifact:
          </p>
          <div className="ml-8 grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs font-mono">
            <div className="p-3 rounded-lg bg-[#111111] border border-[#222222]">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-neutral-400 block text-[10px] uppercase font-bold">Semantic Memory</span>
                <Badge variant="outline" className="text-[9px] py-0 h-3.5 border-neutral-700 bg-neutral-900 text-neutral-400">
                  Cognee
                </Badge>
              </div>
              <span className="text-white font-semibold block">Semantic Observations</span>
              <span className="text-[10px] text-neutral-500 mt-1 block">AI-derived records with file &amp; SHA provenance</span>
            </div>

            <div className="p-3 rounded-lg bg-[#111111] border border-[#222222]">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-neutral-400 block text-[10px] uppercase font-bold">Vector Projection</span>
                <Badge variant="outline" className="text-[9px] py-0 h-3.5 border-neutral-700 bg-neutral-900 text-neutral-400">
                  LanceDB
                </Badge>
              </div>
              <span className="text-white font-semibold block">LanceDB Chunks</span>
              <span className="text-[10px] text-neutral-500 mt-1 block">Chunk embeddings for dense semantic retrieval</span>
            </div>

            <div className="p-3 rounded-lg bg-[#111111] border border-[#222222]">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-neutral-400 block text-[10px] uppercase font-bold">Graph Projection</span>
                <Badge variant="outline" className="text-[9px] py-0 h-3.5 border-neutral-700 bg-neutral-900 text-neutral-400">
                  Kùzu
                </Badge>
              </div>
              <span className="text-white font-semibold block">Kùzu Entity Network</span>
              <span className="text-[10px] text-neutral-500 mt-1 block">Multi-hop relational entity &amp; module graph</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Bar with clear differentiation between Incremental Scan and Full Re-index */}
      <div className="p-4 rounded-xl bg-[#0d0d0d] border border-[#222222] flex flex-col sm:flex-row items-center justify-between gap-3">
        <div>
          <h4 className="text-xs font-mono font-bold text-white uppercase">Lifecycle Controls</h4>
          <p className="text-xs text-neutral-400">
            Incremental Scan checks for modified files via ManifestService. Full Re-index re-runs parsing and storage projection.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={onTriggerScan}
            disabled={isScanning}
            className="h-8 text-xs font-mono gap-1.5 border-[#333333] hover:bg-[#1a1a1a] cursor-pointer"
          >
            <RefreshCw className={cn("w-3 h-3", isScanning && "animate-spin text-amber-400")} />
            <span>Incremental Scan</span>
          </Button>

          <Button
            size="sm"
            onClick={onOpenReindex}
            disabled={isIndexing}
            className="h-8 text-xs font-mono bg-white text-black hover:bg-neutral-200 cursor-pointer font-medium"
          >
            <Layers className="w-3 h-3" />
            <span>Full Re-index</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
