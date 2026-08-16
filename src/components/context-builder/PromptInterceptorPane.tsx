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
    <div className="flex-1 h-full flex flex-col bg-card rounded-lg border border-border/80 shadow-xs overflow-hidden">
      {/* Header */}
      <div className="p-3.5 border-b border-border/80 bg-card flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-secondary flex items-center justify-center text-foreground">
            <Terminal className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
              Agent Prompt Interceptor
            </span>
            <p className="text-[11px] text-muted-foreground">Live Context Interception & Synthesis</p>
          </div>
        </div>

        {agentResponse?.intent_category && (
          <Badge variant="outline" className="text-xs font-mono px-2.5 py-1 bg-secondary/30">
            Intent: <strong className="ml-1 text-foreground">{agentResponse.intent_category}</strong>
          </Badge>
        )}
      </div>

      <div className="p-4 flex-1 flex flex-col gap-4 overflow-y-auto">
        {/* Token Budget Gauge */}
        <div className="p-3.5 rounded-lg bg-secondary/30 border border-border/70 space-y-2.5">
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2 text-foreground font-semibold">
              <Gauge className="w-4 h-4 text-primary" />
              <span>Token Budget Allocation</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-foreground font-bold">
                {currentTokens.toLocaleString()} / {maxTokens.toLocaleString()} tokens
              </span>
              <Badge variant="secondary" className="text-[10px] font-mono px-1.5 py-0 h-4">
                {tokenPercentage}%
              </Badge>
            </div>
          </div>

          <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                tokenPercentage > 95 ? "bg-amber-500" : "bg-primary"
              }`}
              style={{ width: `${tokenPercentage}%` }}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-muted-foreground pt-1 border-t border-border/40">
            <div className="flex items-center gap-2">
              <span>Target Budget:</span>
              <input
                type="number"
                min={500}
                max={128000}
                step={500}
                value={maxTokens}
                onChange={(e) => onMaxTokensChange(Number(e.target.value) || 8000)}
                className="w-20 px-2 py-1 rounded-md bg-background border border-border/80 text-foreground text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <span>tokens</span>
            </div>

            <div className="flex items-center gap-1.5">
              {[4000, 8000, 16000, 32000].map((b) => (
                <button
                  key={b}
                  onClick={() => onMaxTokensChange(b)}
                  className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                    maxTokens === b
                      ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                      : "bg-secondary/60 hover:bg-secondary text-muted-foreground hover:text-foreground border border-border/40"
                  }`}
                >
                  {b >= 1000 ? `${b / 1000}k` : b}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Prompt Input Box */}
        <div className="space-y-2 flex-1 flex flex-col">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-foreground">
              Developer Prompt / Agent Task
            </label>
            <span className="text-[11px] text-muted-foreground font-mono">
              Interception active
            </span>
          </div>

          <textarea
            value={taskPrompt}
            onChange={(e) => onPromptChange(e.target.value)}
            placeholder="Type developer task or intercepted coding agent prompt..."
            rows={5}
            className="w-full flex-1 p-3.5 text-xs font-mono bg-background border border-border/80 rounded-lg focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none text-foreground placeholder:text-muted-foreground/60 resize-none leading-relaxed"
          />

          {/* Quick Presets */}
          <div className="space-y-1.5 pt-1">
            <span className="text-[11px] font-medium text-muted-foreground">Sample Interceptions:</span>
            <div className="flex flex-col gap-1">
              {samplePrompts.map((sp, i) => (
                <button
                  key={i}
                  onClick={() => onPromptChange(sp)}
                  className="text-left text-xs font-mono px-3 py-1.5 rounded-md bg-secondary/40 hover:bg-secondary/80 border border-border/40 text-muted-foreground hover:text-foreground transition-colors truncate"
                >
                  → {sp}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Quantization Warning */}
        {agentResponse?.quantization_warning && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center gap-2.5 text-xs font-mono text-amber-400">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{agentResponse.quantization_warning}</span>
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={onExecuteContextPull}
          disabled={loading || !taskPrompt.trim()}
          size="lg"
          className="w-full font-semibold text-xs h-10 gap-2 shadow-sm"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              <span>Synthesizing Context Package...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Synthesize & Deliver Context Package</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
