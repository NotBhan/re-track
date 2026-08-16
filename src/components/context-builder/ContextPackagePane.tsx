import { useState } from "react";
import { FileText, Copy, Check, Download, Layers } from "lucide-react";
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
    <div className="w-full lg:w-[520px] h-full flex flex-col bg-card rounded-md border border-border shadow-xs overflow-hidden shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-secondary flex items-center justify-center text-foreground border border-border">
            <FileText className="w-4 h-4 text-foreground" />
          </div>
          <div>
            <span className="text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
              Context Package
            </span>
            <p className="text-xs text-muted-foreground mt-0.5">Structured Agent Output</p>
          </div>
        </div>

        {agentResponse && (
          <Badge variant="outline" className="text-xs font-mono px-2.5 py-0.5 border-border bg-secondary text-muted-foreground">
            {agentResponse.generation_time_ms}ms
          </Badge>
        )}
      </div>

      {/* Action Toolbar */}
      <div className="p-4 border-b border-border flex items-center justify-between bg-black/40">
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
          <Layers className="w-4 h-4 text-foreground" />
          <span>
            <strong className="text-white text-sm font-semibold">
              {agentResponse?.estimated_tokens.toLocaleString() || 0}
            </strong>{" "}
            est. tokens
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={!agentResponse}
            className="h-9 px-3.5 text-xs gap-2 font-medium border-border bg-black text-foreground hover:bg-secondary rounded-md"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400 font-semibold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span>Copy Markdown</span>
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={!agentResponse}
            className="h-9 px-3.5 text-xs gap-2 font-medium border-border bg-black text-foreground hover:bg-secondary rounded-md"
          >
            <Download className="w-4 h-4" />
            <span>Save .md</span>
          </Button>
        </div>
      </div>

      {/* Content Area */}
      <ScrollArea className="flex-1 p-4 bg-black">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-3 text-center">
            <span className="text-2xl animate-spin text-muted-foreground">⚙</span>
            <p className="text-xs font-mono text-muted-foreground">
              Synthesizing structured Markdown package...
            </p>
          </div>
        ) : agentResponse?.context_markdown ? (
          <pre className="text-xs font-mono text-neutral-300 whitespace-pre-wrap break-words leading-relaxed font-normal select-text selection:bg-neutral-800">
            {agentResponse.context_markdown}
          </pre>
        ) : (
          <div className="h-64 flex flex-col items-center justify-center gap-2 text-center p-6">
            <div className="w-10 h-10 rounded bg-secondary flex items-center justify-center mb-2 border border-border">
              <FileText className="w-5 h-5 text-muted-foreground" />
            </div>
            <h4 className="text-xs font-semibold text-foreground">No context package generated yet</h4>
            <p className="text-xs text-muted-foreground max-w-xs leading-normal">
              Enter a task instruction in the prompt interceptor and click synthesize to assemble context.
            </p>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
