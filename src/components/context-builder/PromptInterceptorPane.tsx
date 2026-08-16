import { Terminal, Gauge, Play, AlertTriangle } from "lucide-react";
import { AgentContextResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface PromptInterceptorPaneProps {
  taskPrompt: string;
  onPromptChange: (val: string) => void;
  onExecuteContextPull: () => void;
  loading: boolean;
  maxTokens: number;
  onMaxTokensChange: (tokens: number) => void;
  agentResponse: AgentContextResponse | null;
}

export function PromptInterceptorPane({
  taskPrompt,
  onPromptChange,
  onExecuteContextPull,
  loading,
  maxTokens,
  onMaxTokensChange,
  agentResponse,
}: PromptInterceptorPaneProps) {
  const currentTokens = agentResponse?.estimated_tokens || 0;
  const tokenPercentage = Math.min(100, Math.round((currentTokens / maxTokens) * 100));

  const samplePrompts = [
    "Find where Settings are initialized and how LLM providers are configured",
    "How does ContextService assemble context packages and what pipeline stages run?",
    "Add support for configuring LM Studio and Ollama endpoints in Settings",
  ];

  return (
    <div className="flex-1 h-full flex flex-col bg-card rounded-md border border-border shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-secondary flex items-center justify-center text-foreground border border-border">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <span className="text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
              Prompt Interceptor
            </span>
            <p className="text-xs text-muted-foreground mt-0.5">Real-time Task Context Interception</p>
          </div>
        </div>

        {agentResponse?.intent_category && (
          <Badge variant="outline" className="text-xs font-mono px-2.5 py-1 bg-secondary border-border text-foreground">
            Intent: <strong className="ml-1 text-white">{agentResponse.intent_category}</strong>
          </Badge>
        )}
      </div>

      <div className="p-5 flex-1 flex flex-col gap-4 overflow-y-auto">
        {/* Token Budget Allocation Card */}
        <div className="p-4 rounded-md bg-secondary/50 border border-border space-y-3">
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2 text-foreground font-medium">
              <Gauge className="w-4 h-4 text-foreground" />
              <span>Token Budget Allocation</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-foreground font-medium">
                {currentTokens.toLocaleString()} / {maxTokens.toLocaleString()} tokens
              </span>
              <Badge variant="outline" className="text-xs font-mono px-2 py-0 border-border bg-black text-muted-foreground">
                {tokenPercentage}%
              </Badge>
            </div>
          </div>

          <div className="w-full h-1.5 bg-black rounded-full overflow-hidden border border-border">
            <div
              className="h-full bg-white transition-all duration-300"
              style={{ width: `${tokenPercentage}%` }}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-muted-foreground pt-2 border-t border-border">
            <div className="flex items-center gap-2">
              <span>Target Budget:</span>
              <input
                type="number"
                min={500}
                max={128000}
                step={500}
                value={maxTokens}
                onChange={(e) => onMaxTokensChange(Number(e.target.value) || 8000)}
                className="w-24 px-2.5 py-1 rounded bg-black border border-border text-foreground text-xs font-mono focus:outline-none focus:ring-1 focus:ring-white"
              />
              <span>tokens</span>
            </div>

            <div className="flex items-center gap-1.5">
              {[4000, 8000, 16000, 32000].map((b) => (
                <button
                  key={b}
                  onClick={() => onMaxTokensChange(b)}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-colors ${
                    maxTokens === b
                      ? "bg-white text-black border-white font-medium"
                      : "bg-black text-muted-foreground border-border hover:text-foreground hover:bg-secondary"
                  }`}
                >
                  {b >= 1000 ? `${b / 1000}k` : b}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Developer Prompt Textarea */}
        <div className="flex-1 flex flex-col gap-2.5 min-h-[180px]">
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span className="font-semibold text-foreground uppercase tracking-wider text-xs">Intercepted Agent Request</span>
            <span className="text-xs font-mono">Natural language task</span>
          </div>

          <textarea
            value={taskPrompt}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="Type developer instruction or task prompt to synthesize context..."
            className="w-full flex-1 min-h-[160px] p-4 rounded-md bg-black border border-border text-foreground text-sm font-sans resize-none focus:outline-none focus:ring-1 focus:ring-white leading-relaxed placeholder:text-muted-foreground/60"
          />
        </div>

        {/* Quick Sample Prompts */}
        <div className="space-y-2">
          <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
            Quick Scenarios:
          </span>
          <div className="flex flex-col gap-2">
            {samplePrompts.map((p, idx) => (
              <button
                key={idx}
                onClick={() => onPromptChange(p)}
                className="text-left text-sm p-3 rounded-md bg-black/80 border border-border text-muted-foreground hover:text-foreground hover:bg-secondary hover:border-border/90 transition-colors line-clamp-1 font-sans"
              >
                "{p}"
              </button>
            ))}
          </div>
        </div>

        {/* Quantization Warning */}
        {agentResponse?.quantization_warning && (
          <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/30 flex items-center gap-2.5 text-xs font-mono text-amber-500">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{agentResponse.quantization_warning}</span>
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={onExecuteContextPull}
          disabled={loading || !taskPrompt.trim()}
          size="lg"
          className="w-full h-12 text-sm font-semibold uppercase tracking-wider font-mono gap-2.5 bg-white text-black hover:bg-neutral-200 transition-colors shadow-sm rounded-md"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
              <span>Synthesizing Context Package...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-black" />
              <span>Synthesize Context Package</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
