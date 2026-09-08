import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { useRepositoryStore } from "@/stores/repository-store";
import { useLayout } from "@/components/layout/LayoutContext";
import { CallGraphView } from "@/components/repositories/CallGraphView";
import { ReindexModal } from "@/components/repositories/ReindexModal";
import { RepositoryCardSkeleton } from "@/components/ui/skeleton-loaders";
import { ProviderAlertBanner } from "@/components/shared/ProviderAlertBanner";
import { WorkspaceHeader } from "@/components/workspace/WorkspaceHeader";
import { LifecycleStepper } from "@/components/workspace/LifecycleStepper";
import { ManifestEvidenceTable } from "@/components/workspace/ManifestEvidenceTable";
import type { CallGraphNode, CallGraphEdge } from "@/types/repository";
import {
  FolderGit2,
  RefreshCw,
  Search,
  X,
  FileCode,
  Network,
  ShieldCheck,
  Brain,
  ArrowRight,
  CheckCircle2,
  FolderOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type WorkspaceTab = "overview" | "lifecycle" | "ast" | "manifest";

export default function Workspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    repositories,
    selectedId,
    selected,
    select,
    fetchRepositories,
    scanRepo,
    scanning,
    loading,
    searchQuery,
    setSearchQuery,
  } = useRepositoryStore();

  const { openNewIndexModal } = useLayout();
  const [showReindexModal, setShowReindexModal] = useState(false);
  const [selectedAstNode, setSelectedAstNode] = useState<CallGraphNode | null>(null);

  // Active tab from URL query param (?tab=...)
  const activeTab = (searchParams.get("tab") as WorkspaceTab) || "overview";

  const setTab = (tab: WorkspaceTab) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", tab);
    setSearchParams(next);
  };

  // Synchronize URL ?repo=<id> with store.selectedId
  useEffect(() => {
    const urlRepoId = searchParams.get("repo");
    if (urlRepoId && urlRepoId !== selectedId) {
      const match = repositories.find((r) => r.id === urlRepoId);
      if (match) {
        select(urlRepoId);
      }
    } else if (!urlRepoId && selectedId) {
      const next = new URLSearchParams(searchParams);
      next.set("repo", selectedId);
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, selectedId, repositories, select, setSearchParams]);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  // Derived CallGraph nodes & edges for AST Tab
  const callGraphNodes: CallGraphNode[] = useMemo(() => {
    if (!selected) return [];
    if (selected.call_graph_nodes && Array.isArray(selected.call_graph_nodes)) {
      return selected.call_graph_nodes;
    }
    if (selected.metadata?.call_graph_nodes && Array.isArray(selected.metadata.call_graph_nodes)) {
      return selected.metadata.call_graph_nodes as CallGraphNode[];
    }
    return [];
  }, [selected]);

  const callGraphEdges: CallGraphEdge[] = useMemo(() => {
    if (!selected) return [];
    if (selected.call_graph_edges && Array.isArray(selected.call_graph_edges)) {
      return selected.call_graph_edges;
    }
    if (selected.metadata?.call_graph_edges && Array.isArray(selected.metadata.call_graph_edges)) {
      return selected.metadata.call_graph_edges as CallGraphEdge[];
    }
    return [];
  }, [selected]);

  // Storage metric counts
  const fileCount = selected?.file_count ?? (selected?.metadata?.files_indexed as number) ?? 0;
  const symbolCount = callGraphNodes.length || (selected?.metadata?.symbols_count as number) || 0;
  const vectorCount = (selected?.metadata?.vector_records as number) ?? (selected?.metadata?.vectors_count as number) ?? 0;
  const graphCount = (selected?.metadata?.graph_entities as number) ?? callGraphEdges.length;
  const semanticCount = (selected?.metadata?.semantic_memories_count as number) ?? 0;

  // Filtered repositories for the no-active-repo catalog
  const filteredRepos = repositories.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.local_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelectRepo = (id: string) => {
    select(id);
    const next = new URLSearchParams(searchParams);
    next.set("repo", id);
    setSearchParams(next);
  };

  const handleClearSelection = () => {
    select(null);
    const next = new URLSearchParams(searchParams);
    next.delete("repo");
    setSearchParams(next);
  };

  const handleTriggerScan = async () => {
    if (!selected) return;
    try {
      await scanRepo(selected.id);
    } catch {
      // Handled in store
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased">
      <TopBar
        title="RE:Track | Repository Workspace"
        subtitle={selected ? `Codebase: ${selected.name}` : "Workspace & Storage Hub"}
      />

      {/* Main Container */}
      <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {!selected ? (
          /* ============================================================ */
          /* NO ACTIVE REPOSITORY STATE: Clean Selection & Catalog Deck */
          /* ============================================================ */
          <div className="flex-1 min-h-0 flex flex-col p-4 sm:p-6 lg:p-8 max-w-6xl w-full mx-auto overflow-y-auto">
            <div className="mb-4">
              <ProviderAlertBanner />
            </div>

            {/* Header Banner */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[#1e1e1e]">
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
                  <FolderGit2 className="w-6 h-6 text-white" />
                  Select Active Workspace
                </h1>
                <p className="text-xs text-neutral-400 mt-1">
                  Choose an indexed codebase to explore its deterministic AST topology, manifest deltas, and lifecycle.
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Search Bar */}
                <div className="relative w-56 sm:w-64">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-500" />
                  <Input
                    type="text"
                    placeholder="Filter workspaces..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="h-8 pl-8 pr-7 text-xs font-mono bg-[#0a0a0a] border-[#262626] rounded-md text-neutral-200 placeholder:text-neutral-500 focus-visible:ring-1 focus-visible:ring-neutral-400"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      aria-label="Clear search filter"
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white p-0.5 rounded cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>

                <Button
                  size="sm"
                  onClick={() => openNewIndexModal?.()}
                  className="h-8 px-3 text-xs font-mono font-medium gap-1.5 bg-white text-black hover:bg-neutral-200 cursor-pointer shadow-sm"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span>Index Codebase</span>
                </Button>
              </div>
            </div>

            {/* Repository Grid */}
            <div className="mt-6 flex-1">
              {loading && repositories.length === 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <RepositoryCardSkeleton />
                  <RepositoryCardSkeleton />
                  <RepositoryCardSkeleton />
                </div>
              ) : filteredRepos.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 text-center bg-[#0a0a0a] rounded-xl border border-[#1e1e1e]">
                  <div className="w-12 h-12 rounded-xl bg-[#141414] border border-[#262626] flex items-center justify-center mb-3 text-neutral-400">
                    <FolderGit2 className="w-6 h-6 text-neutral-300" />
                  </div>
                  <h3 className="text-sm font-semibold text-white tracking-tight mb-1">
                    {searchQuery ? "No matching repositories" : "No repositories indexed yet"}
                  </h3>
                  <p className="text-xs text-neutral-500 max-w-md leading-relaxed mb-4">
                    {searchQuery
                      ? `No indexed repositories match "${searchQuery}". Clear the search query to see all workspaces.`
                      : "Index a local directory to generate deterministic AST topology, manifest tracking, and semantic context."}
                  </p>
                  {searchQuery ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSearchQuery("")}
                      className="h-8 px-3.5 text-xs font-mono border-[#262626] hover:bg-[#1f1f1f] text-neutral-200"
                    >
                      Clear search filter
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => openNewIndexModal?.()}
                      className="h-8 px-4 text-xs font-mono font-medium bg-white text-black hover:bg-neutral-200"
                    >
                      Index First Codebase
                    </Button>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredRepos.map((repo) => (
                    <div
                      key={repo.id}
                      onClick={() => handleSelectRepo(repo.id)}
                      className={cn(
                        "p-4 rounded-xl border transition-all cursor-pointer group flex flex-col justify-between",
                        "bg-[#0a0a0a] border-[#1e1e1e] hover:border-neutral-700 hover:bg-[#111111]"
                      )}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h3 className="text-sm font-semibold text-white group-hover:text-white transition-colors truncate">
                            {repo.name}
                          </h3>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[10px] font-mono capitalize",
                              repo.status === "indexed"
                                ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/60"
                                : "bg-neutral-900 text-neutral-400 border-neutral-800"
                            )}
                          >
                            {repo.status}
                          </Badge>
                        </div>
                        <p className="text-[11px] font-mono text-neutral-500 truncate mb-3">
                          {repo.local_path}
                        </p>
                        <div className="flex flex-wrap gap-1.5 mb-4">
                          {repo.languages && repo.languages.length > 0 ? (
                            repo.languages.slice(0, 3).map((lang) => (
                              <span
                                key={lang}
                                className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#141414] border border-[#222222] text-neutral-300"
                              >
                                {lang}
                              </span>
                            ))
                          ) : (
                            <span className="text-[10px] text-neutral-600 font-mono">No languages detected</span>
                          )}
                        </div>
                      </div>

                      <div className="pt-3 border-t border-[#1a1a1a] flex items-center justify-between text-[11px] font-mono text-neutral-400">
                        <span>{repo.file_count || 0} files</span>
                        <span className="text-neutral-300 group-hover:text-white flex items-center gap-1 font-sans font-medium text-xs">
                          Open Workspace <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* ============================================================ */
          /* ACTIVE REPOSITORY WORKSPACE: Scoped 4-Subview Architecture   */
          /* ============================================================ */
          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {/* Pinned Repository Header */}
            <WorkspaceHeader
              repository={selected}
              scanning={scanning}
              onTriggerScan={handleTriggerScan}
              onOpenReindex={() => setShowReindexModal(true)}
              onClearSelection={handleClearSelection}
            />

            {/* Sub-Navigation Tabs */}
            <div className="px-4 sm:px-6 border-b border-[#1e1e1e] bg-[#090909] shrink-0">
              <div className="flex items-center gap-1 overflow-x-auto py-1.5 scrollbar-none">
                <button
                  onClick={() => setTab("overview")}
                  className={cn(
                    "px-3 py-1.5 rounded-md text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
                    activeTab === "overview"
                      ? "bg-white text-black font-semibold shadow-sm"
                      : "text-neutral-400 hover:text-white hover:bg-[#141414]"
                  )}
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Overview</span>
                </button>

                <button
                  onClick={() => setTab("lifecycle")}
                  className={cn(
                    "px-3 py-1.5 rounded-md text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
                    activeTab === "lifecycle"
                      ? "bg-white text-black font-semibold shadow-sm"
                      : "text-neutral-400 hover:text-white hover:bg-[#141414]"
                  )}
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Lifecycle</span>
                </button>

                <button
                  onClick={() => setTab("ast")}
                  className={cn(
                    "px-3 py-1.5 rounded-md text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
                    activeTab === "ast"
                      ? "bg-white text-black font-semibold shadow-sm"
                      : "text-neutral-400 hover:text-white hover:bg-[#141414]"
                  )}
                >
                  <Network className="w-3.5 h-3.5" />
                  <span>AST</span>
                  {callGraphNodes.length > 0 && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-neutral-800 text-neutral-300 font-mono">
                      {callGraphNodes.length}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setTab("manifest")}
                  className={cn(
                    "px-3 py-1.5 rounded-md text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
                    activeTab === "manifest"
                      ? "bg-white text-black font-semibold shadow-sm"
                      : "text-neutral-400 hover:text-white hover:bg-[#141414]"
                  )}
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>Manifest &amp; Evidence</span>
                </button>
              </div>
            </div>

            {/* Subview Content */}
            <div className="flex-1 min-h-0 overflow-y-auto">
              {/* SUBVIEW 1: OVERVIEW */}
              {activeTab === "overview" && (
                <div className="p-4 sm:p-6 max-w-6xl w-full mx-auto space-y-6">
                  {/* 5 Distinct Storage-Derived Metric Cards with Truth States */}
                  <div>
                    <h3 className="text-xs font-mono uppercase tracking-wider text-neutral-400 mb-3">
                      Storage-Derived Quantities &amp; Truth States
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                      {/* 1. Tracked Files */}
                      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#1e1e1e]">
                        <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
                          <span>Tracked Files</span>
                          <span
                            className={cn(
                              "px-1.5 py-0.2 text-[9px] rounded font-mono uppercase",
                              fileCount > 0 ? "bg-emerald-950/60 text-emerald-400" : "bg-neutral-900 text-neutral-500"
                            )}
                          >
                            {fileCount > 0 ? "Loaded" : "Empty"}
                          </span>
                        </div>
                        <div className="text-xl font-bold font-mono text-white">{fileCount}</div>
                        <div className="text-[10px] text-neutral-400 mt-1">Local Filesystem</div>
                      </div>

                      {/* 2. AST Symbols */}
                      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#1e1e1e]">
                        <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
                          <span>AST Symbols</span>
                          <span
                            className={cn(
                              "px-1.5 py-0.2 text-[9px] rounded font-mono uppercase",
                              symbolCount > 0
                                ? "bg-emerald-950/60 text-emerald-400"
                                : selected.call_graph_status === "analyzing"
                                ? "bg-amber-950/60 text-amber-400"
                                : selected.call_graph_status === "failed"
                                ? "bg-red-950/60 text-red-400"
                                : "bg-neutral-900 text-neutral-500"
                            )}
                          >
                            {symbolCount > 0
                              ? "Loaded"
                              : selected.call_graph_status === "analyzing"
                              ? "Analyzing"
                              : selected.call_graph_status === "failed"
                              ? "Failed"
                              : "Not Analyzed"}
                          </span>
                        </div>
                        <div className="text-xl font-bold font-mono text-white">{symbolCount}</div>
                        <div className="text-[10px] text-neutral-400 mt-1">Deterministic AST</div>
                      </div>

                      {/* 3. Vector Projections */}
                      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#1e1e1e]">
                        <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
                          <span>Vector Records</span>
                          <span
                            className={cn(
                              "px-1.5 py-0.2 text-[9px] rounded font-mono uppercase",
                              vectorCount > 0 ? "bg-emerald-950/60 text-emerald-400" : "bg-neutral-900 text-neutral-500"
                            )}
                          >
                            {vectorCount > 0 ? "Loaded" : "Not Projected"}
                          </span>
                        </div>
                        <div className="text-xl font-bold font-mono text-white">{vectorCount}</div>
                        <div className="text-[10px] text-neutral-400 mt-1">LanceDB Vectors</div>
                      </div>

                      {/* 4. Graph Entities */}
                      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#1e1e1e]">
                        <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
                          <span>Graph Entities</span>
                          <span
                            className={cn(
                              "px-1.5 py-0.2 text-[9px] rounded font-mono uppercase",
                              graphCount > 0 ? "bg-emerald-950/60 text-emerald-400" : "bg-neutral-900 text-neutral-500"
                            )}
                          >
                            {graphCount > 0 ? "Loaded" : "Not Projected"}
                          </span>
                        </div>
                        <div className="text-xl font-bold font-mono text-white">{graphCount}</div>
                        <div className="text-[10px] text-neutral-400 mt-1">Kùzu Graph Engine</div>
                      </div>

                      {/* 5. Semantic Memories */}
                      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#1e1e1e]">
                        <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
                          <span>Derived Records</span>
                          <span
                            className={cn(
                              "px-1.5 py-0.2 text-[9px] rounded font-mono uppercase",
                              semanticCount > 0 ? "bg-emerald-950/60 text-emerald-400" : "bg-neutral-900 text-neutral-500"
                            )}
                          >
                            {semanticCount > 0 ? "Loaded" : "Not Generated"}
                          </span>
                        </div>
                        <div className="text-xl font-bold font-mono text-white">{semanticCount}</div>
                        <div className="text-[10px] text-neutral-400 mt-1">Cognee Semantic Memory</div>
                      </div>
                    </div>
                  </div>

                  {/* Storage Subsystem Truth Architecture Card */}
                  <div className="p-5 rounded-xl bg-[#0a0a0a] border border-[#1e1e1e]">
                    <div className="flex items-center gap-2 mb-3">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <h4 className="text-sm font-semibold text-white tracking-tight">
                        Truth Boundary &amp; Storage Subsystems
                      </h4>
                    </div>
                    <p className="text-xs text-neutral-400 mb-4 leading-relaxed">
                      RE:Track enforces a strict boundary between authoritative repository truth and derived AI projections. The backend is the sole authority; derived storage is never treated as source truth.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Authoritative Column */}
                      <div className="p-4 rounded-lg bg-[#0d0d0d] border border-emerald-900/40">
                        <div className="flex items-center gap-2 mb-2 text-emerald-400 text-xs font-mono font-bold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          AUTHORITATIVE STORAGE (TIER 1 &amp; TIER 2)
                        </div>
                        <p className="text-[11px] text-neutral-400 mb-3">
                          Deterministic data directly verified against local source files. Always takes precedence during arbitration.
                        </p>
                        <div className="space-y-2 text-xs font-mono">
                          <div className="flex justify-between items-center py-1 border-b border-[#1f1f1f]">
                            <span className="text-neutral-300">Filesystem &amp; Manifest</span>
                            <span className="text-neutral-400">{fileCount} files tracked</span>
                          </div>
                          <div className="flex justify-between items-center py-1">
                            <span className="text-neutral-300">Tree-sitter AST Topology</span>
                            <span className="text-neutral-400">{symbolCount} syntax nodes</span>
                          </div>
                        </div>
                      </div>

                      {/* Derived Column */}
                      <div className="p-4 rounded-lg bg-[#0d0d0d] border border-amber-900/40">
                        <div className="flex items-center gap-2 mb-2 text-amber-400 text-xs font-mono font-bold">
                          <Brain className="w-3.5 h-3.5" />
                          DERIVED STORAGE (TIER 3 &amp; TIER 4)
                        </div>
                        <p className="text-[11px] text-neutral-400 mb-3">
                          Projections and AI-derived records. Subject to strict provenance invalidation when source files change.
                        </p>
                        <div className="space-y-2 text-xs font-mono">
                          <div className="flex justify-between items-center py-1 border-b border-[#1f1f1f]">
                            <span className="text-neutral-300">LanceDB Vector Index</span>
                            <span className="text-neutral-400">{vectorCount} embeddings</span>
                          </div>
                          <div className="flex justify-between items-center py-1 border-b border-[#1f1f1f]">
                            <span className="text-neutral-300">Kùzu Knowledge Graph</span>
                            <span className="text-neutral-400">{graphCount} entities/edges</span>
                          </div>
                          <div className="flex justify-between items-center py-1">
                            <span className="text-neutral-300">Cognee Semantic Records</span>
                            <span className="text-neutral-400">{semanticCount} observations</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* SUBVIEW 2: LIFECYCLE PIPELINE */}
              {activeTab === "lifecycle" && (
                <LifecycleStepper
                  repository={selected}
                  fileCount={fileCount}
                  symbolCount={symbolCount}
                  scanning={scanning}
                  onTriggerScan={handleTriggerScan}
                  onOpenReindex={() => setShowReindexModal(true)}
                />
              )}

              {/* SUBVIEW 3: AST & TOPOLOGY */}
              {activeTab === "ast" && (
                <div className="h-full flex flex-col">
                  <CallGraphView
                    nodes={callGraphNodes}
                    edges={callGraphEdges}
                    selectedNodeId={selectedAstNode?.id}
                    onSelectNode={setSelectedAstNode}
                    status={selected.call_graph_status}
                    errorMessage={selected.call_graph_error}
                    onTriggerAnalyze={() => setShowReindexModal(true)}
                  />
                </div>
              )}

              {/* SUBVIEW 4: MANIFEST & EVIDENCE */}
              {activeTab === "manifest" && (
                <ManifestEvidenceTable
                  repository={selected}
                  callGraphNodes={callGraphNodes}
                  fileCount={fileCount}
                />
              )}
            </div>
          </div>
        )}
      </main>

      {/* Reindex Modal */}
      {selected && (
        <ReindexModal
          repoId={selected.id}
          open={showReindexModal}
          onOpenChange={setShowReindexModal}
        />
      )}
    </div>
  );
}
