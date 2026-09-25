import React from "react";
import {
  FileText,
  Code,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import type { AgentContextResponse } from "../../types/api";
import { Badge } from "../../components/Badge";

interface EvidenceViewerProps {
  result: AgentContextResponse;
}

const EVIDENCE_STATE_LABELS: Record<string, string> = {
  sufficient: "Sufficient",
  partial: "Partial",
  insufficient: "Insufficient",
  none: "No evidence",
  index_unavailable: "Index unavailable",
  verified: "Verified",
};

/**
 * The engine reports confidence as evidence-channel agreement only:
 * 1.0 = symbol and snippet evidence both present, 0.5 = exactly one channel,
 * 0.0 = neither. It is rendered as a qualitative tier rather than a
 * percentage so the number is never read as a probability.
 */
function describeConfidence(confidence: number | undefined): {
  label: string;
  detail: string;
} | null {
  if (confidence === undefined || confidence === null) return null;
  if (confidence >= 0.9) {
    return {
      label: "Cross-validated",
      detail: "Symbol and code-snippet evidence agree",
    };
  }
  if (confidence > 0) {
    return {
      label: "Single-channel",
      detail: "Grounded by one evidence channel only",
    };
  }
  return {
    label: "Not computed",
    detail: "No matching symbols or snippets to cross-check",
  };
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ result }) => {
  const evidenceState = result.evidence_state || "none";
  const stateVariant =
    evidenceState === "sufficient" || evidenceState === "verified"
      ? "success"
      : evidenceState === "partial"
      ? "warning"
      : evidenceState === "insufficient" || evidenceState === "none"
      ? "danger"
      : "default";

  const strengthPercent =
    typeof result.evidence_score === "number"
      ? Math.round(Math.min(1, Math.max(0, result.evidence_score)) * 100)
      : null;
  const confidence = describeConfidence(result.evidence_confidence);

  return (
    <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-3 pr-1">
      {/* 1. What task did the system understand? */}
      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626]">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
            Understood Task
          </span>
          {result.intent_category && (
            <Badge variant="default" size="sm">
              {result.intent_category}
            </Badge>
          )}
        </div>
        <p className="text-xs text-[#ededed] leading-relaxed font-medium">
          {result.task_summary || "Context generated from prompt"}
        </p>
      </div>

      {/* Abstention Notice if engine abstained */}
      {result.abstained && (
        <div className="p-3.5 rounded-lg bg-[#1c1304] border border-[#f59e0b]/25 text-[#f59e0b]">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-[#f59e0b]" />
            <span className="text-xs font-semibold">Engine abstained from unsupported claims</span>
          </div>
          <p className="text-xs text-[#f59e0b]/90 leading-relaxed">
            {result.abstention_reason || "The system refrained from hallucinating information lacking verifiable repository evidence."}
          </p>
        </div>
      )}

      {/* 2. Evidence state, strength, and confidence */}
      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#a1a1a1]" />
            <span className="text-xs text-[#ededed] font-medium">Evidence Grounding</span>
          </div>
          <Badge variant={stateVariant}>{EVIDENCE_STATE_LABELS[evidenceState] || evidenceState}</Badge>
        </div>

        {strengthPercent !== null && (
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
                Evidence strength
              </span>
              <span className="text-[11px] font-mono text-[#ededed]">{strengthPercent}%</span>
            </div>
            <div className="w-full h-1 bg-[#1a1a1a] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#ededed]/60 rounded-full"
                style={{ width: `${strengthPercent}%` }}
              />
            </div>
          </div>
        )}

        {confidence && (
          <div className="flex items-start justify-between gap-3 pt-2 border-t border-[#1a1a1a]">
            <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono pt-0.5">
              Confidence
            </span>
            <div className="flex flex-col items-end gap-0.5 min-w-0">
              <span className="text-[11px] text-[#ededed]">{confidence.label}</span>
              <span className="text-[10px] text-[#707070] text-right">{confidence.detail}</span>
            </div>
          </div>
        )}

        {!confidence && strengthPercent === null && (
          <span className="text-[11px] text-[#707070]">
            This response carries no computed evidence metrics.
          </span>
        )}
      </div>

      {/* 3. Deterministic AST Symbols (Functions / Classes) */}
      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626]">
        <div className="flex items-center gap-2 mb-2">
          <Code className="w-3.5 h-3.5 text-[#a1a1a1]" />
          <span className="text-xs font-semibold text-[#ededed]">
            Relevant AST Symbols ({result.extracted_symbols?.length || 0})
          </span>
        </div>
        {result.extracted_symbols && result.extracted_symbols.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {result.extracted_symbols.map((sym) => (
              <span
                key={sym}
                className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#121212] text-[#ededed] border border-[#262626]"
              >
                {sym}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-xs text-[#707070] italic">No specific symbols isolated</span>
        )}
      </div>

      {/* 4. Callers & Callees (Call Graph Relationships) */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-3 rounded-lg bg-[#0a0a0a] border border-[#262626]">
          <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider block mb-1.5 font-mono">
            Callers ({result.callers?.length || 0})
          </span>
          {result.callers && result.callers.length > 0 ? (
            <div className="flex flex-col gap-1 max-h-28 overflow-y-auto">
              {result.callers.map((c, idx) => (
                <span key={idx} className="text-[11px] font-mono text-[#a1a1a1] truncate">
                  {c}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-[11px] text-[#707070] italic">None detected</span>
          )}
        </div>

        <div className="p-3 rounded-lg bg-[#0a0a0a] border border-[#262626]">
          <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider block mb-1.5 font-mono">
            Callees ({result.callees?.length || 0})
          </span>
          {result.callees && result.callees.length > 0 ? (
            <div className="flex flex-col gap-1 max-h-28 overflow-y-auto">
              {result.callees.map((c, idx) => (
                <span key={idx} className="text-[11px] font-mono text-[#a1a1a1] truncate">
                  {c}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-[11px] text-[#707070] italic">None detected</span>
          )}
        </div>
      </div>

      {/* 5. Relevant Grounded Files */}
      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626]">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="w-3.5 h-3.5 text-[#a1a1a1]" />
          <span className="text-xs font-semibold text-[#ededed]">
            Grounded Files ({result.related_files?.length || 0})
          </span>
        </div>
        {result.related_files && result.related_files.length > 0 ? (
          <div className="flex flex-col gap-1">
            {result.related_files.map((file, idx) => (
              <span
                key={idx}
                className="text-[11px] font-mono text-[#a1a1a1] truncate hover:text-[#ededed] transition-colors"
                title={file}
              >
                {file}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-xs text-[#707070] italic">No grounded files</span>
        )}
      </div>
    </div>
  );
};
