import { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { useRepositoryStore } from "@/stores/repository-store";
import {
  ArrowLeft,
  Layers,
  Terminal,
  Sparkles,
  FolderGit2,
  Folder,
  FileCode,
  Network,
  ListTree,
  Zap,
  ChevronRight,
  ChevronDown,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CallGraphView } from "@/components/repositories/CallGraphView";
import { QuickContextModal } from "@/components/repositories/QuickContextModal";
import type { CallGraphNode, CallGraphEdge } from "@/types/repository";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";

export default function KnowledgeExplorer() {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const { repositories, fetchRepositories } = useRepositoryStore();

  const [activeTab, setActiveTab] = useState<"graph" | "tree" | "components">("graph");
  const [selectedNode, setSelectedNode] = useState<CallGraphNode | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    backend: true,
    src: true,
    docs: true,
  });
  const [showQuickContext, setShowQuickContext] = useState(false);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  const repo = repositories.find((r) => r.id === repoId);

  // Authoritative call graph nodes and edges from repository state
  const callGraphNodes: CallGraphNode[] = useMemo(() => {
    if (repo?.call_graph_nodes && Array.isArray(repo.call_graph_nodes)) {
      return repo.call_graph_nodes;
    }
    if (repo?.metadata?.call_graph_nodes && Array.isArray(repo.metadata.call_graph_nodes)) {
      return repo.metadata.call_graph_nodes as CallGraphNode[];
    }
    return [];
  }, [repo]);

  const callGraphEdges: CallGraphEdge[] = useMemo(() => {
    if (repo?.call_graph_edges && Array.isArray(repo.call_graph_edges)) {
      return repo.call_graph_edges;
    }
    if (repo?.metadata?.call_graph_edges && Array.isArray(repo.metadata.call_graph_edges)) {
      return repo.metadata.call_graph_edges as CallGraphEdge[];
    }
    return [];
  }, [repo]);

  const graphStatus = useMemo(() => {
    if (repo?.call_graph_status) return repo.call_graph_status;
    if (repo?.metadata?.call_graph_status) return repo.metadata.call_graph_status as string;
    if (callGraphEdges.length > 0) return "analyzed";
    if (callGraphNodes.length > 0) return "zero_edges";
    if (repo?.status === "indexing" || repo?.status === "scanning") return "analyzing";
    return "not_analyzed";
  }, [repo, callGraphNodes, callGraphEdges]);

  const toggleFolder = (f: string) => {
    setExpandedFolders((prev) => ({ ...prev, [f]: !prev[f] }));
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased">
      <TopBar title={`RE:Track | Knowledge Explorer: ${repo ? repo.name : repoId}`}>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/")}
            className="h-8 px-2.5 text-xs font-mono gap-1.5 border-[#262626] bg-[#0a0a0a] text-neutral-300 hover:text-white hover:bg-[#1f1f1f] cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Workspaces</span>
          </Button>

          {repo && (
            <Button
              size="sm"
              onClick={() => setShowQuickContext(true)}
              className="h-8 px-3 text-xs font-mono font-semibold bg-[#1a1a1a] border border-[#333] text-white hover:bg-white hover:text-black gap-1.5 transition-all cursor-pointer"
            >
              <Zap className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
              <span>Quick Context</span>
            </Button>
          )}

          {repo && (
            <Button
              size="sm"
              onClick={() => navigate(`/studio?repo=${repo.id}`)}
              className="h-8 px-3.5 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 gap-1.5 shadow-sm cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Context Studio</span>
            </Button>
          )}
        </div>
      </TopBar>

      <main className="flex-1 min-h-0 flex flex-col overflow-hidden p-4 sm:p-6 max-w-[1800px] w-full mx-auto gap-5">
        {repo ? (
          <>
            {/* Repository Info Card */}
            <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 shrink-0 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 shadow-xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-black border border-[#2a2a2a] flex items-center justify-center text-white shrink-0">
                  <FolderGit2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h1 className="text-lg font-bold text-white tracking-tight">
                      {repo.name}
                    </h1>
                    <Badge
                      variant="outline"
                      className="text-[10px] font-mono uppercase px-2 py-0.5 border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                    >
                      {repo.status || "Indexed"}
                    </Badge>
                  </div>
                  <p className="text-xs font-mono text-neutral-400 mt-0.5">
                    {repo.local_path}
                  </p>
                </div>
              </div>

              {/* Quick Telemetry Chips */}
              <div className="flex items-center gap-4 text-xs font-mono flex-wrap">
                <div className="bg-black border border-[#222] px-3 py-1.5 rounded-lg">
                  <span className="text-neutral-500 uppercase text-[10px] block">Files</span>
                  <span className="text-white font-bold">{repo.file_count || 0}</span>
                </div>
                <div className="bg-black border border-[#222] px-3 py-1.5 rounded-lg">
                  <span className="text-neutral-500 uppercase text-[10px] block">Architecture</span>
                  <span className="text-white font-bold capitalize">{repo.architecture || "Modular"}</span>
                </div>
                <div className="bg-black border border-[#222] px-3 py-1.5 rounded-lg">
                  <span className="text-neutral-500 uppercase text-[10px] block">AST Topology</span>
                  <span className="text-emerald-400 font-bold">{callGraphNodes.length} nodes · {callGraphEdges.length} edges</span>
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center justify-between border-b border-[#262626] pb-1 shrink-0">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setActiveTab("graph")}
                  className={cn(
                    "px-4 py-2 text-xs font-mono font-medium rounded-lg transition-all flex items-center gap-2 cursor-pointer",
                    activeTab === "graph"
                      ? "bg-white text-black font-semibold shadow-sm"
                      : "text-neutral-400 hover:text-white"
                  )}
                >
                  <Network className="w-3.5 h-3.5" />
                  <span>Call Graph &amp; AST Topology</span>
                  <span className="text-[10px] font-mono opacity-70">({callGraphNodes.length} nodes / {callGraphEdges.length} edges)</span>
                </button>

                <button
                  onClick={() => setActiveTab("tree")}
                  className={cn(
                    "px-4 py-2 text-xs font-mono font-medium rounded-lg transition-all flex items-center gap-2 cursor-pointer",
                    activeTab === "tree"
                      ? "bg-white text-black font-semibold shadow-sm"
                      : "text-neutral-400 hover:text-white"
                  )}
                >
                  <ListTree className="w-3.5 h-3.5" />
                  <span>Directory &amp; Module Map</span>
                </button>

                <button
                  onClick={() => setActiveTab("components")}
                  className={cn(
                    "px-4 py-2 text-xs font-mono font-medium rounded-lg transition-all flex items-center gap-2 cursor-pointer",
                    activeTab === "components"
                      ? "bg-white text-black font-semibold shadow-sm"
                      : "text-neutral-400 hover:text-white"
                  )}
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Key Components &amp; Entry Points</span>
                  {repo.components && (
                    <span className="text-[10px] font-mono opacity-70">({repo.components.length})</span>
                  )}
                </button>
              </div>
            </div>

            {/* Tab Contents Area */}
            <div className="flex-1 min-h-0 relative">
              <AnimatePresence mode="wait">
                {activeTab === "graph" && (
                  <motion.div
                    key="graph"
                    initial={{ opacity: 0, scale: 0.99 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.99 }}
                    transition={{ duration: 0.2 }}
                    className="w-full h-full flex flex-col"
                  >
                    {graphStatus === "not_analyzed" ? (
                      <div className="w-full h-full flex flex-col items-center justify-center bg-[#0a0a0a] rounded-xl border border-[#262626] p-8 text-center">
                        <Network className="w-8 h-8 text-neutral-600 mb-3" />
                        <h3 className="text-sm font-semibold text-white mb-1">AST Analysis Not Available</h3>
                        <p className="text-xs text-neutral-400 max-w-md">
                          This repository has not yet undergone static AST symbol extraction. Run repository indexing to discover modules, classes, and call relationships.
                        </p>
                      </div>
                    ) : graphStatus === "analyzing" ? (
                      <div className="w-full h-full flex flex-col items-center justify-center bg-[#0a0a0a] rounded-xl border border-[#262626] p-8 text-center">
                        <div className="w-7 h-7 border-2 border-white/20 border-t-white rounded-full animate-spin mb-3" />
                        <h3 className="text-sm font-semibold text-white mb-1">Analyzing AST Call Graph</h3>
                        <p className="text-xs text-neutral-400 max-w-md">
                          Scanning module symbol tables, import declarations, and function call hierarchies...
                        </p>
                      </div>
                    ) : graphStatus === "failed" ? (
                      <div className="w-full h-full flex flex-col items-center justify-center bg-[#0a0a0a] rounded-xl border border-red-500/30 p-8 text-center">
                        <X className="w-8 h-8 text-red-400 mb-3" />
                        <h3 className="text-sm font-semibold text-white mb-1">AST Analysis Error</h3>
                        <p className="text-xs text-red-400/80 font-mono max-w-md mb-2">
                          {repo.call_graph_error || "Failed to parse repository abstract syntax tree."}
                        </p>
                      </div>
                    ) : (
                      <div className="w-full h-full flex flex-col relative">
                        {graphStatus === "zero_edges" && (
                          <div className="mb-2 px-3.5 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-[11px] font-mono text-neutral-400 flex items-center justify-between shrink-0">
                            <span>
                              Static AST analysis identified <strong className="text-neutral-200">{callGraphNodes.length}</strong> symbols, but detected <strong className="text-neutral-200">0</strong> direct internal call, import, or render relationships.
                            </span>
                            <Badge variant="outline" className="text-[9px] uppercase border-[#333] text-neutral-400">
                              Zero Internal Edges
                            </Badge>
                          </div>
                        )}
                        <div className="flex-1 min-h-0">
                          <CallGraphView
                            nodes={callGraphNodes}
                            edges={callGraphEdges}
                            onSelectNode={setSelectedNode}
                            selectedNodeId={selectedNode?.id}
                          />
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}

                {activeTab === "tree" && (
                  <motion.div
                    key="tree"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="w-full h-full bg-[#0a0a0a] rounded-xl border border-[#262626] p-6 overflow-y-auto font-mono text-xs shadow-2xl"
                  >
                    <h3 className="text-sm font-bold text-white mb-4 tracking-tight flex items-center gap-2">
                      <Folder className="w-4 h-4 text-white" />
                      <span>Framework-Aware Project Directory Hierarchy</span>
                    </h3>

                    <div className="space-y-3 max-w-3xl">
                      {/* Backend services */}
                      <div className="border border-[#222] rounded-xl p-3 bg-black">
                        <button
                          onClick={() => toggleFolder("backend")}
                          className="flex items-center gap-2 text-white font-semibold w-full text-left cursor-pointer"
                        >
                          {expandedFolders["backend"] ? (
                            <ChevronDown className="w-4 h-4 text-neutral-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-neutral-400" />
                          )}
                          <Folder className="w-4 h-4 text-amber-400" />
                          <span>backend/app</span>
                          <span className="text-[10px] text-neutral-500">(FastAPI, Cognee Memory Orchestration)</span>
                        </button>

                        {expandedFolders["backend"] && (
                          <div className="mt-2.5 pl-6 space-y-1.5 text-neutral-300 border-l border-[#262626] ml-2">
                            <div className="flex items-center gap-2">
                              <FileCode className="w-3.5 h-3.5 text-neutral-400" />
                              <span>services/context_service.py</span>
                              <Badge variant="outline" className="text-[9px] border-[#333]">Pipeline Entry</Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <FileCode className="w-3.5 h-3.5 text-neutral-400" />
                              <span>services/cognee_service.py</span>
                              <Badge variant="outline" className="text-[9px] border-[#333]">LanceDB + Kuzu</Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <FileCode className="w-3.5 h-3.5 text-neutral-400" />
                              <span>services/package_builder.py</span>
                              <Badge variant="outline" className="text-[9px] border-[#333]">Budget &amp; Render</Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <FileCode className="w-3.5 h-3.5 text-neutral-400" />
                              <span>services/repository_summary.py</span>
                              <Badge variant="outline" className="text-[9px] border-[#333]">AST Extraction</Badge>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Frontend src */}
                      <div className="border border-[#222] rounded-xl p-3 bg-black">
                        <button
                          onClick={() => toggleFolder("src")}
                          className="flex items-center gap-2 text-white font-semibold w-full text-left cursor-pointer"
                        >
                          {expandedFolders["src"] ? (
                            <ChevronDown className="w-4 h-4 text-neutral-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-neutral-400" />
                          )}
                          <Folder className="w-4 h-4 text-cyan-400" />
                          <span>src/</span>
                          <span className="text-[10px] text-neutral-500">(React, TypeScript, Tauri IPC UI)</span>
                        </button>

                        {expandedFolders["src"] && (
                          <div className="mt-2.5 pl-6 space-y-1.5 text-neutral-300 border-l border-[#262626] ml-2">
                            <div className="flex items-center gap-2">
                              <FileCode className="w-3.5 h-3.5 text-neutral-400" />
                              <span>pages/ContextStudio.tsx</span>
                              <Badge variant="outline" className="text-[9px] border-[#333]">Studio Workbench</Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <FileCode className="w-3.5 h-3.5 text-neutral-400" />
                              <span>pages/KnowledgeExplorer.tsx</span>
                              <Badge variant="outline" className="text-[9px] border-[#333]">AST Map</Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <FileCode className="w-3.5 h-3.5 text-neutral-400" />
                              <span>components/repositories/CallGraphView.tsx</span>
                              <Badge variant="outline" className="text-[9px] border-[#333]">SVG Graph</Badge>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}

                {activeTab === "components" && (
                  <motion.div
                    key="components"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="w-full h-full bg-[#0a0a0a] rounded-xl border border-[#262626] p-6 overflow-y-auto shadow-2xl space-y-6"
                  >
                    <div>
                      <h3 className="text-sm font-bold text-white mb-1 tracking-tight flex items-center gap-2">
                        <Layers className="w-4 h-4 text-white" />
                        <span>Key Architectural Components</span>
                      </h3>
                      <p className="text-xs font-mono text-neutral-400 mb-4">
                        Components ranked by structural centrality and incoming call volume.
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {repo.components && repo.components.length > 0 ? (
                          repo.components.map((comp, idx) => (
                            <div
                              key={comp}
                              className="bg-black border border-[#222222] rounded-xl p-4 flex items-start justify-between gap-3"
                            >
                              <div>
                                <span className="text-sm font-bold text-white font-mono block">
                                  {comp}
                                </span>
                                <span className="text-[11px] font-mono text-neutral-400 mt-1 block">
                                  Rank #{idx + 1} Centrality
                                </span>
                              </div>
                              <Badge
                                variant="outline"
                                className={cn(
                                  "text-[10px] font-mono uppercase px-2 py-0.5",
                                  idx < 3
                                    ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                                    : "border-[#333] text-neutral-400"
                                )}
                              >
                                {idx < 3 ? "Core" : "Peripheral"}
                              </Badge>
                            </div>
                          ))
                        ) : (
                          <div className="col-span-full p-8 text-center text-xs font-mono text-neutral-500 bg-black rounded-xl border border-[#222]">
                            No specific component annotations found. Re-index to re-extract AST components.
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Entry Points Section */}
                    {repo.entry_points && repo.entry_points.length > 0 && (
                      <div>
                        <h4 className="text-xs font-mono uppercase tracking-wider font-semibold text-neutral-400 mb-3 flex items-center gap-2">
                          <Terminal className="w-3.5 h-3.5 text-white" />
                          <span>Discovered Entry Points &amp; Executables</span>
                        </h4>

                        <div className="space-y-2">
                          {repo.entry_points.map((ep) => (
                            <div
                              key={ep}
                              className="bg-black border border-[#222] rounded-lg p-3 text-xs font-mono text-neutral-200 flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2 truncate">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                                <span className="truncate">{ep}</span>
                              </div>
                              <Badge variant="outline" className="text-[10px] border-[#333] shrink-0">
                                Entry Point
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
            <p className="text-sm font-mono text-neutral-400">
              Workspace not found. Check repository list or return to catalog.
            </p>
            <Button
              onClick={() => navigate("/")}
              className="mt-4 bg-white text-black text-xs font-mono font-bold hover:bg-neutral-200"
            >
              Back to Repositories
            </Button>
          </div>
        )}
      </main>

      {/* Quick Context Modal */}
      {repo && (
        <QuickContextModal
          repo={repo}
          open={showQuickContext}
          onOpenChange={setShowQuickContext}
        />
      )}
    </div>
  );
}
