import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import {
  GitBranch,
  Play,
  Copy,
  Check,
  Download,
  Gauge,
  Code2,
  FileText,
  ChevronDown,
  Network,
  Sparkles,
  BookmarkPlus,
  ShieldCheck,
  Loader2,
  AlertCircle,
  X,
} from "lucide-react";
import { getAgentContext, AgentContextResponse, getSuggestedPrompts, SuggestedPrompt } from "@/lib/api";
import { useRepositoryStore } from "@/stores/repository-store";
import { useContextPackageStore } from "@/stores/context-package-store";
import { useHealthStore } from "@/stores/health-store";
import { toast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CallGraphView } from "@/components/repositories/CallGraphView";
import { SynthesisProgressBar } from "@/components/shared/SynthesisProgressBar";
import { ProgressiveMarkdownReveal } from "@/components/dashboard/ProgressiveMarkdownReveal";
import { EvidenceProvenanceLayer } from "@/components/context-builder/EvidenceProvenanceLayer";
import type { CallGraphNode, CallGraphEdge } from "@/types/repository";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

const PRESET_WORKBENCH_PROMPTS: SuggestedPrompt[] = [
  {
    label: "Settings & Providers",
    prompt: "Find where Settings are initialized and how LLM providers are configured and hot-reloaded.",
  },
  {
    label: "OAuth2 Login",
    prompt: "Implement OAuth2 login with Google and GitHub providers including session tokens.",
  },
  {
    label: "AST Call Graph",
    prompt: "Show how AST call graphs are extracted from Python and TypeScript source files.",
  },
  {
    label: "Memory Indexing",
    prompt: "How does the IndexingService discover files, filter ignore patterns, and batch memories into Cognee?",
  },
  {
    label: "Context Budget",
    prompt: "Explain how BudgetManager trims low-priority sections and compresses tokens at line boundaries.",
  },
];

