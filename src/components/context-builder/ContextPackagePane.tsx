import { useState } from "react";
import { FileText, Copy, Check, Download, Layers, Clock, Cpu } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AgentContextResponse } from "@/lib/api";

interface ContextPackagePaneProps {
  agentResponse: AgentContextResponse | null;
  loading: boolean;
}

export function ContextPackagePane({ agentResponse, loading }: ContextPackagePaneProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (agentResponse?.context_markdown) {
      await navigator.clipboard.writeText(agentResponse.context_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!agentResponse?.context_markdown) return;
    const blob = new Blob([agentResponse.context_markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `context-package-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full lg:w-[460px] h-full flex flex-col bg-card rounded-lg border border-border/80 shadow-xs overflow-hidden shrink-0">
      {/* Header */}
      <div className="p-3.5 border-b border-border/80 bg-card flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-secondary flex items-center justify-center text-foreground">
            <FileText className="w-3.5 h-3.5 text-primary" />
          </div>
          <div>
            <span className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              Context Package
            </span>
            <p className="text-[11px] text-muted-foreground">Markdown Delivery Ready</p>
          </div>
        </div>

        {agentResponse && (
          <Badge variant="secondary" className="text-xs font-mono px-2 py-0.5">
            {agentResponse.generation_time_ms}ms
          </Badge>
        )}
      </div>

      {/* Action Toolbar */}
      <div className="p-3 border-b border-border/80 flex items-center justify-between bg-secondary/30">
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
          <Layers className="w-3.5 h-3.5 text-primary" />
          <span>
            <strong className="text-foreground">
              {agentResponse?.estimated_tokens.toLocaleString() || 0}
            </strong>{" "}
            est. tokens
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={!agentResponse}
            className="h-8 px-2.5 text-xs gap-1.5 font-medium border-border/80 hover:bg-secondary"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-emerald-500">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Markdown</span>
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={!agentResponse}
            className="h-8 px-2.5 text-xs gap-1.5 font-medium border-border/80 hover:bg-secondary"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Save .md</span>
          </Button>
        </div>
      </div>

      {/* Package Content Viewer */}
      <ScrollArea className="flex-1 p-4 bg-background">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center p-12 text-center gap-3">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-xs font-mono text-muted-foreground">
              Synthesizing context package & AST graph...
            </p>
          </div>
        ) : agentResponse ? (
          <pre className="text-xs font-mono text-foreground whitespace-pre-wrap leading-relaxed select-text font-normal">
            {agentResponse.context_markdown}
          </pre>
        ) : (
          <div className="h-full flex flex-col items-center justify-center p-12 text-center text-muted-foreground gap-3 font-mono text-xs">
            <div className="w-10 h-10 rounded-full bg-secondary/60 flex items-center justify-center">
              <Cpu className="w-5 h-5 text-muted-foreground" />
            </div>
            <div>
              <span className="font-semibold text-foreground block text-sm">No context package generated</span>
              <span className="text-xs text-muted-foreground mt-1 block">
                Execute an intercept to synthesize structured markdown
              </span>
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Footer Metadata */}
      {agentResponse && (
        <div className="p-3 border-t border-border/80 bg-card text-xs font-mono flex items-center justify-between text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-primary" />
            <span>Generated in {(agentResponse.generation_time_ms / 1000).toFixed(2)}s</span>
          </div>
          <span className="text-emerald-500 font-semibold flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Ready for Agent
          </span>
        </div>
      )}
    </div>
  );
}
