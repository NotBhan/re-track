import { useEffect, useState } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { RepositoryCard } from "@/components/repositories/RepositoryCard";
import { RepositoryDetailPanel } from "@/components/repositories/RepositoryDetailPanel";
import { RepositoryCardSkeleton } from "@/components/ui/skeleton-loaders";
import { ProviderAlertBanner } from "@/components/shared/ProviderAlertBanner";
import { useRepositoryStore } from "@/stores/repository-store";
import {
  Search,
  LayoutGrid,
  Info,
  FolderGit2,
  X,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
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
        <div className="relative w-48 sm:w-60 md:w-64 max-w-full hidden sm:block">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400" />
          <Input
            type="text"
            placeholder="Filter workspaces..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-8 pr-7 text-xs font-mono bg-[#050505] border-[#222222] rounded-md text-neutral-200 placeholder:text-neutral-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              aria-label="Clear search"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white p-0.5 rounded cursor-pointer"
            >
              <X className="w-3 h-3" />
            </button>
          )}
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

      {/* Main Content Area */}
      <main className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden p-4 sm:p-5 lg:p-6 gap-5 lg:gap-6 max-w-[1900px] w-full mx-auto">
        {/* Left Column: Repository Catalog */}
        <div
          className={`flex-1 min-h-0 flex flex-col overflow-hidden bg-[#0a0a0a] rounded-lg border border-[#1e1e1e] p-4 sm:p-5 ${
            mobileTab === "detail" ? "hidden lg:flex" : "flex"
          }`}
        >
          {/* AI Provider Health Alert Banner */}
          <div className="mb-3">
            <ProviderAlertBanner />
          </div>

          {/* Deck Header */}
          <div className="flex justify-between items-center mb-4 pb-3 border-b border-[#1a1a1a] shrink-0">
            <div className="flex items-center gap-2.5">
              <div>
                <h2 className="text-sm font-semibold text-white tracking-tight">
                  Active Codebases
                </h2>
                <p className="text-xs text-neutral-500">
                  AST Knowledge &amp; Semantic Embeddings
                </p>
              </div>
              <Badge
                variant="outline"
                className="text-[11px] font-mono ml-2 hidden sm:inline-flex"
              >
                {filtered.length} indexed
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
                className="h-7 pl-7 pr-6 text-xs bg-[#050505] border-[#222222] rounded-md text-white placeholder:text-neutral-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  aria-label="Clear search"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white p-0.5 rounded cursor-pointer"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {loading && repositories.length === 0 ? (
            <div className="flex-1 min-h-0 overflow-y-auto pr-1">
              <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-2 gap-3">
                <RepositoryCardSkeleton />
                <RepositoryCardSkeleton />
                <RepositoryCardSkeleton />
                <RepositoryCardSkeleton />
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
              className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#050505] rounded-lg border border-[#1e1e1e]"
            >
              <div className="w-12 h-12 rounded-lg bg-[#0f0f0f] border border-[#222222] flex items-center justify-center mb-3 text-neutral-400">
                <FolderGit2 className="w-6 h-6 text-neutral-300" />
              </div>

              <h3 className="text-sm font-semibold text-white tracking-tight mb-1">
                {searchQuery ? "No matching repositories" : "No repositories indexed yet"}
              </h3>

              <p className="text-xs text-neutral-500 max-w-sm leading-relaxed mb-3">
                {searchQuery
                  ? `No indexed repositories match "${searchQuery}". Clear the search query to see all workspaces.`
                  : "Index a local directory or Git repository to generate semantic embeddings and AST call graphs."}
              </p>

              {searchQuery && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSearchQuery("")}
                  className="h-7.5 px-3 text-xs"
                >
                  Clear search filter
                </Button>
              )}
            </motion.div>
          ) : (
            <div className="flex-1 min-h-0 overflow-y-auto pr-1">
              <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-2 gap-3">
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