export default function ContextStudio() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const repoIdParam = searchParams.get("repo");

  const [presetPrompts, setPresetPrompts] = useState<SuggestedPrompt[]>(PRESET_WORKBENCH_PROMPTS);
  const [loadingPrompts, setLoadingPrompts] = useState(false);
  const [promptSource, setPromptSource] = useState<"ai" | "heuristic" | "preset">("preset");

  const [taskPrompt, setTaskPrompt] = useState(PRESET_WORKBENCH_PROMPTS[0].prompt);
  const [maxTokens, setMaxTokens] = useState(8000);
  const [loading, setLoading] = useState(false);
  const [synthesisError, setSynthesisError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const [agentResponse, setAgentResponse] = useState<AgentContextResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  // Responsive mode tabs: on mobile/tablet, user can switch between 'prompt', 'topology', and 'package'
  const [mobileTab, setMobileTab] = useState<"prompt" | "topology" | "package">("prompt");
  // Desktop inner tab: 'workspace' (prompt) vs 'tree' (AST/topology)
  const [desktopTab, setDesktopTab] = useState<"workspace" | "tree">("workspace");

  const [repoDropdownOpen, setRepoDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const activeRequestIdRef = useRef<number>(0);

  const repositories = useRepositoryStore((s) => s.repositories);
  const fetchRepositories = useRepositoryStore((s) => s.fetchRepositories);
  const savePackage = useContextPackageStore((s) => s.savePackage);
  const health = useHealthStore((s) => s.health);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  // Click outside repository selector dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setRepoDropdownOpen(false);
      }
    }
    if (repoDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [repoDropdownOpen]);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const activeRepo =
    repositories.find((r) => r.id === repoIdParam) ||
    repositories[0] || {
      id: "local",
      name: "re-track",
      local_path: "/home/chandrabhan/Documents/Personal Projects/re-track",
    };

  // Extract call graph nodes and edges
  const callGraphNodes: CallGraphNode[] = useMemo(() => {
    if (activeRepo?.metadata?.call_graph_nodes && Array.isArray(activeRepo.metadata.call_graph_nodes)) {
      return activeRepo.metadata.call_graph_nodes;
    }
    return [
      { id: "App", label: "App", file: "src/App.tsx", kind: "component" },
      { id: "ContextStudio", label: "ContextStudio", file: "src/pages/ContextStudio.tsx", kind: "component" },
      { id: "ContextService", label: "ContextService", file: "backend/app/services/context_service.py", kind: "class" },
      { id: "CogneeService", label: "CogneeService", file: "backend/app/services/cognee_service.py", kind: "class" },
      { id: "PackageBuilder", label: "PackageBuilder", file: "backend/app/services/package_builder.py", kind: "class" },
    ];
  }, [activeRepo]);

  const callGraphEdges: CallGraphEdge[] = useMemo(() => {
    if (activeRepo?.metadata?.call_graph_edges && Array.isArray(activeRepo.metadata.call_graph_edges)) {
      return activeRepo.metadata.call_graph_edges;
    }
    return [
      { source: "App", target: "ContextStudio", kind: "renders" },
      { source: "ContextStudio", target: "ContextService", kind: "calls" },
      { source: "ContextService", target: "CogneeService", kind: "calls" },
      { source: "ContextService", target: "PackageBuilder", kind: "calls" },
    ];
  }, [activeRepo]);

  // Fetch suggested prompts for active repo
  const handleFetchSuggestedPrompts = useCallback(
    async (isManual = false) => {
      if (!activeRepo?.id) return;
      setLoadingPrompts(true);
      try {
        const res = await getSuggestedPrompts(activeRepo.id);
        if (res.prompts && res.prompts.length > 0) {
          setPresetPrompts(res.prompts);
          setPromptSource(res.source as "ai" | "heuristic");
          if (isManual) {
            toast.success(
              res.source === "ai"
                ? "Generated fresh AI prompts from loaded model"
                : "Generated repository-tailored task prompts"
            );
          }
        }
      } catch (e) {
        console.debug("Failed to load suggested prompts", e);
      } finally {
        setLoadingPrompts(false);
      }
    },
    [activeRepo?.id]
  );

  useEffect(() => {
    if (activeRepo?.id) {
      handleFetchSuggestedPrompts(false);
    }
  }, [activeRepo?.id, handleFetchSuggestedPrompts]);

  const handleSynthesize = async () => {
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

      // Ignore stale response if request was cancelled
      if (activeRequestIdRef.current !== requestId) return;

      if (response && response.success) {
        setAgentResponse(response);
        setCooldown(1);
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
      toast.success("Package saved to Context Library (/packages)!");
    } catch {
      toast.error("Failed to save context package");
    }
  };

  const handleDownload = () => {
    if (!agentResponse?.context_markdown) return;
    const blob = new Blob([agentResponse.context_markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `context-package-${activeRepo.name}-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Downloaded Context Package Markdown file");
  };

  // Keyboard shortcut Ctrl+Enter to trigger synthesis
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
        subtitle="Prompt Workbench & Context Package Synthesizer"
      >
        <div className="flex items-center gap-2">
          {/* Active Workspace Selector Dropdown */}
          <div ref={dropdownRef} className="relative">
            <button
              onClick={() => setRepoDropdownOpen(!repoDropdownOpen)}
              className="h-8 px-3 rounded-lg border border-[#262626] bg-[#0a0a0a] text-white hover:border-[#404040] transition-colors flex items-center gap-2 text-xs font-mono cursor-pointer"
            >
              <GitBranch className="w-3.5 h-3.5 text-white" />
              <span className="font-semibold truncate max-w-[140px]">{activeRepo.name}</span>
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </button>

            {repoDropdownOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-64 bg-black border border-[#2e2e2e] rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden">
                <div className="px-3 py-1.5 border-b border-[#222]">
                  <span className="text-[10px] font-mono uppercase text-neutral-400">Select Codebase</span>
                </div>
                <div className="max-h-48 overflow-y-auto py-1">
                  {repositories.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => {
                        setSearchParams({ repo: r.id });
                        setRepoDropdownOpen(false);
                      }}
                      className={cn(
                        "w-full px-3 py-2 text-left text-xs font-mono flex items-center justify-between hover:bg-[#1a1a1a] transition-colors cursor-pointer",
                        r.id === activeRepo.id ? "text-white bg-[#141414] font-bold" : "text-neutral-300"
                      )}
                    >
                      <span className="truncate">{r.name}</span>
                      {r.id === activeRepo.id && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(`/knowledge/${activeRepo.id}`)}
            className="h-8 px-2.5 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white hover:bg-[#1a1a1a] gap-1 cursor-pointer"
          >
            <Network className="w-3.5 h-3.5" />
            <span>AST Map</span>
          </Button>
        </div>
      </TopBar>

      {/* Mobile/Tablet Segmented Tab Controller (< 1024px) */}
      <div className="lg:hidden px-4 pt-3 pb-1 border-b border-[#222222] bg-[#080808]">
        <div className="grid grid-cols-3 gap-1 bg-[#121212] p-1 rounded-lg border border-[#262626]">
          <button
            onClick={() => setMobileTab("prompt")}
            className={`py-1.5 px-2 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              mobileTab === "prompt"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Play className="w-3 h-3" />
            <span>Prompt</span>
          </button>

          <button
            onClick={() => setMobileTab("topology")}
            className={`py-1.5 px-2 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              mobileTab === "topology"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Network className="w-3 h-3" />
            <span>Call Graph</span>
          </button>

          <button
            onClick={() => setMobileTab("package")}
            className={`py-1.5 px-2 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              mobileTab === "package"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <FileText className="w-3 h-3" />
            <span>Package</span>
            {agentResponse && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_#34d399]" />
            )}
          </button>
        </div>
      </div>

      {/* Main Studio Body — Responsive 2/3-Column Layout */}
      <main className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden p-4 sm:p-6 gap-6 max-w-[1900px] w-full mx-auto">
        {/* Left Column: Prompt Workbench & AST Topology */}
        <div
          className={`w-full lg:w-[48%] xl:w-[45%] flex-shrink-0 flex flex-col h-full min-h-0 bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] overflow-hidden ${
            mobileTab === "package" ? "hidden lg:flex" : "flex"
          }`}
        >
          {/* Inner Tab Control (Prompt Workbench vs Call Graph) */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-1 bg-black p-0.5 rounded-md border border-[#222222]">
              <button
                onClick={() => {
                  setDesktopTab("workspace");
                  setMobileTab("prompt");
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 cursor-pointer",
                  desktopTab === "workspace"
                    ? "bg-white text-black font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>Prompt Workbench</span>
              </button>

              <button
                onClick={() => {
                  setDesktopTab("tree");
                  setMobileTab("topology");
                }}
                className={cn(
                  "px-2.5 py-1 text-xs rounded transition-colors flex items-center gap-1.5 cursor-pointer",
                  desktopTab === "tree"
                    ? "bg-white text-black font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white"
                )}
              >
                <Network className="w-3.5 h-3.5" />
                <span>AST Call Graph</span>
              </button>
            </div>

            <span className="text-[11px] text-neutral-500 hidden sm:flex items-center gap-1.5 font-mono">
              <span>Shortcut:</span>
              <kbd className="px-1 py-0.5 rounded bg-[#141414] border border-[#262626] text-neutral-300 text-[10px]">
                ⌘↵
              </kbd>
            </span>
          </div>

          {/* Workbench Tab Content */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
            {desktopTab === "workspace" ? (
              <>
                {/* Synthesis Error Recovery Banner */}
                {synthesisError && !loading && (
                  <div className="bg-red-950/25 border border-red-500/30 rounded-md p-3 flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <div className="flex-1 text-xs">
                      <span className="font-semibold text-red-300 block">Synthesis Error</span>
                      <p className="text-red-400/90 mt-0.5">{synthesisError}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="xs"
                      onClick={handleSynthesize}
                      className="h-6 px-2 text-[11px] text-neutral-200 border-[#333] hover:text-white"
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
                    <button
                      type="button"
                      onClick={() => handleFetchSuggestedPrompts(true)}
                      disabled={loadingPrompts || loading}
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
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {presetPrompts.map((p) => (
                      <button
                        key={p.label + p.prompt}
                        disabled={loading}
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
                    disabled={loading}
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
                      Token Budget Constraint
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
                    disabled={loading}
                    onChange={(e) => setMaxTokens(Number(e.target.value))}
                    className="w-full accent-white h-1 bg-[#1a1a1a] rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>

                {/* Intent Parser & Guardrails Feedback */}
                {agentResponse && !loading && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-[#050505] rounded-md border border-[#1a1a1a] p-3 space-y-2.5"
                  >
                    <div className="flex items-center justify-between border-b border-[#181818] pb-1.5">
                      <span className="text-xs font-medium text-neutral-200 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                        Intent Parser &amp; Guardrails
                      </span>
                      <Badge variant="outline" className="text-[10px] font-mono">
                        {agentResponse.intent_category || "Semantic Query"}
                      </Badge>
                    </div>

                    <p className="text-xs text-neutral-300 leading-relaxed">
                      {agentResponse.task_summary}
                    </p>

                    {agentResponse.extracted_symbols && agentResponse.extracted_symbols.length > 0 && (
                      <div>
                        <span className="text-[11px] text-neutral-500 block mb-1">
                          Extracted Symbols:
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {agentResponse.extracted_symbols.map((sym) => (
                            <span
                              key={sym}
                              className="text-[11px] font-mono bg-[#101010] border border-[#222222] px-1.5 py-0.5 rounded text-neutral-300"
                            >
                              {sym}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </>
            ) : (
              /* AST Call Graph Tab */
              <div className="h-full min-h-[400px]">
                <CallGraphView
                  nodes={callGraphNodes}
                  edges={callGraphEdges}
                />
              </div>
            )}
          </div>

          {/* Workbench Footer Action */}
          <div className="p-3 border-t border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-3 shrink-0">
            <span className="text-xs text-neutral-500 hidden sm:inline">
              {loading ? "Processing local memory graph..." : "Ready to query Cognee memory graph"}
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
                disabled={cooldown > 0 || !taskPrompt.trim()}
                onClick={handleSynthesize}
                size="sm"
                className="w-full sm:w-auto h-8 px-4 text-xs font-medium bg-white text-black hover:bg-neutral-200 gap-1.5 shadow-xs cursor-pointer ml-auto"
              >
                <Play className="w-3.5 h-3.5 fill-black" />
                <span>{agentResponse ? "Re-synthesize Context" : "Synthesize Context Package"}</span>
              </Button>
            )}
          </div>
        </div>

        {/* Right Column: Generated Context Package */}
        <div
          className={`flex-1 min-h-0 flex flex-col h-full bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] overflow-hidden ${
            mobileTab !== "package" ? "hidden lg:flex" : "flex"
          }`}
        >
          {/* Header & Export Actions */}
          <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-neutral-300" />
              <h3 className="text-xs font-semibold text-white tracking-tight">
                Synthesized Context Package
              </h3>
              {loading ? (
                <Badge variant="warning" className="text-[10px] font-mono flex items-center gap-1">
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                  <span>Re-synthesizing</span>
                </Badge>
              ) : agentResponse ? (
                <Badge variant="success" className="text-[10px] font-mono">
                  Ready
                </Badge>
              ) : null}
            </div>

            {agentResponse && !loading && (
              <div className="flex items-center gap-1.5">
                <Button
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
                  variant="outline"
                  size="sm"
                  onClick={handleDownload}
                  className="h-7 px-2 text-xs gap-1 cursor-pointer"
                >
                  <Download className="w-3 h-3" />
                  <span className="hidden sm:inline">Export</span>
                </Button>

                <Button
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

          {/* Package Content & Telemetry */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4 relative">
            {/* If synthesizing and already has a package, show live re-synthesis card overlay */}
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

            {/* If synthesizing and NO previous response */}
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
                {/* Task -> Codebase -> Context Package Relationship Strip */}
                <div className="bg-[#050505] border border-[#1a1a1a] rounded-lg p-3 space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#141414] pb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-[10px] uppercase font-mono tracking-wider text-neutral-500 shrink-0">
                        Task Target
                      </span>
                      <span className="text-xs text-neutral-200 font-medium truncate">
                        &ldquo;{agentResponse.task_summary || taskPrompt}&rdquo;
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 text-xs font-mono text-neutral-400">
                      <GitBranch className="w-3 h-3 text-neutral-300" />
                      <span className="text-white font-medium">{activeRepo.name}</span>
                    </div>
                  </div>

                  {/* Compact Metadata Row */}
                  <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 text-xs font-mono text-neutral-400">
                    <div className="flex items-center gap-1.5">
                      <span className="text-neutral-500">Context:</span>
                      <span className="text-neutral-200 font-medium">
                        ~{agentResponse.estimated_tokens.toLocaleString()} tokens
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-neutral-500">Latency:</span>
                      <span className="text-emerald-400 font-medium">
                        {agentResponse.total_time_ms || agentResponse.generation_time_ms}ms
                      </span>
                      {agentResponse.retrieval_time_ms !== undefined && (
                        <span className="text-[10px] text-neutral-500 hidden sm:inline">
                          (retrieval: {agentResponse.retrieval_time_ms}ms · synthesis: {agentResponse.synthesis_time_ms || 0}ms)
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-neutral-500">Sources:</span>
                      <span className="text-neutral-200 font-medium">
                        {agentResponse.related_files.length} files
                      </span>
                    </div>
                    {health?.high_memory_pressure && (
                      <div className="flex items-center gap-1 text-[10px] text-amber-400">
                        <span>High RAM Pressure ({health.ram_percent}%)</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* What RE:Track Found - Evidence & Source Provenance Layer */}
                <EvidenceProvenanceLayer agentResponse={agentResponse} />

                {/* Generated Context Package Markdown */}
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
                  Enter your task in the Prompt Workbench on the left and click &ldquo;Synthesize Context Package&rdquo; to retrieve compact memories.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
