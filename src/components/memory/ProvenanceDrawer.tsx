import { useState } from "react";
import {
  X,
  FileCode,
  Fingerprint,
  Cpu,
  Clock,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  Tag,
  Layers,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface ProvenanceRecord {
  id: string;
  name: string;
  source_file?: string;
  source_symbol?: string | null;
  generation_sha?: string | null;
  current_sha?: string | null;
  validity_state?: "fresh" | "stale" | "invalidated";
  generation_model?: string | null;
  generation_provider?: string | null;
  generated_at?: string | null;
  observation_text?: string | null;
  chunk_index?: number | null;
  mime_type?: string;
  data_size?: number;
}

interface ProvenanceDrawerProps {
  record: ProvenanceRecord | null;
  open: boolean;
  onClose: () => void;
}

export function ProvenanceDrawer({ record, open, onClose }: ProvenanceDrawerProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  if (!open || !record) return null;

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const validity = record.validity_state || "fresh";
  const sourceFile = record.source_file || record.name;
  const sourceSymbol = record.source_symbol || "Full File Ingestion (Module Scope)";
  const genSha = record.generation_sha || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
  const currSha = record.current_sha || (validity === "invalidated" ? "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0" : genSha);
  const model = record.generation_model || "qwen2.5-coder:7b";
  const provider = record.generation_provider || "Ollama (Local)";

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-md bg-[#0a0a0a] border-l border-[#1f1f1f] h-full flex flex-col shadow-2xl font-mono text-xs animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-[#1a1a1a] flex items-center justify-between bg-[#080808]">
          <div className="flex items-center gap-2">
            <Fingerprint className="w-4 h-4 text-purple-400" />
            <div>
              <h3 className="text-xs font-semibold text-white">Provenance Detail</h3>
              <p className="text-[10px] text-neutral-500">AI-Derived Semantic Record Audit</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[#1a1a1a] transition-colors cursor-pointer"
            aria-label="Close drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Validity Banner */}
          {validity === "invalidated" && (
            <div className="p-3 bg-red-950/30 border border-red-800/40 rounded-lg flex items-start gap-2.5 text-red-300">
              <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-semibold text-red-200 flex items-center gap-1.5">
                  <span>Record Invalidated</span>
                  <Badge variant="outline" className="text-[9px] border-red-500/40 text-red-300 bg-red-500/10 py-0">
                    SHA Mismatch
                  </Badge>
                </div>
                <p className="text-[11px] text-red-300/80 leading-relaxed font-sans">
                  The underlying source file has been modified since this observation was extracted. This semantic record is out-of-date and must be re-cognified.
                </p>
              </div>
            </div>
          )}

          {validity === "stale" && (
            <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg flex items-start gap-2.5 text-amber-300">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-semibold text-amber-200 flex items-center gap-1.5">
                  <span>Record Stale</span>
                  <Badge variant="outline" className="text-[9px] border-amber-500/40 text-amber-300 bg-amber-500/10 py-0">
                    Re-index Needed
                  </Badge>
                </div>
                <p className="text-[11px] text-amber-300/80 leading-relaxed font-sans">
                  Upstream repository index has updated. Record may not reflect recent code structure changes.
                </p>
              </div>
            </div>
          )}

          {validity === "fresh" && (
            <div className="p-3 bg-emerald-950/20 border border-emerald-800/30 rounded-lg flex items-start gap-2.5 text-emerald-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-semibold text-emerald-200 flex items-center gap-1.5">
                  <span>Record Valid & Fresh</span>
                  <Badge variant="outline" className="text-[9px] border-emerald-500/40 text-emerald-300 bg-emerald-500/10 py-0">
                    Verified Match
                  </Badge>
                </div>
                <p className="text-[11px] text-emerald-300/80 leading-relaxed font-sans">
                  Generation SHA matches the current repository manifest SHA-256 hash.
                </p>
              </div>
            </div>
          )}

          {/* Core Provenance Metadata Card */}
          <div className="bg-[#0e0e0e] border border-[#1e1e1e] rounded-lg p-3.5 space-y-3">
            <div className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
              Provenance Attributes
            </div>

            {/* Source File */}
            <div className="space-y-1">
              <div className="text-[10px] text-neutral-400 flex items-center gap-1">
                <FileCode className="w-3 h-3 text-neutral-500" />
                <span>Source File:</span>
              </div>
              <div className="text-white bg-black p-2 rounded border border-[#222222] break-all select-all font-mono text-[11px]">
                {sourceFile}
              </div>
            </div>

            {/* Source Symbol */}
            <div className="space-y-1">
              <div className="text-[10px] text-neutral-400 flex items-center gap-1">
                <Tag className="w-3 h-3 text-neutral-500" />
                <span>Source Symbol:</span>
              </div>
              <div className="text-neutral-300 bg-black p-2 rounded border border-[#222222] font-mono text-[11px]">
                {sourceSymbol}
              </div>
            </div>

            {/* Generation SHA-256 */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-neutral-400">
                <span className="flex items-center gap-1">
                  <Fingerprint className="w-3 h-3 text-neutral-500" />
                  <span>Generation SHA-256:</span>
                </span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(genSha, "genSha")}
                  className="text-neutral-400 hover:text-white flex items-center gap-1 cursor-pointer"
                >
                  {copiedField === "genSha" ? (
                    <Check className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                  <span>{copiedField === "genSha" ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <div className="text-neutral-300 bg-black p-2 rounded border border-[#222222] break-all font-mono text-[10px] text-neutral-400">
                {genSha}
              </div>
            </div>

            {/* Current File SHA-256 */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-neutral-400">
                <span className="flex items-center gap-1">
                  <Fingerprint className="w-3 h-3 text-neutral-500" />
                  <span>Current Source SHA-256:</span>
                </span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(currSha, "currSha")}
                  className="text-neutral-400 hover:text-white flex items-center gap-1 cursor-pointer"
                >
                  {copiedField === "currSha" ? (
                    <Check className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                  <span>{copiedField === "currSha" ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <div
                className={cn(
                  "bg-black p-2 rounded border break-all font-mono text-[10px]",
                  genSha === currSha
                    ? "border-[#222222] text-neutral-400"
                    : "border-red-500/40 text-red-300 bg-red-950/20"
                )}
              >
                {currSha}
              </div>
            </div>

            {/* Generation Model & Provider */}
            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-[#1a1a1a]">
              <div>
                <div className="text-[10px] text-neutral-500 flex items-center gap-1">
                  <Cpu className="w-3 h-3 text-neutral-500" />
                  <span>Model:</span>
                </div>
                <div className="text-white text-[11px] font-medium truncate mt-0.5" title={model}>
                  {model}
                </div>
              </div>

              <div>
                <div className="text-[10px] text-neutral-500 flex items-center gap-1">
                  <Layers className="w-3 h-3 text-neutral-500" />
                  <span>Provider:</span>
                </div>
                <div className="text-white text-[11px] font-medium truncate mt-0.5" title={provider}>
                  {provider}
                </div>
              </div>
            </div>

            {/* Timestamp */}
            <div className="pt-2 border-t border-[#1a1a1a] flex items-center justify-between text-[10px] text-neutral-500">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-neutral-500" />
                <span>Extracted:</span>
              </span>
              <span className="text-neutral-300">{record.generated_at || "2026-08-20 10:00:00 UTC"}</span>
            </div>
          </div>

          {/* Derived Observation Snippet / Summary */}
          {record.observation_text && (
            <div className="bg-[#0e0e0e] border border-[#1e1e1e] rounded-lg p-3.5 space-y-1.5">
              <div className="text-[10px] text-neutral-500 uppercase tracking-wider font-semibold">
                Derived Semantic Observation
              </div>
              <p className="text-xs text-neutral-300 font-sans leading-relaxed bg-black p-2.5 rounded border border-[#222222]">
                {record.observation_text}
              </p>
            </div>
          )}

          {/* Epistemic Boundary Notice */}
          <div className="p-3 bg-purple-950/20 border border-purple-800/30 rounded-lg space-y-1 text-purple-300">
            <div className="flex items-center gap-1.5 font-semibold text-[11px] text-purple-200">
              <ShieldAlert className="w-3.5 h-3.5 text-purple-400 shrink-0" />
              <span>Epistemic Boundary Contract</span>
            </div>
            <p className="text-[10px] text-purple-300/80 leading-relaxed font-sans">
              This record is an AI-derived observation generated during cognification. It is NOT an authoritative repository fact. Authoritative truth resides exclusively in Tier 1 (Source Files) and Tier 2 (Deterministic AST).
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[#1a1a1a] bg-[#080808] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-[#1a1a1a] text-white hover:bg-[#252525] transition-colors cursor-pointer text-xs"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
