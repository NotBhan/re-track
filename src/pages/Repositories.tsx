import { useEffect, useState } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { RepositoryCard } from "@/components/repositories/RepositoryCard";
import { RepositoryDetailPanel } from "@/components/repositories/RepositoryDetailPanel";
import { ProviderAlertBanner } from "@/components/shared/ProviderAlertBanner";
import { useRepositoryStore } from "@/stores/repository-store";
import {
  Search,
  Loader2,
  GitBranch,
  LayoutGrid,
  Info,
  Sparkles,
  Zap,
  Cpu,
  Layers,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { motion } from "motion/react";

export default function Repositories() {
  const {
    repositories,
    selectedId,
    searchQuery,
    setSearchQuery,
    select,
    fetchRepositories,
    loading,
  } = useRepositoryStore();

  const [mobileTab, setMobileTab] = useState<"catalog" | "detail">("catalog");

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  // When user selects a repository on mobile, switch to detail tab
  const handleSelect = (id: string) => {
    const newId = id === selectedId ? null : id;
    select(newId);
    if (newId) {
      setMobileTab("detail");
    }
  };

  const filtered = repositories.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.local_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased">
      <TopBar title="RE:Track | Workspaces & Repositories" subtitle="Repository Knowledge Base">
        <div className="relative w-72 max-w-full hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400" />
          <Input
            type="text"
            placeholder="Filter workspaces..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-8 text-xs font-mono bg-[#0a0a0a] border-[#262626] rounded-lg text-white placeholder:text-neutral-500 focus-visible:ring-1 focus-visible:ring-white"
          />
        </div>
      </TopBar>

      {/* Mobile Tab Control (< lg screens) */}
      <div className="lg:hidden px-4 pt-3 pb-1 border-b border-[#222222] bg-[#080808]">
        <div className="grid grid-cols-2 gap-1 bg-[#121212] p-1 rounded-lg border border-[#262626]">
          <button
            onClick={() => setMobileTab("catalog")}
            className={`py-1.5 px-3 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              mobileTab === "catalog"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span>Catalog ({filtered.length})</span>
          </button>

          <button
            onClick={() => setMobileTab("detail")}
            className={`py-1.5 px-3 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              mobileTab === "detail"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Info className="w-3.5 h-3.5" />
            <span>Workspace Details</span>
            {selectedId && (
              <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_4px_#ffffff]" />
            )}
          </button>
        </div>
      </div>

      <main className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden p-4 sm:p-6 gap-6 max-w-[1800px] w-full mx-auto">
        {/* Repo Catalog Grid */}
        <div
          className={`flex-1 min-h-0 flex flex-col overflow-hidden bg-[#0a0a0a] rounded-xl border border-[#262626] p-4 sm:p-6 shadow-2xl ${
            mobileTab === "detail" ? "hidden lg:flex" : "flex"
          }`}
        >
          {/* AI Provider Health Alert Banner */}
          <div className="mb-4">
            <ProviderAlertBanner />
          </div>

          {/* Deck Header */}
          <div className="flex justify-between items-center mb-4 sm:mb-6 pb-4 border-b border-[#262626] shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-black border border-[#262626] flex items-center justify-center text-white shrink-0">
                <GitBranch className="w-4 h-4 text-white" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white tracking-tight">
                  Active Codebases
                </h2>
                <p className="text-xs font-mono text-neutral-400">
                  AST Knowledge &amp; Semantic Embeddings
                </p>
              </div>
              <Badge
                variant="outline"
                className="text-xs font-mono border-[#2a2a2a] bg-black text-neutral-300 ml-2 hidden sm:inline-flex"
              >
                {filtered.length} Indexed
              </Badge>
            </div>

            {/* Mobile Search Bar inline */}
            <div className="md:hidden relative w-36">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-400" />
              <Input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-7 text-xs font-mono bg-black border-[#262626] rounded-md text-white placeholder:text-neutral-500"
              />
            </div>
          </div>

          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center gap-3">
              <Loader2 className="w-8 h-8 text-white animate-spin" />
              <p className="text-neutral-400 text-xs font-mono">
                Loading repository catalog...
              </p>
            </div>
          ) : filtered.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-gradient-to-b from-[#111111] to-black rounded-2xl border border-[#262626] relative overflow-hidden"
            >
              {/* Subtle ambient glow */}
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_40%,rgba(255,255,255,0.03),transparent_70%)] pointer-events-none" />

              <div className="w-16 h-16 rounded-2xl bg-black border border-[#2e2e2e] flex items-center justify-center mb-5 text-white shadow-xl">
                <Sparkles className="w-8 h-8 text-white" />
              </div>

              <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight mb-2">
                {searchQuery ? "No matching repositories found" : "Persistent AI Memory for Your Codebase"}
              </h3>

              <p className="text-xs sm:text-sm text-neutral-400 max-w-md mb-6 leading-relaxed font-sans">
                {searchQuery
                  ? "Try refining your search keyword above or clear the filter."
                  : "Point RE:Track at any local repository. It continuously indexes AST structure, call graphs, and architectural decisions into local memory for compact context generation."}
              </p>

              {!searchQuery && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-lg w-full mb-8 text-left">
                  <div className="bg-[#0a0a0a] border border-[#222] rounded-xl p-3">
                    <Zap className="w-4 h-4 text-amber-400 mb-1.5" />
                    <h5 className="text-xs font-bold text-white font-mono">Zero Prompt Bloat</h5>
                    <p className="text-[11px] text-neutral-400 mt-0.5">Compresses 50k tokens down to targeted ~1.5k context packages.</p>
                  </div>
                  <div className="bg-[#0a0a0a] border border-[#222] rounded-xl p-3">
                    <Layers className="w-4 h-4 text-emerald-400 mb-1.5" />
                    <h5 className="text-xs font-bold text-white font-mono">AST Call Graph</h5>
                    <p className="text-[11px] text-neutral-400 mt-0.5">Extracts real callers, callees, and component topology.</p>
                  </div>
                  <div className="bg-[#0a0a0a] border border-[#222] rounded-xl p-3">
                    <Cpu className="w-4 h-4 text-cyan-400 mb-1.5" />
                    <h5 className="text-xs font-bold text-white font-mono">100% Local-First</h5>
                    <p className="text-[11px] text-neutral-400 mt-0.5">Runs offline with Ollama or LM Studio models.</p>
                  </div>
                </div>
              )}
            </motion.div>
          ) : (
            <div className="flex-1 min-h-0 overflow-y-auto pr-1">
              <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-2 gap-4">
                {filtered.map((repo) => (
                  <RepositoryCard
                    key={repo.id}
                    repo={repo}
                    selected={repo.id === selectedId}
                    onSelect={() => handleSelect(repo.id)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Detail Panel Container */}
        <div
          className={`w-full lg:w-[440px] xl:w-[460px] flex-shrink-0 flex flex-col h-full min-h-0 ${
            mobileTab === "catalog" ? "hidden lg:flex" : "flex"
          }`}
        >
          <RepositoryDetailPanel />
        </div>
      </main>
    </div>
  );
}
