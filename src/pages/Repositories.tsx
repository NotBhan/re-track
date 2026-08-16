import { useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { RepoCard } from "@/components/repositories/RepoCard";
import { RepoDetailPanel } from "@/components/repositories/RepoDetailPanel";
import { useRepositoryStore } from "@/stores/repository-store";
import { Search, FolderOpen, Loader2, GitBranch } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

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

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  const filtered = repositories.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.local_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground">
      <TopBar title="RE:Track | Workspaces & Repositories">
        <div className="relative w-80 max-w-full hidden md:block">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <Input
            type="text"
            placeholder="Search workspaces by name or path..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 pl-10 text-xs font-mono bg-[#0a0a0a] border-[#262626] rounded-lg text-white placeholder:text-neutral-500 focus-visible:ring-1 focus-visible:ring-white"
          />
        </div>
      </TopBar>

      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden p-6 gap-6 max-w-[1700px] w-full mx-auto">
        {/* Repo Catalog Grid */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#0a0a0a] rounded-xl border border-[#262626] p-6 shadow-2xl">
          {/* Deck Header */}
          <div className="flex justify-between items-center mb-6 pb-4 border-b border-[#262626]">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-black border border-[#262626] flex items-center justify-center text-white">
                <GitBranch className="w-4 h-4 text-white" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white tracking-tight">
                  Active Codebases
                </h2>
                <p className="text-xs font-mono text-neutral-400">
                  AST Knowledge & Semantic Embeddings
                </p>
              </div>
              <Badge variant="outline" className="text-xs font-mono border-[#2a2a2a] bg-black text-neutral-300 ml-2">
                {filtered.length} Indexed
              </Badge>
            </div>

            <div className="flex items-center gap-2.5">
              <span className="text-xs font-mono text-neutral-400 hidden sm:inline">
                Indexed Local Catalogs
              </span>
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
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center gap-3 bg-black rounded-xl border border-[#262626]">
              <div className="w-12 h-12 rounded-xl bg-[#141414] border border-[#262626] flex items-center justify-center text-neutral-500">
                <FolderOpen className="w-6 h-6 text-neutral-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">
                  {searchQuery ? "No matching repositories found" : "No repositories indexed yet"}
                </h3>
                <p className="text-xs text-neutral-400 mt-1 max-w-sm">
                  {searchQuery
                    ? "Try refining your search keyword above."
                    : "Click '+ Index Repository' in the sidebar to index a local directory."}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto pr-2">
              <div className="grid grid-cols-1 2xl:grid-cols-2 gap-4">
                {filtered.map((repo) => (
                  <RepoCard
                    key={repo.id}
                    repo={repo}
                    selected={repo.id === selectedId}
                    onSelect={() => select(repo.id === selectedId ? null : repo.id)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Fixed width Detail Panel */}
        <div className="w-full lg:w-[440px] xl:w-[460px] flex-shrink-0 flex flex-col h-full">
          <RepoDetailPanel />
        </div>
      </main>
    </div>
  );
}
