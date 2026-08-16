import { useState, useEffect, useMemo, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import {
  Folder,
  Search,
  GitBranch,
  Play,
  Copy,
  Check,
  Download,
  Gauge,
  Code2,
  FileText,
  AlertCircle,
  Layers,
  Box,
  ChevronDown,
  FolderGit2,
  Network,
  List,
} from "lucide-react";
import { getAgentContext, AgentContextResponse } from "@/lib/api";
import { useRepositoryStore } from "@/stores/repository-store";
import { toast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { CallGraphView } from "@/components/repositories/CallGraphView";

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const repoIdParam = searchParams.get("repo");

  const [taskPrompt, setTaskPrompt] = useState(
    "Find where Settings are initialized and how LLM providers are configured"
  );
  const [maxTokens, setMaxTokens] = useState(8000);
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [agentResponse, setAgentResponse] = useState<AgentContextResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"workspace" | "tree">("workspace");
  const [astView, setAstView] = useState<"list" | "graph">("list");

  const [searchRepo, setSearchRepo] = useState("");
  const [selectedSubfolder, setSelectedSubfolder] = useState("backend/app/services");
  const [repoDropdownOpen, setRepoDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const repositories = useRepositoryStore((s) => s.repositories);
  const fetchRepositories = useRepositoryStore((s) => s.fetchRepositories);

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

  // Derive dynamic AST and module items from active repository scan & metadata
  const subfolders = useMemo(() => {
    const items: Array<{ path: string; description: string; type: "component" | "entry" | "framework" | "module" }> = [];

    if (activeRepo.entry_points && activeRepo.entry_points.length > 0) {
      for (const ep of activeRepo.entry_points) {
        items.push({
          path: ep,
          description: "Primary system entry point & runtime bootstrap",
          type: "entry",
        });
      }
    }

    if (activeRepo.components && activeRepo.components.length > 0) {
      for (const comp of activeRepo.components) {
        items.push({
          path: comp,
          description: `Top-level module in ${activeRepo.name}`,
          type: "component",
        });
      }
    }

    if (activeRepo.frameworks && activeRepo.frameworks.length > 0) {
      for (const fw of activeRepo.frameworks) {
        items.push({
          path: fw,
          description: `Detected architectural framework in ${activeRepo.name}`,
          type: "framework",
        });
      }
    }

    // Fallback if no specific components scanned yet
    if (items.length === 0) {
      items.push(
        {
          path: activeRepo.local_path || activeRepo.name,
          description: `Root directory (${activeRepo.file_count || 0} indexed files, ${activeRepo.languages?.join(", ") || "Code"})`,
          type: "module",
        }
      );
    }

    return items;
  }, [activeRepo]);

  const filteredFolders = subfolders.filter(
    (f) => f.path.toLowerCase().includes(searchRepo.toLowerCase()) || f.description.toLowerCase().includes(searchRepo.toLowerCase())
  );

  const samplePrompts = [
    `Find where core entry points are located in ${activeRepo.name}`,
    `Explain the architectural layers and components of ${activeRepo.name}`,
    `How are services and configuration handled in ${activeRepo.name}?`,
  ];

  const handleExecuteContextPull = async () => {
    if (!taskPrompt.trim()) return;
    if (loading || cooldown > 0) {
      toast.warning("Please wait a moment before triggering another request.");
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    const toastId = toast.loading(
      "Synthesizing context package via LM Studio...",
      "Context Generation Started"
    );

    try {
      const res = await getAgentContext({
        task_prompt: taskPrompt,
        repository_path: activeRepo.local_path,
        max_tokens: maxTokens,
        include_structural_graph: true,
      });
      setAgentResponse(res);
      setCooldown(3); // 3-second cooldown to avoid accidental spam
      toast.update(toastId, {
        type: "success",
        title: "Context Package Ready",
        message: `Assembled ${res.estimated_tokens.toLocaleString()} tokens in ${res.generation_time_ms}ms`,
      });
    } catch (err) {
      console.error("Context interception failed", err);
      const msg =
        err instanceof Error
          ? err.message
          : "Context generation failed. Ensure your LM Studio / Ollama provider is running on port 1234 or 11434.";
      setErrorMessage(msg);
      setCooldown(2);
      toast.update(toastId, {
        type: "error",
        title: "Synthesis Failed",
        message: msg,
      });
    } finally {
      setLoading(false);
    }
  };

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

  const currentTokens = agentResponse?.estimated_tokens || 0;
  const tokenPercentage = Math.min(100, Math.round((currentTokens / maxTokens) * 100));

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground">
      <TopBar title="RE:Track | Context Studio" />

      {/* Main Unified Linear / Raycast Studio Deck */}
      <main className="flex-1 flex overflow-hidden p-6 gap-6 max-w-[1700px] w-full mx-auto">
        {/* Left Interactive Builder & Interceptor Workbench */}
        <div className="flex-1 flex flex-col h-full bg-[#0a0a0a] rounded-xl border border-[#262626] overflow-hidden shadow-2xl">
          {/* Top Studio Control Bar */}
          <div className="h-14 px-6 border-b border-[#262626] bg-[#0f0f0f] flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Repository Selector Dropdown */}
              <div ref={dropdownRef} className="relative">
                <button
                  onClick={() => setRepoDropdownOpen(!repoDropdownOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black border border-[#262626] hover:border-[#404040] hover:bg-[#141414] text-xs font-mono text-foreground transition-all cursor-pointer shadow-xs"
                >
                  <GitBranch className="w-3.5 h-3.5 text-foreground" />
                  <span className="font-semibold text-white">{activeRepo.name}</span>
                  <ChevronDown className={`w-3.5 h-3.5 text-neutral-400 transition-transform ${repoDropdownOpen ? "rotate-180" : ""}`} />
                </button>

                {repoDropdownOpen && (
                  <div className="absolute left-0 top-full mt-2 w-72 bg-black border border-[#2e2e2e] rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden">
                    <div className="px-3.5 py-1.5 text-[10px] font-mono text-neutral-500 uppercase tracking-wider border-b border-[#222222]">
                      Switch Active Workspace
                    </div>
                    <div className="max-h-60 overflow-y-auto py-1">
                      {repositories.map((repo) => {
                        const isCurrent = repo.id === activeRepo.id || repo.local_path === activeRepo.local_path;
                        return (
                          <button
                            key={repo.id}
                            onClick={() => {
                              setSearchParams({ repo: repo.id });
                              setRepoDropdownOpen(false);
                            }}
                            className={`w-full flex items-center justify-between px-3.5 py-2 text-xs font-mono text-left transition-colors ${
                              isCurrent
                                ? "bg-[#1f1f1f] text-white"
                                : "text-neutral-300 hover:text-white hover:bg-[#141414]"
                            }`}
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-bold truncate flex items-center gap-2">
                                <span>{repo.name}</span>
                              </div>
                              <span className="text-[10px] text-neutral-500 truncate block">
                                {repo.local_path}
                              </span>
                            </div>
                            {isCurrent && <Check className="w-3.5 h-3.5 text-white shrink-0" />}
                          </button>
                        );
                      })}
                    </div>
                    <div className="p-1.5 border-t border-[#222222] bg-[#0c0c0c]">
                      <button
                        onClick={() => {
                          setRepoDropdownOpen(false);
                          navigate("/repositories");
                        }}
                        className="w-full py-1.5 px-3 rounded-lg text-xs font-mono text-neutral-400 hover:text-white hover:bg-[#1c1c1c] transition-colors flex items-center justify-center gap-1.5"
                      >
                        <FolderGit2 className="w-3.5 h-3.5" />
                        <span>Manage Workspaces</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center bg-black p-1 rounded-lg border border-[#262626]">
                <button
                  onClick={() => setActiveTab("workspace")}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    activeTab === "workspace"
                      ? "bg-[#262626] text-white"
                      : "text-muted-foreground hover:text-white"
                  }`}
                >
                  Prompt Workbench
                </button>
                <button
                  onClick={() => setActiveTab("tree")}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    activeTab === "tree"
                      ? "bg-[#262626] text-white"
                      : "text-muted-foreground hover:text-white"
                  }`}
                >
                  Repository AST Map
                </button>
              </div>
            </div>

            {/* Token Budget Quick Controls */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                <span>Budget:</span>
                <div className="flex items-center gap-1">
                  {[4000, 8000, 16000, 32000].map((b) => (
                    <button
                      key={b}
                      onClick={() => setMaxTokens(b)}
                      className={`px-2.5 py-1 rounded text-xs font-mono border transition-colors ${
                        maxTokens === b
                          ? "bg-white text-black border-white font-semibold"
                          : "bg-black text-muted-foreground border-[#262626] hover:text-white hover:bg-[#1a1a1a]"
                      }`}
                    >
                      {b >= 1000 ? `${b / 1000}k` : b}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Workbench Body */}
          {activeTab === "workspace" ? (
            <div className="flex-1 flex flex-col p-6 gap-5 overflow-y-auto">
              {/* Natural Language Prompt Area */}
              <div className="flex-1 flex flex-col gap-2.5 min-h-[220px]">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
                    Agent Instruction / Task Query
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">
                    Markdown Context Synthesis
                  </span>
                </div>

                <div className="flex-1 relative rounded-xl border border-[#262626] bg-black focus-within:border-white transition-colors overflow-hidden flex flex-col">
                  <textarea
                    value={taskPrompt}
                    onChange={(e) => setTaskPrompt(e.target.value)}
                    placeholder="Describe the feature, bug, or module to synthesize structured agent context for..."
                    className="w-full flex-1 p-5 text-sm font-sans bg-transparent text-foreground placeholder:text-muted-foreground/50 resize-none outline-none leading-relaxed"
                  />

                  {/* Token Meter bar in footer of box */}
                  <div className="p-3 bg-[#0d0d0d] border-t border-[#1f1f1f] flex items-center justify-between text-xs font-mono text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Gauge className="w-4 h-4 text-foreground" />
                      <span>
                        Est. Tokens:{" "}
                        <strong className="text-white">
                          {currentTokens.toLocaleString()}
                        </strong>{" "}
                        / {maxTokens.toLocaleString()}
                      </span>
                    </div>

                    <div className="w-48 h-2 bg-[#1a1a1a] rounded-full overflow-hidden border border-[#262626]">
                      <div
                        className="h-full bg-white transition-all duration-300"
                        style={{ width: `${tokenPercentage}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Sample Scenarios Deck */}
              <div className="space-y-2">
                <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                  Preset Scenarios
                </span>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {samplePrompts.map((p, i) => (
                    <button
                      key={i}
                      onClick={() => setTaskPrompt(p)}
                      className="p-3.5 rounded-lg text-left bg-black border border-[#262626] text-xs text-muted-foreground hover:text-white hover:bg-[#141414] hover:border-[#383838] transition-all line-clamp-2 font-sans leading-normal shadow-sm"
                    >
                      "{p}"
                    </button>
                  ))}
                </div>
              </div>

              {/* Error notice if synthesis fails */}
              {errorMessage && (
                <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-500/30 flex items-start gap-2.5 text-xs font-mono text-red-300">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-semibold text-white mb-0.5">Synthesis Error</p>
                    <p>{errorMessage}</p>
                  </div>
                </div>
              )}

              {/* Big Action Synthesize Bar */}
              <Button
                onClick={handleExecuteContextPull}
                disabled={loading || cooldown > 0 || !taskPrompt.trim()}
                className="w-full h-13 text-sm font-bold uppercase tracking-wider font-mono gap-3 bg-white text-black hover:bg-neutral-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg rounded-xl"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                    <span>Synthesizing Context Package...</span>
                  </>
                ) : cooldown > 0 ? (
                  <>
                    <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full" />
                    <span>Ready in {cooldown}s...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-black" />
                    <span>Synthesize & Assemble Context Package</span>
                  </>
                )}
              </Button>
            </div>
          ) : (
            /* AST Outline Tree Tab */
            <div className="flex-1 flex flex-col p-6 gap-4 overflow-hidden">
              {/* Sub-tab header: List / Graph */}
              <div className="flex items-center gap-3">
                <div className="flex items-center bg-black p-1 rounded-lg border border-[#262626]">
                  <button
                    onClick={() => setAstView("list")}
                    className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      astView === "list" ? "bg-[#262626] text-white" : "text-muted-foreground hover:text-white"
                    }`}
                  >
                    <List className="w-3.5 h-3.5" />
                    Directory List
                  </button>
                  <button
                    onClick={() => setAstView("graph")}
                    className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      astView === "graph" ? "bg-[#262626] text-white" : "text-muted-foreground hover:text-white"
                    }`}
                  >
                    <Network className="w-3.5 h-3.5" />
                    Call Graph
                  </button>
                </div>
                {astView === "list" && (
                  <>
                    <div className="relative flex-1">
                      <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        type="text"
                        placeholder="Filter AST submodules and files..."
                        value={searchRepo}
                        onChange={(e) => setSearchRepo(e.target.value)}
                        className="h-10 pl-10 text-xs font-mono bg-black border-[#262626] rounded-lg"
                      />
                    </div>
                    <Badge variant="outline" className="text-xs font-mono px-3 py-1.5 border-[#262626] bg-black text-neutral-300">
                      {filteredFolders.length} AST & Directory Entries
                    </Badge>
                  </>
                )}
                {astView === "graph" && (
                  <Badge variant="outline" className="text-xs font-mono px-3 py-1.5 border-[#262626] bg-black text-neutral-300">
                    {(activeRepo.call_graph_nodes ?? []).length} nodes · {(activeRepo.call_graph_edges ?? []).length} edges
                  </Badge>
                )}
              </div>

              {astView === "list" ? (
                <ScrollArea className="flex-1 rounded-xl border border-[#262626] bg-black p-3">
                  <div className="space-y-1.5">
                    {filteredFolders.map((sub) => {
                      const isSelected = selectedSubfolder === sub.path;
                      const Icon =
                        sub.type === "entry"
                          ? Code2
                          : sub.type === "framework"
                          ? Layers
                          : sub.type === "component"
                          ? Box
                          : Folder;

                      return (
                        <button
                          key={sub.path}
                          onClick={() => setSelectedSubfolder(sub.path)}
                          className={`w-full text-left p-3.5 rounded-lg transition-colors text-xs font-mono border ${
                            isSelected
                              ? "bg-[#1f1f1f] border-[#404040] text-white shadow-xs"
                              : "border-transparent text-muted-foreground hover:text-white hover:bg-[#141414]"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2.5 font-medium truncate mb-1">
                            <div className="flex items-center gap-2.5 min-w-0">
                              <Icon className={`w-4 h-4 shrink-0 ${isSelected ? "text-white" : "text-muted-foreground"}`} />
                              <span className="truncate font-semibold text-sm">{sub.path}</span>
                            </div>
                            <Badge
                              variant="outline"
                              className="text-[10px] uppercase font-mono px-2 py-0.5 border-[#333333] text-neutral-400 bg-black shrink-0"
                            >
                              {sub.type}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground font-sans line-clamp-1 pl-6.5">
                            {sub.description}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </ScrollArea>
              ) : (
                <div className="flex-1 min-h-0">
                  <CallGraphView
                    nodes={activeRepo.call_graph_nodes ?? []}
                    edges={activeRepo.call_graph_edges ?? []}
                    width={680}
                    height={480}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Structured Delivery Deck */}
        <div className="w-[580px] h-full flex flex-col bg-[#0a0a0a] rounded-xl border border-[#262626] overflow-hidden shadow-2xl shrink-0">
          {/* Output Deck Header */}
          <div className="h-14 px-5 border-b border-[#262626] bg-[#0f0f0f] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-black border border-[#262626] flex items-center justify-center text-white font-bold text-xs">
                <FileText className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white tracking-tight">
                  Synthesized Package
                </h3>
                <span className="text-xs font-mono text-muted-foreground">
                  {agentResponse?.generation_time_ms ? `${agentResponse.generation_time_ms}ms generation` : "Ready for Agent"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                disabled={!agentResponse}
                className="h-8 px-3 text-xs gap-1.5 font-medium border-[#262626] bg-black text-foreground hover:bg-[#1f1f1f] rounded-lg"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                disabled={!agentResponse}
                className="h-8 px-3 text-xs gap-1.5 font-medium border-[#262626] bg-black text-foreground hover:bg-[#1f1f1f] rounded-lg"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Save</span>
              </Button>
            </div>
          </div>

          {/* Markdown Preview Body */}
          <ScrollArea className="flex-1 p-5 bg-black">
            {loading ? (
              <div className="h-full min-h-[320px] flex flex-col items-center justify-center gap-3 text-center">
                <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <p className="text-xs font-mono text-muted-foreground">
                  Synthesizing and indexing AST graph...
                </p>
              </div>
            ) : agentResponse?.context_markdown ? (
              <pre className="text-xs font-mono text-neutral-300 whitespace-pre-wrap break-words leading-relaxed select-text selection:bg-neutral-800 font-normal">
                {agentResponse.context_markdown}
              </pre>
            ) : (
              <div className="h-full min-h-[320px] flex flex-col items-center justify-center gap-3 text-center p-8">
                <div className="w-12 h-12 rounded-xl bg-[#141414] border border-[#262626] flex items-center justify-center mb-1">
                  <Code2 className="w-6 h-6 text-muted-foreground" />
                </div>
                <h4 className="text-sm font-semibold text-white">No Package Generated</h4>
                <p className="text-xs text-muted-foreground max-w-xs leading-normal">
                  Write instructions in the Prompt Workbench on the left and click synthesize to assemble structured context.
                </p>
              </div>
            )}
          </ScrollArea>
        </div>
      </main>
    </div>
  );
}
