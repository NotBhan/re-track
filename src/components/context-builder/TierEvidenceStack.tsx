import { useState } from "react";
import {
  FileCode,
  GitFork,
  Database,
  BrainCircuit,
  ShieldCheck,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Info,
  CheckCircle2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { AgentContextResponse } from "@/lib/api";

interface TierEvidenceStackProps {
  agentResponse: AgentContextResponse | null;
  className?: string;
}

export function TierEvidenceStack({ agentResponse, className }: TierEvidenceStackProps) {
  const [expandedTiers, setExpandedTiers] = useState<Record<string, boolean>>({
    tier1: true,
    tier2: true,
    tier3: true,
    tier4: true,
  });

  const toggleTier = (tierKey: string) => {
    setExpandedTiers((prev) => ({ ...prev, [tierKey]: !prev[tierKey] }));
  };

  if (!agentResponse) {
    return (
      <div className={cn("h-full flex flex-col items-center justify-center p-8 text-center", className)}>
        <div className="w-12 h-12 rounded-lg bg-[#0f0f0f] border border-[#222222] flex items-center justify-center mb-3 text-neutral-400">
          <ShieldCheck className="w-5 h-5 text-neutral-400" />
        </div>
        <h4 className="text-sm font-semibold text-white tracking-tight">
          Evidence Inspector Standby
        </h4>
        <p className="text-xs text-neutral-500 mt-1 max-w-xs leading-relaxed">
          Synthesize a context package to inspect the arbitrated 4-tier evidence stack and authority arbitration.
        </p>
      </div>
    );
  }

  // Tier 1: Filesystem Source (Authoritative)
  const tier1Files = Array.from(
    new Set([...(agentResponse.evidence_files || []), ...(agentResponse.related_files || [])])
  );

  // Tier 2: Manifest / AST (Authoritative)
  const tier2Symbols = Array.from(
    new Set([...(agentResponse.evidence_symbols || []), ...(agentResponse.extracted_symbols || [])])
  );
  const callers = agentResponse.callers || [];
  const callees = agentResponse.callees || [];

  // Tier 3: LanceDB / Kùzu (Derived Projections)
  const tier3Relationships = agentResponse.evidence_relationships || [];

  // Tier 4: Cognee Semantic Memory (Derived Observations)
  const tier4Observations = agentResponse.observed_evidence || [];

  // Runtime Truth attributes
  const hasEvidenceScore = typeof agentResponse.evidence_score === "number";
  const evidenceScorePercent = hasEvidenceScore
    ? Math.round((agentResponse.evidence_score as number) * 100)
    : null;

  const executingModel = agentResponse.model_invoked
    ? (agentResponse.model_name || "None")
    : "None";

  const isAbstained = Boolean(agentResponse.abstained);
  const modelClaimsDisallowed = agentResponse.model_claims_allowed === false;

  return (
    <div className={cn("space-y-4 overflow-y-auto p-4 font-sans", className)}>
      {/* Runtime Arbitration & Evidence Header */}
      <div className="bg-[#050505] border border-[#1e1e1e] rounded-lg p-3.5 space-y-3">
        <div className="flex items-center justify-between border-b border-[#141414] pb-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs font-semibold text-white tracking-tight">
              Retrieval Arbitration &amp; Evidence
            </h4>
          </div>
          <span className="text-[10px] font-mono text-neutral-500">
            Tier 1 &gt; Tier 2 &gt; Tier 3 &gt; Tier 4
          </span>
        </div>

        {/* Runtime Truth Badges Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
          <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2">
            <span className="text-[10px] text-neutral-500 uppercase block">Executing Model</span>
            <span
              className={cn(
                "font-semibold truncate block mt-0.5",
                executingModel === "None" ? "text-neutral-400" : "text-emerald-400"
              )}
              title={executingModel}
            >
              {executingModel}
            </span>
          </div>

          <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2">
            <span className="text-[10px] text-neutral-500 uppercase block">Evidence Score</span>
            <span className="font-semibold text-neutral-200 block mt-0.5">
              {hasEvidenceScore ? `${evidenceScorePercent}%` : "Not Provided"}
            </span>
          </div>

          <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2">
            <span className="text-[10px] text-neutral-500 uppercase block">Grounding State</span>
            <span
              className={cn(
                "font-semibold block mt-0.5",
                isAbstained
                  ? "text-amber-400"
                  : agentResponse.evidence_state === "sufficient"
                  ? "text-emerald-400"
                  : "text-neutral-300"
              )}
            >
              {isAbstained ? "Abstained" : agentResponse.evidence_state || "Active"}
            </span>
          </div>

          <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2">
            <span className="text-[10px] text-neutral-500 uppercase block">Model Claims</span>
            <span
              className={cn(
                "font-semibold block mt-0.5",
                modelClaimsDisallowed ? "text-amber-400" : "text-emerald-400"
              )}
            >
              {modelClaimsDisallowed ? "Disallowed" : "Permitted"}
            </span>
          </div>
        </div>

        {/* Negative Grounding Abstention Banner (Visibly Distinct from Provider Failure) */}
        {isAbstained && (
          <div className="bg-amber-950/30 border border-amber-500/40 rounded-md p-3 space-y-2">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <span className="text-xs font-semibold text-amber-300 block">
                  Negative Grounding Abstention
                </span>
                <p className="text-xs text-amber-200/90 mt-0.5 font-mono">
                  {agentResponse.abstention_reason ||
                    "Context synthesis abstained due to insufficient authoritative repository evidence."}
                </p>
              </div>
            </div>
            {agentResponse.missing_evidence && agentResponse.missing_evidence.length > 0 && (
              <div className="text-[11px] font-mono text-neutral-300 pl-6">
                <span className="text-neutral-400">Missing Subsystems:</span>{" "}
                {agentResponse.missing_evidence.join(", ")}
              </div>
            )}
            <div className="text-[10px] font-mono text-amber-400/70 pl-6">
              Contract note: This is an intentional truth boundary abstention, not an inference failure.
            </div>
          </div>
        )}

        {/* Model Claims Disallowed Notice */}
        {modelClaimsDisallowed && (
          <div className="bg-neutral-900/60 border border-amber-500/30 rounded p-2.5 flex items-center gap-2 text-xs font-mono text-amber-300">
            <Info className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>
              Model Claims Disallowed: Synthesis output is strictly constrained to extracted AST &amp; source evidence.
            </span>
          </div>
        )}
      </div>

      {/* 4-Tier Evidence Stack */}
      <div className="space-y-2.5">
        {/* Tier 1: Filesystem Source */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => toggleTier("tier1")}
            className="w-full px-3.5 py-2.5 bg-[#0e0e0e] flex items-center justify-between hover:bg-[#141414] transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2 min-w-0">
              <FileCode className="w-4 h-4 text-blue-400 shrink-0" />
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white">Tier 1: Filesystem Source</span>
                <Badge variant="outline" className="text-[10px] font-mono border-blue-500/30 text-blue-300 bg-blue-950/20">
                  Authoritative
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs font-mono text-neutral-400">
                {tier1Files.length} {tier1Files.length === 1 ? "file" : "files"}
              </span>
              {expandedTiers.tier1 ? (
                <ChevronDown className="w-3.5 h-3.5 text-neutral-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-neutral-400" />
              )}
            </div>
          </button>

          {expandedTiers.tier1 && (
            <div className="p-3 border-t border-[#1a1a1a] space-y-1.5">
              {tier1Files.length > 0 ? (
                <div className="space-y-1">
                  {tier1Files.map((file) => (
                    <div
                      key={file}
                      className="text-xs font-mono px-2.5 py-1.5 rounded bg-[#050505] border border-[#1a1a1a] text-neutral-300 flex items-center justify-between"
                    >
                      <span className="truncate">{file}</span>
                      <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1 shrink-0 ml-2">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>verified</span>
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-neutral-500 font-mono py-1">
                  No source files matched in Tier 1.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tier 2: Manifest / AST */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => toggleTier("tier2")}
            className="w-full px-3.5 py-2.5 bg-[#0e0e0e] flex items-center justify-between hover:bg-[#141414] transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2 min-w-0">
              <GitFork className="w-4 h-4 text-emerald-400 shrink-0" />
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white">Tier 2: Manifest / AST</span>
                <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/30 text-emerald-300 bg-emerald-950/20">
                  Authoritative
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs font-mono text-neutral-400">
                {tier2Symbols.length} {tier2Symbols.length === 1 ? "symbol" : "symbols"}
              </span>
              {expandedTiers.tier2 ? (
                <ChevronDown className="w-3.5 h-3.5 text-neutral-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-neutral-400" />
              )}
            </div>
          </button>

          {expandedTiers.tier2 && (
            <div className="p-3 border-t border-[#1a1a1a] space-y-3">
              {tier2Symbols.length > 0 ? (
                <div>
                  <span className="text-[10px] uppercase font-mono text-neutral-500 block mb-1">
                    Extracted Symbols
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {tier2Symbols.map((sym) => (
                      <span
                        key={sym}
                        className="text-xs font-mono bg-[#050505] border border-[#222] px-2 py-0.5 rounded text-neutral-200"
                      >
                        {sym}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-xs text-neutral-500 font-mono py-1">
                  No symbols extracted in Tier 2.
                </div>
              )}

              {(callers.length > 0 || callees.length > 0) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-[#141414]">
                  {callers.length > 0 && (
                    <div>
                      <span className="text-[10px] uppercase font-mono text-neutral-500 block mb-1">
                        Callers (Upstream)
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {callers.map((c) => (
                          <span
                            key={c}
                            className="text-[11px] font-mono bg-[#050505] border border-[#1a1a1a] px-1.5 py-0.5 rounded text-neutral-400"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {callees.length > 0 && (
                    <div>
                      <span className="text-[10px] uppercase font-mono text-neutral-500 block mb-1">
                        Callees (Downstream)
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {callees.map((c) => (
                          <span
                            key={c}
                            className="text-[11px] font-mono bg-[#050505] border border-[#1a1a1a] px-1.5 py-0.5 rounded text-neutral-400"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tier 3: LanceDB / Kùzu */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => toggleTier("tier3")}
            className="w-full px-3.5 py-2.5 bg-[#0e0e0e] flex items-center justify-between hover:bg-[#141414] transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2 min-w-0">
              <Database className="w-4 h-4 text-purple-400 shrink-0" />
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white">Tier 3: LanceDB / Kùzu</span>
                <Badge variant="outline" className="text-[10px] font-mono border-purple-500/30 text-purple-300 bg-purple-950/20">
                  Derived Projections
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs font-mono text-neutral-400">
                {tier3Relationships.length} {tier3Relationships.length === 1 ? "relation" : "relations"}
              </span>
              {expandedTiers.tier3 ? (
                <ChevronDown className="w-3.5 h-3.5 text-neutral-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-neutral-400" />
              )}
            </div>
          </button>

          {expandedTiers.tier3 && (
            <div className="p-3 border-t border-[#1a1a1a] space-y-1.5">
              {tier3Relationships.length > 0 ? (
                <div className="space-y-1">
                  {tier3Relationships.map((rel, idx) => (
                    <div
                      key={`${rel}-${idx}`}
                      className="text-xs font-mono px-2.5 py-1.5 rounded bg-[#050505] border border-[#1a1a1a] text-neutral-300"
                    >
                      {rel}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-neutral-500 font-mono py-1">
                  No projected vector/graph relationships returned for this query.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tier 4: Cognee Semantic Memory */}
        <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg overflow-hidden">
          <button
            type="button"
            onClick={() => toggleTier("tier4")}
            className="w-full px-3.5 py-2.5 bg-[#0e0e0e] flex items-center justify-between hover:bg-[#141414] transition-colors cursor-pointer text-left"
          >
            <div className="flex items-center gap-2 min-w-0">
              <BrainCircuit className="w-4 h-4 text-amber-400 shrink-0" />
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white">Tier 4: Cognee Semantic Memory</span>
                <Badge variant="outline" className="text-[10px] font-mono border-amber-500/30 text-amber-300 bg-amber-950/20">
                  Derived Observations
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs font-mono text-neutral-400">
                {tier4Observations.length} {tier4Observations.length === 1 ? "record" : "records"}
              </span>
              {expandedTiers.tier4 ? (
                <ChevronDown className="w-3.5 h-3.5 text-neutral-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-neutral-400" />
              )}
            </div>
          </button>

          {expandedTiers.tier4 && (
            <div className="p-3 border-t border-[#1a1a1a] space-y-1.5">
              {tier4Observations.length > 0 ? (
                <div className="space-y-1">
                  {tier4Observations.map((obs, idx) => (
                    <div
                      key={`${obs}-${idx}`}
                      className="text-xs font-mono px-2.5 py-1.5 rounded bg-[#050505] border border-[#1a1a1a] text-neutral-300"
                    >
                      {obs}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-neutral-500 font-mono py-1">
                  No semantic memory observations recorded.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
