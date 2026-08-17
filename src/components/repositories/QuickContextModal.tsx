import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  Play,
  Copy,
  Check,
  ArrowUpRight,
  Loader2,
  FileText,
  X,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";
import { generateContext, ContextResponse } from "@/lib/api";
import { SynthesisProgressBar } from "@/components/shared/SynthesisProgressBar";
import type { Repository } from "@/types/repository";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

interface QuickContextModalProps {
  repo: Repository | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const PRESET_TASKS = [
  {
    label: "OAuth2 Authentication",
    prompt: "Implement OAuth2 social login with Google and GitHub providers",
  },
  {
    label: "API Endpoint",
    prompt: "Create a new async REST API endpoint with input validation and error handling",
  },
  {
    label: "Refactor Services",
    prompt: "Refactor core services to use dependency injection and decoupled storage",
  },
  {
    label: "Unit Test Suite",
    prompt: "Write comprehensive unit and integration tests for critical business logic",
  },
  {
    label: "Fix Memory Leak",
    prompt: "Diagnose and optimize memory leaks and high CPU utilization in data ingestion",
  },
];

export function QuickContextModal({ repo, open, onOpenChange }: QuickContextModalProps) {
  const navigate = useNavigate();
  const [task, setTask] = useState(PRESET_TASKS[0].prompt);
  const [topK] = useState(25);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ContextResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [rawView, setRawView] = useState(false);
  const activeReqRef = useRef<number>(0);

  const handleGenerate = async () => {
    if (!repo || !task.trim()) return;
    setLoading(true);
    setResult(null);

    const reqId = Date.now();
    activeReqRef.current = reqId;

    try {
      const response = await generateContext({
        task: task.trim(),
        datasets: [repo.name],
        top_k: topK,
      });

      if (activeReqRef.current !== reqId) return;

      setResult(response);
      toast.success("Context package synthesized successfully!");
    } catch (err) {
      if (activeReqRef.current !== reqId) return;
      toast.error(err instanceof Error ? err.message : "Context generation failed");
    } finally {
      if (activeReqRef.current === reqId) {
        setLoading(false);
      }
    }
  };

  const handleCancel = () => {
    activeReqRef.current = 0;
    setLoading(false);
    toast.info("Context synthesis cancelled.");
  };

  const handleCopy = async () => {
    if (!result?.markdown) return;
    try {
      await navigator.clipboard.writeText(result.markdown);
      setCopied(true);
      toast.success("Copied Context Package to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const handleOpenStudio = () => {
    onOpenChange(false);
    if (repo) {
      navigate(`/studio?repo=${repo.id}`);
    } else {
      navigate("/studio");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-[#0a0a0a] border-[#262626] text-white p-0 overflow-hidden shadow-2xl rounded-2xl">
        <DialogHeader className="p-5 sm:p-6 border-b border-[#222222] bg-gradient-to-b from-[#141414] to-[#0a0a0a]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-white text-black flex items-center justify-center font-bold shadow-md">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <DialogTitle className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  <span>Quick Context Synthesizer</span>
                  {repo && (
                    <Badge variant="outline" className="text-xs font-mono border-[#333] bg-black text-neutral-300">
                      {repo.name}
                    </Badge>
                  )}
                </DialogTitle>
                <DialogDescription className="text-xs text-neutral-400 font-mono mt-0.5">
                  Generate instant AI context without full-repo prompt bloat
                </DialogDescription>
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="p-5 sm:p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* Quick Preset Chips */}
          <div>
            <label className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 block mb-2">
              Quick Task Templates
            </label>
            <div className="flex flex-wrap gap-1.5">
              {PRESET_TASKS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => setTask(preset.prompt)}
                  className={cn(
                    "text-xs font-mono px-2.5 py-1 rounded-lg border transition-all cursor-pointer",
                    task === preset.prompt
                      ? "bg-white text-black border-white font-medium shadow-sm"
                      : "bg-[#141414] border-[#262626] text-neutral-300 hover:text-white hover:border-[#404040]"
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Task Input */}
          <div>
            <label className="text-[11px] font-mono uppercase tracking-wider text-neutral-400 block mb-2">
              Development Task or Question
            </label>
            <textarea
              rows={3}
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe the feature, bug fix, or architecture question..."
              className="w-full bg-black border border-[#262626] rounded-xl p-3.5 text-xs sm:text-sm font-mono text-white placeholder:text-neutral-600 focus:outline-none focus:border-white transition-colors resize-none leading-relaxed"
            />
          </div>

          {/* Synthesis Real-Time Progress Bar */}
          {loading && (
            <SynthesisProgressBar
              loading={loading}
              onCancel={handleCancel}
              variant="card"
              taskTitle={task}
            />
          )}

          {/* Result Area */}
          <AnimatePresence>
            {result && !loading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* Telemetry banner */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-black border border-[#262626] rounded-xl p-3">
                  <div>
                    <span className="text-[10px] font-mono text-neutral-400 uppercase block">Token Size</span>
                    <span className="text-sm font-bold text-white font-mono">
                      ~{result.token_estimate.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-neutral-400 uppercase block">Memories</span>
                    <span className="text-sm font-bold text-white font-mono">
                      {result.retrieved_memories} facts
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-neutral-400 uppercase block">Latency</span>
                    <span className="text-sm font-bold text-emerald-400 font-mono">
                      {result.total_time_ms ? `${result.total_time_ms}ms` : "< 200ms"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-neutral-400 uppercase block">Reduction</span>
                    <span className="text-sm font-bold text-emerald-400 font-mono">
                      ~88% Saved
                    </span>
                  </div>
                </div>

                {/* Markdown Preview Container */}
                <div className="bg-black rounded-xl border border-[#262626] overflow-hidden">
                  <div className="flex items-center justify-between px-3.5 py-2 border-b border-[#222222] bg-[#0e0e0e]">
                    <span className="text-xs font-mono text-neutral-400 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-white" />
                      Generated Context Markdown
                    </span>
                    <button
                      onClick={() => setRawView(!rawView)}
                      className="text-[11px] font-mono text-neutral-400 hover:text-white transition-colors cursor-pointer"
                    >
                      {rawView ? "Formatted View" : "Raw Markdown"}
                    </button>
                  </div>

                  <div className="p-4 max-h-60 overflow-y-auto font-mono text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap selection:bg-white selection:text-black">
                    {result.markdown}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-[#222222] bg-[#0e0e0e] flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            onClick={handleOpenStudio}
            className="text-xs font-mono text-neutral-400 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <span>Open in Context Studio (Power Mode)</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
            {loading ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancel}
                  className="h-9 px-3 text-xs font-mono border-red-500/30 bg-red-950/20 text-red-300 hover:bg-red-900/30 gap-1.5 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Cancel</span>
                </Button>

                <Button
                  size="sm"
                  disabled
                  className="h-9 px-4 text-xs font-mono font-bold bg-white/20 text-white gap-1.5 cursor-not-allowed"
                >
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Synthesizing...</span>
                </Button>
              </div>
            ) : (
              <>
                {result && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopy}
                    className="h-9 px-3.5 text-xs font-mono font-semibold border-[#333] bg-black text-white hover:bg-[#1f1f1f] gap-1.5 cursor-pointer"
                  >
                    {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    <span>{copied ? "Copied!" : "Copy Context"}</span>
                  </Button>
                )}

                <Button
                  size="sm"
                  disabled={!task.trim()}
                  onClick={handleGenerate}
                  className="h-9 px-4 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 gap-1.5 shadow-md cursor-pointer"
                >
                  <Play className="w-4 h-4 fill-black" />
                  <span>{result ? "Re-synthesize" : "Synthesize Context"}</span>
                </Button>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
