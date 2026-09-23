import { useState, useEffect, useMemo, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import {
  Play,
  Copy,
  Check,
  Download,
  Gauge,
  Code2,
  FileText,
  Network,
  Sparkles,
  BookmarkPlus,
  Loader2,
  AlertCircle,
  AlertTriangle,
  X,
  History,
  FolderGit2,
  Sliders,
} from "lucide-react";
import { getAgentContext, AgentContextResponse, SavedContextPackage } from "@/lib/api";
import { useRepositoryStore } from "@/stores/repository-store";
import { useContextPackageStore } from "@/stores/context-package-store";
import { useHealthStore } from "@/stores/health-store";
import { useContextStore, PRESET_WORKBENCH_PROMPTS } from "@/stores/context-store";
import { toast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CallGraphView } from "@/components/repositories/CallGraphView";
import { SynthesisProgressBar } from "@/components/shared/SynthesisProgressBar";
import { ProgressiveMarkdownReveal } from "@/components/dashboard/ProgressiveMarkdownReveal";
import { TierEvidenceStack } from "@/components/context-builder/TierEvidenceStack";
import { PackageHistoryDrawer } from "@/components/context-packages/PackageHistoryDrawer";
import type { CallGraphNode, CallGraphEdge } from "@/types/repository";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export default function ContextStudio() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const repoIdParam = searchParams.get("repo");
  const tabParam = searchParams.get("tab");

  const recommendedPrompts = useContextStore((s) => s.recommendedPrompts);
  const promptSource = useContextStore((s) => s.promptSource);
  const loadingPrompts = useContextStore((s) => s.loadingPrompts);
  const initializeRecommendedPrompts = useContextStore((s) => s.initializeRecommendedPrompts);
  const generateRecommendedPrompts = useContextStore((s) => s.generateRecommendedPrompts);

  const [taskPrompt, setTaskPrompt] = useState(PRESET_WORKBENCH_PROMPTS[0].prompt);
  const [maxTokens, setMaxTokens] = useState(8000);
  const [loading, setLoading] = useState(false);
  const [synthesisError, setSynthesisError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const [agentResponse, setAgentResponse] = useState<AgentContextResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  // Center column view: "workbench" (Tier Evidence Stack) vs "tree" (AST Call Graph)
  const [centerTab, setCenterTab] = useState<"workbench" | "tree">("workbench");

  // Right column tab: "package" vs "history"
  const [rightTab, setRightTab] = useState<"package" | "history">(
    tabParam === "history" ? "history" : "package"
  );

  // Mobile navigation tabs (< 1024px)
  const [mobileTab, setMobileTab] = useState<"prompt" | "evidence" | "topology" | "package">("prompt");

  const activeRequestIdRef = useRef<number>(0);

  const repositories = useRepositoryStore((s) => s.repositories);
  const selectedId = useRepositoryStore((s) => s.selectedId);
  const selected = useRepositoryStore((s) => s.selected);
  const fetchRepositories = useRepositoryStore((s) => s.fetchRepositories);
  const savePackage = useContextPackageStore((s) => s.savePackage);
  const health = useHealthStore((s) => s.health);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  // Sync tab with search params
  useEffect(() => {
    if (tabParam === "history") {
      setRightTab("history");
    }
  }, [tabParam]);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const repoList = Array.isArray(repositories) ? repositories : [];

  // Resolve active repository
  const activeRepo = useMemo(() => {
    if (selected) return selected;
    if (repoIdParam) {
      const found = repoList.find((r) => r.id === repoIdParam);
      if (found) return found;
    }
    if (selectedId) {
      const found = repoList.find((r) => r.id === selectedId);
      if (found) return found;
    }
    return null;
  }, [selected, repoIdParam, selectedId, repoList]);

  // Zero synthetic AST nodes: only use authentic repository metadata
  const callGraphNodes: CallGraphNode[] = useMemo(() => {
    if (activeRepo?.call_graph_nodes && Array.isArray(activeRepo.call_graph_nodes)) {
      return activeRepo.call_graph_nodes;
    }
    if (activeRepo?.metadata?.call_graph_nodes && Array.isArray(activeRepo.metadata.call_graph_nodes)) {
      return activeRepo.metadata.call_graph_nodes as CallGraphNode[];
    }
    return [];
  }, [activeRepo]);

  const callGraphEdges: CallGraphEdge[] = useMemo(() => {
    if (activeRepo?.call_graph_edges && Array.isArray(activeRepo.call_graph_edges)) {
      return activeRepo.call_graph_edges;
    }
    if (activeRepo?.metadata?.call_graph_edges && Array.isArray(activeRepo.metadata.call_graph_edges)) {
      return activeRepo.metadata.call_graph_edges as CallGraphEdge[];
    }
    return [];
  }, [activeRepo]);

  // Initialize recommended prompts when active repository is available
  useEffect(() => {
    if (activeRepo?.id) {
      initializeRecommendedPrompts(activeRepo.id);
    }
  }, [activeRepo?.id, initializeRecommendedPrompts]);

  const handleSynthesize = async () => {
    if (!activeRepo) {
      toast.error("Repository Required: Select a repository to synthesize context.");
      return;
    }
    if (!taskPrompt.trim() || loading || cooldown > 0) return;

    setLoading(true);
    setSaved(false);
    setSynthesisError(null);

    const requestId = Date.now();
    activeRequestIdRef.current = requestId;

    try {
      const response = await getAgentContext({
        task_prompt: taskPrompt.trim(),
        repository_path: activeRepo.local_path || "",
        dataset_name: activeRepo.name,
        max_tokens: maxTokens,
        include_structural_graph: true,
      });

      // Ignore if user cancelled
      if (activeRequestIdRef.current !== requestId) return;

      if (response && response.success) {
        setAgentResponse(response);
        setCooldown(1);
        setRightTab("package");
        toast.success("Context Package synthesized successfully!");
      } else {
        throw new Error(response?.context_markdown || "Context generation returned no content.");
      }
    } catch (err: any) {
      if (activeRequestIdRef.current !== requestId) return;
      const msg = err?.message || String(err) || "Failed to synthesize context package";
      setSynthesisError(msg);
      toast.error(msg);
    } finally {
      if (activeRequestIdRef.current === requestId) {
        setLoading(false);
      }
    }
  };

  const handleCancelSynthesis = () => {
    activeRequestIdRef.current = 0;
    setLoading(false);
    toast.info("Context synthesis cancelled.");
  };

  const handleCopy = async () => {
    if (!agentResponse?.context_markdown) return;
    try {
      await navigator.clipboard.writeText(agentResponse.context_markdown);
      setCopied(true);
      toast.success("Context Package copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const handleSaveToLibrary = async () => {
    if (!agentResponse?.context_markdown || !activeRepo || saved) return;
    try {
      await savePackage({
        name: `${activeRepo.name} — ${taskPrompt.slice(0, 32)}...`,
        task: taskPrompt,
        objective: agentResponse.task_summary || taskPrompt,
        repository_id: activeRepo.id,
        repository_name: activeRepo.name,
        markdown: agentResponse.context_markdown,
        token_estimate: agentResponse.estimated_tokens,
        tags: [agentResponse.intent_category || "context"],
      });
      setSaved(true);
      toast.success("Package saved to Context Library!");
    } catch {
      toast.error("Failed to save context package");
    }
  };

  const handleDownload = () => {
    if (!agentResponse?.context_markdown || !activeRepo) return;
    const blob = new Blob([agentResponse.context_markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `context-package-${activeRepo.name}-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Downloaded Context Package Markdown file");
  };

  const handleSelectPackageFromHistory = (pkg: SavedContextPackage) => {
    setTaskPrompt(pkg.task || pkg.name);
    setAgentResponse({
      success: true,
      context_markdown: pkg.markdown,
      task_summary: pkg.objective || pkg.task,
      intent_category: pkg.tags?.[0] || "saved",
      extracted_symbols: [],
      callers: [],
      callees: [],
      related_files: [],
      estimated_tokens: pkg.token_estimate || 0,
      generation_time_ms: pkg.total_time_ms || 0,
      model_invoked: false,
    });
    setRightTab("package");
    toast.info(`Loaded package: "${pkg.name}"`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSynthesize();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased font-sans">
      <TopBar
        title="RE:Track | Context Studio"
        subtitle="Prompt Workbench, Retrieval Arbitration & Context Packages"
      >
        <div className="flex items-center gap-2">
          {activeRepo && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/workspace?repo=${activeRepo.id}&tab=ast`)}
              className="h-8 px-2.5 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white hover:bg-[#1a1a1a] gap-1 cursor-pointer"
            >
              <Network className="w-3.5 h-3.5 shrink-0" />
              <span className="hidden xs:inline">AST Topology</span>
            </Button>
          )}
        </div>
      </TopBar>

      {/* Null Repository Guard Banner */}
      {!activeRepo && (
        <div className="px-4 py-2.5 bg-amber-950/40 border-b border-amber-500/30 flex items-center justify-between text-xs font-mono text-amber-300 shrink-0">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              Repository Required: No active repository selected. Please select a codebase from the TopBar to synthesize context.
            </span>
          </div>
          <Button
            size="xs"
            variant="outline"
            onClick={() => navigate("/workspace")}
            className="h-6 px-2 text-[11px] border-amber-500/30 text-amber-200 hover:bg-amber-900/30"
          >
            Go to Catalog
          </Button>
        </div>
      )}

      {/* Mobile/Tablet Segmented Tab Controller (< 1024px) */}
      <div className="lg:hidden px-4 pt-3 pb-1 border-b border-[#222222] bg-[#080808]">
        <div className="grid grid-cols-4 gap-1 bg-[#121212] p-1 rounded-lg border border-[#262626]">
          <button
            onClick={() => setMobileTab("prompt")}
            className={cn(
              "py-1.5 px-2 text-xs font-mono rounded-md transition-all flex items-center justify-center gap-1 cursor-pointer",
              mobileTab === "prompt"
                ? "bg-white text-black font-semibold shadow-xs"
                : "text-neutral-400 hover:text-white"
            )}
          >
            <Play className="w-3 h-3" />
            <span>Prompt</span>
          </button>

          <button
            onClick={() => setMobileTab("evidence")}
            className={cn(
              "py-1.5 px-2 text-xs font-mono rounded-md transition-all flex items-center justify-center gap-1 cursor-pointer",
              mobileTab === "evidence"
                ? "bg-white text-black font-semibold shadow-xs"
                : "text-neutral-400 hover:text-white"
            )}
          >
            <Sliders className="w-3 h-3" />
            <span>Evidence</span>
          </button>

          <button
            onClick={() => setMobileTab("topology")}
            className={cn(
              "py-1.5 px-2 text-xs font-mono rounded-md transition-all flex items-center justify-center gap-1 cursor-pointer",
              mobileTab === "topology"
                ? "bg-white text-black font-semibold shadow-xs"
                : "text-neutral-400 hover:text-white"
            )}
          >
            <Network className="w-3 h-3" />
            <span>Call Graph</span>
          </button>

          <button
            onClick={() => setMobileTab("package")}
            className={cn(
              "py-1.5 px-2 text-xs font-mono rounded-md transition-all flex items-center justify-center gap-1 cursor-pointer",
              mobileTab === "package"
                ? "bg-white text-black font-semibold shadow-xs"
                : "text-neutral-400 hover:text-white"
            )}
          >
            <FileText className="w-3 h-3" />
            <span>Package</span>
            {agentResponse && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_#34d399]" />
            )}
          </button>
        </div>
      </div>

      {/* Main Studio Body — 3-Column Responsive Layout */}
      <main className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden p-4 sm:p-5 gap-4 max-w-[2000px] w-full mx-auto">
        {/* COLUMN 1: Input Workbench */}
        <div
          className={cn(
            "flex flex-col h-full min-h-0 bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] overflow-hidden w-full lg:w-[32%] xl:w-[30%] min-w-[320px] max-w-[500px] shrink-0",
            mobileTab !== "prompt" ? "hidden lg:flex" : "flex"
          )}
        >
          {/* Workbench Header */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-white" />
              <h3 className="text-xs font-semibold text-white tracking-tight">Input Workbench</h3>
            </div>
            {activeRepo && (
              <span className="text-[11px] font-mono text-neutral-400 flex items-center gap-1 truncate max-w-[150px]">
                <FolderGit2 className="w-3 h-3 text-neutral-500 shrink-0" />
                <span className="truncate">{activeRepo.name}</span>
              </span>
            )}
          </div>

          {/* Workbench Scroll Area */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
            {/* Synthesis Error Recovery Banner */}
            {synthesisError && !loading && (
              <div className="bg-red-950/25 border border-red-500/30 rounded-md p-3 flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div className="flex-1 text-xs">
                  <span className="font-semibold text-red-300 block">Synthesis Error</span>
                  <p className="text-red-400/90 mt-0.5 font-mono">{synthesisError}</p>
                </div>
                <Button
                  variant="outline"
                  size="xs"
                  onClick={handleSynthesize}
                  className="h-6 px-2 text-[11px] text-neutral-200 border-[#333] hover:text-white shrink-0"
                >
                  Retry
                </Button>
              </div>
            )}

            {/* Suggested Prompts */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-neutral-300 flex items-center gap-2">
                  <span>Suggested Prompts</span>
                  {promptSource === "ai" && (
                    <Badge variant="success" className="text-[10px] font-mono px-1 py-0">
                      AI Generated
                    </Badge>
                  )}
                </label>
                {activeRepo && (
                  <button
                    type="button"
                    onClick={() => generateRecommendedPrompts(activeRepo.id, true)}
                    disabled={loadingPrompts || loading || !activeRepo}
                    className="text-xs text-neutral-400 hover:text-white disabled:opacity-40 disabled:pointer-events-none flex items-center gap-1 cursor-pointer transition-colors px-2 py-0.5 rounded border border-[#222222] bg-[#0c0c0c]"
                    title="Generate fresh prompts grounded in AST symbols"
                  >
                    {loadingPrompts ? (
                      <Loader2 className="w-3 h-3 animate-spin text-white" />
                    ) : (
                      <Sparkles className="w-3 h-3 text-amber-400" />
                    )}
                    <span>{loadingPrompts ? "Generating..." : "AI Generate"}</span>
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {recommendedPrompts.map((p) => (
                  <button
                    key={p.label + p.prompt}
                    disabled={loading || !activeRepo}
                    onClick={() => setTaskPrompt(p.prompt)}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-md border transition-colors cursor-pointer text-left disabled:opacity-50 disabled:pointer-events-none",
                      taskPrompt === p.prompt
                        ? "bg-white text-black border-white font-medium shadow-xs"
                        : "bg-[#0c0c0c] border-[#222222] text-neutral-300 hover:text-white hover:border-[#333333]"
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Prompt Textarea */}
            <div>
              <label className="text-xs font-medium text-neutral-300 block mb-1.5">
                Development Task or Technical Question
              </label>
              <textarea
                rows={5}
                value={taskPrompt}
                disabled={loading || !activeRepo}
                onChange={(e) => setTaskPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type the feature, refactoring, or question for your local memory..."
                className="w-full bg-[#050505] border border-[#222222] rounded-md p-3 text-xs font-mono text-neutral-200 placeholder:text-neutral-600 focus:outline-none focus:border-neutral-400 focus:ring-1 focus:ring-neutral-400 transition-colors resize-none leading-relaxed disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            {/* Token Budget Constraint */}
            <div className="bg-[#050505] p-3 rounded-md border border-[#1a1a1a] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-300 flex items-center gap-1.5">
                  <Gauge className="w-3.5 h-3.5 text-neutral-400" />
                  <span>Token Budget</span>
                </span>
                <span className="text-xs font-mono font-medium text-neutral-200">
                  {maxTokens.toLocaleString()} max tokens
                </span>
              </div>

              <input
                type="range"
                min={2000}
                max={32000}
                step={1000}
                value={maxTokens}
                disabled={loading || !activeRepo}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="w-full accent-white h-1 bg-[#1a1a1a] rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          {/* Workbench Footer Action */}
          <div className="p-3 border-t border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-2 shrink-0">
            <span className="text-[11px] text-neutral-500 font-mono hidden sm:inline">
              ⌘↵ to trigger
            </span>

            {loading ? (
              <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleCancelSynthesis}
                  className="h-8 px-3 text-xs gap-1 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Cancel</span>
                </Button>

                <Button
                  disabled
                  size="sm"
                  className="h-8 px-4 text-xs font-medium bg-neutral-800 text-neutral-400 gap-1.5 cursor-not-allowed"
                >
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Synthesizing...</span>
                </Button>
              </div>
            ) : (
              <Button
                disabled={cooldown > 0 || !taskPrompt.trim() || !activeRepo}
                onClick={handleSynthesize}
                size="sm"
                className="w-full sm:w-auto h-8 px-4 text-xs font-medium bg-white text-black hover:bg-neutral-200 gap-1.5 shadow-xs cursor-pointer ml-auto disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-3.5 h-3.5 fill-black" />
                <span>{agentResponse ? "Re-synthesize Context" : "Synthesize Context"}</span>
              </Button>
            )}
          </div>
        </div>

        {/* COLUMN 2: Retrieval Arbitration & Evidence Stack */}
        <div
          className={cn(
            "flex flex-col h-full min-h-0 bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] overflow-hidden flex-1 min-w-[340px]",
            mobileTab !== "evidence" && mobileTab !== "topology" ? "hidden lg:flex" : "flex"
          )}
        >
          {/* Arbitration Header & View Switcher */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-white" />
              <h3 className="text-xs font-semibold text-white tracking-tight">
                Retrieval Arbitration &amp; Evidence
              </h3>
            </div>

            <div className="flex items-center gap-1 bg-black p-0.5 rounded-md border border-[#222222]">
              <button
                onClick={() => {
                  setCenterTab("workbench");
                  setMobileTab("evidence");
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 cursor-pointer font-sans",
                  centerTab === "workbench"
                    ? "bg-white text-black font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Evidence Stack</span>
              </button>

              <button
                onClick={() => {
                  setCenterTab("tree");
                  setMobileTab("topology");
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 cursor-pointer font-sans",
                  centerTab === "tree"
                    ? "bg-white text-black font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                <Network className="w-3.5 h-3.5" />
                <span>Call Graph</span>
              </button>
            </div>
          </div>

          {/* Center Column Content */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {centerTab === "workbench" ? (
              <TierEvidenceStack agentResponse={agentResponse} className="h-full" />
            ) : (
              <div className="h-full p-4">
                <CallGraphView nodes={callGraphNodes} edges={callGraphEdges} />
              </div>
            )}
          </div>
        </div>

        {/* COLUMN 3: Context Package Viewer & History */}
        <div
          className={cn(
            "flex flex-col h-full min-h-0 bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] overflow-hidden w-full lg:w-[38%] xl:w-[38%] min-w-[380px] max-w-[700px] shrink-0",
            mobileTab !== "package" ? "hidden lg:flex" : "flex"
          )}
        >
          {/* Column Header & View Switcher */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-white" />
              <h3 className="text-xs font-semibold text-white tracking-tight">
                Context Package &amp; History
              </h3>
            </div>

            <div className="flex items-center gap-1 bg-black p-0.5 rounded-md border border-[#222222]">
              <button
                onClick={() => {
                  setRightTab("package");
                  setSearchParams({ repo: activeRepo?.id || "" });
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 cursor-pointer font-sans",
                  rightTab === "package"
                    ? "bg-white text-black font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Package</span>
              </button>

              <button
                onClick={() => {
                  setRightTab("history");
                  setSearchParams({ repo: activeRepo?.id || "", tab: "history" });
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 cursor-pointer font-sans",
                  rightTab === "history"
                    ? "bg-white text-black font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                <History className="w-3.5 h-3.5" />
                <span>History</span>
              </button>
            </div>

            {/* Action Buttons for Package View */}
            {rightTab === "package" && agentResponse && !loading && (
              <div className="flex items-center gap-1.5">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={saved}
                  onClick={handleSaveToLibrary}
                  className="h-7 px-2 text-xs gap-1 cursor-pointer disabled:opacity-60"
                >
                  <BookmarkPlus className={cn("w-3 h-3", saved ? "text-emerald-400" : "text-amber-400")} />
                  <span>{saved ? "Saved" : "Save"}</span>
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                  className="h-7 px-2 text-xs gap-1 cursor-pointer"
                >
                  <Download className="w-3 h-3" />
                  <span className="hidden sm:inline">Export</span>
                </Button>

                <Button
                  type="button"
                  size="sm"
                  onClick={handleCopy}
                  className="h-7 px-2.5 text-xs font-medium bg-white text-black hover:bg-neutral-200 gap-1 shadow-xs cursor-pointer"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? "Copied!" : "Copy Context"}</span>
                </Button>
              </div>
            )}
          </div>

          {/* Right Column Body */}
          <div className="flex-1 min-h-0 overflow-y-auto relative">
            {rightTab === "history" ? (
              <PackageHistoryDrawer
                activeRepoId={activeRepo?.id || null}
                activeRepoName={activeRepo?.name}
                onSelectPackage={handleSelectPackageFromHistory}
              />
            ) : (
              <div className="p-4 space-y-4">
                {/* Live Re-synthesis Progress Bar */}
                {loading && agentResponse && (
                  <div className="sticky top-0 z-20 mb-3">
                    <SynthesisProgressBar
                      loading={loading}
                      onCancel={handleCancelSynthesis}
                      variant="card"
                      taskTitle={`Re-synthesizing for: "${taskPrompt}"`}
                      className="w-full bg-[#0a0a0a] border border-[#262626] shadow-xl"
                    />
                  </div>
                )}

                {loading && !agentResponse ? (
                  <div className="h-full flex flex-col items-center justify-center p-6 max-w-xl mx-auto">
                    <SynthesisProgressBar
                      loading={loading}
                      onCancel={handleCancelSynthesis}
                      variant="card"
                      taskTitle={taskPrompt}
                      className="w-full"
                    />
                  </div>
                ) : agentResponse ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: loading ? 0.5 : 1 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-3"
                  >
                    {/* Telemetry Strip */}
                    <div className="bg-[#050505] border border-[#1a1a1a] rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between border-b border-[#141414] pb-2">
                        <span className="text-xs font-semibold text-white truncate">
                          Synthesized Context Package
                        </span>
                        <div className="flex items-center gap-1.5">
                          {agentResponse.abstained ? (
                            <Badge
                              variant="outline"
                              className="text-[10px] font-mono border-amber-500/40 text-amber-400 bg-amber-950/20"
                            >
                              Abstained
                            </Badge>
                          ) : agentResponse.model_invoked ? (
                            <Badge variant="success" className="text-[10px] font-mono">
                              Model Synthesized
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px] font-mono text-neutral-400">
                              Deterministic AST
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* Telemetry Metrics Row */}
                      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 text-xs font-mono text-neutral-400">
                        <div className="flex items-center gap-1.5">
                          <span className="text-neutral-500">Tokens:</span>
                          <span className="text-neutral-200 font-medium">
                            ~{agentResponse.estimated_tokens.toLocaleString()} tokens
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-neutral-500">Latency:</span>
                          <span className="text-emerald-400 font-medium">
                            {agentResponse.total_time_ms || agentResponse.generation_time_ms}ms
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-neutral-500">Sources:</span>
                          <span className="text-neutral-200 font-medium">
                            {(agentResponse.related_files?.length ?? 0)} files
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-neutral-500">Inference:</span>
                          <span className="text-emerald-400 font-medium truncate max-w-[120px]">
                            {agentResponse.model_invoked
                              ? agentResponse.model_name || "None"
                              : "None"}
                          </span>
                        </div>
                        {typeof agentResponse.evidence_score === "number" && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-neutral-500">Score:</span>
                            <span className="text-neutral-200 font-medium">
                              {Math.round(agentResponse.evidence_score * 100)}%
                            </span>
                          </div>
                        )}
                      </div>

                      {health?.high_memory_pressure && (
                        <div className="text-[10px] font-mono text-amber-400 pt-1">
                          Notice: High RAM pressure ({health.ram_percent}%) on host machine.
                        </div>
                      )}
                    </div>

                    {/* Markdown Reveal */}
                    <ProgressiveMarkdownReveal markdown={agentResponse.context_markdown} />
                  </motion.div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center p-8 text-center">
                    <div className="w-12 h-12 rounded-lg bg-[#0f0f0f] border border-[#222222] flex items-center justify-center mb-3 text-neutral-400">
                      <Sparkles className="w-5 h-5 text-neutral-400" />
                    </div>
                    <h4 className="text-sm font-semibold text-white tracking-tight">
                      No Context Package Generated Yet
                    </h4>
                    <p className="text-xs text-neutral-500 mt-1 max-w-sm leading-relaxed">
                      Enter your task in the Input Workbench on the left and click &ldquo;Synthesize Context&rdquo; to retrieve compact memories.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
