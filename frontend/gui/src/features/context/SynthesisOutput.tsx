import React, { useState } from "react";
import { Copy, Check, BookmarkPlus, Zap, Clock, Cpu } from "lucide-react";
import type { AgentContextResponse } from "../../types/api";
import { Button } from "../../components/Button";
import { formatNumber, formatMs } from "../../lib/utils";
import { toast } from "../../app/providers/ToastProvider";
import ReactMarkdown from "react-markdown";

interface SynthesisOutputProps {
  result: AgentContextResponse;
  onSavePackage: () => void;
}

export const SynthesisOutput: React.FC<SynthesisOutputProps> = ({ result, onSavePackage }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(result.context_markdown);
      }
      setCopied(true);
      toast.success("Context markdown copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy context");
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0a0a] border border-[#262626] rounded-lg overflow-hidden">
      {/* Top Meta Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#262626] bg-[#000000]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-mono text-[#ededed]">
            <Zap className="w-3.5 h-3.5 text-[#a1a1a1]" />
            <span>{formatNumber(result.estimated_tokens)} tokens</span>
          </div>

          <div className="h-3.5 w-px bg-[#262626]" />

          <div className="flex items-center gap-1.5 text-xs font-mono text-[#a1a1a1]">
            <Clock className="w-3.5 h-3.5 text-[#707070]" />
            <span>{formatMs(result.generation_time_ms)}</span>
          </div>

          {result.model_name && (
            <>
              <div className="h-3.5 w-px bg-[#262626]" />
              <div className="flex items-center gap-1.5 text-xs text-[#a1a1a1]">
                <Cpu className="w-3.5 h-3.5 text-[#707070]" />
                <span className="font-mono text-[11px] truncate max-w-[140px] text-[#ededed]">
                  {result.model_name}
                </span>
                {result.model_invoked && (
                  <span className="text-[10px] px-1 py-0.2 rounded bg-[#10b981]/10 text-[#10b981] border border-[#10b981]/20 font-mono">
                    active
                  </span>
                )}
              </div>
            </>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={handleCopy}>
            {copied ? <Check className="w-3.5 h-3.5 text-[#10b981]" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </Button>

          <Button size="sm" variant="secondary" onClick={onSavePackage}>
            <BookmarkPlus className="w-3.5 h-3.5 text-[#a1a1a1]" />
            <span>Save Package</span>
          </Button>
        </div>
      </div>

      {/* Markdown Content Viewer */}
      <div className="flex-1 overflow-y-auto p-5 text-sm leading-relaxed text-[#ededed] select-text prose prose-invert max-w-none prose-pre:bg-[#000000] prose-pre:border prose-pre:border-[#262626] prose-code:font-mono prose-headings:text-[#ededed] prose-headings:font-semibold">
        <ReactMarkdown>{result.context_markdown}</ReactMarkdown>
      </div>
    </div>
  );
};
