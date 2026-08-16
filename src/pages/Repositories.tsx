import { useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { RepoCard } from "@/components/repositories/RepoCard";
import { RepoDetailPanel } from "@/components/repositories/RepoDetailPanel";
import { useRepositoryStore } from "@/stores/repository-store";
import { Search, FolderOpen, Loader2, Plus, SlidersHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
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
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-background">
      <TopBar title="RE:Track | Repositories">
        <div className="relative w-72 max-w-full hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Filter by name or path..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-9 text-xs font-mono bg-background border-border/80"
          />
        </div>
      </TopBar>

      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden p-5 gap-5">
        {/* Repo Grid */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-bold text-foreground tracking-tight">
                Indexed Workspaces
              </h2>
              <Badge variant="secondary" className="text-xs font-mono">
                {filtered.length} total
              </Badge>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                <SlidersHorizontal className="w-3.5 h-3.5" />
                <span>Filter</span>
              </Button>
              <Button size="sm" className="h-8 gap-1.5 text-xs font-semibold">
                <Plus className="w-4 h-4" />
                <span>Add Repo</span>
              </Button>
            </div>
          </div>

          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center gap-3">
              <Loader2 className="w-7 h-7 text-primary animate-spin" />
              <p className="text-muted-foreground text-xs font-mono">
                Loading repository catalog...
              </p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center gap-3 bg-card/40 rounded-xl border border-border/70">
              <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center">
                <FolderOpen className="w-6 h-6 text-muted-foreground" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  {searchQuery ? "No matching repositories" : "No repositories indexed"}
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  {searchQuery ? "Try refining your search keyword" : "Import a local folder or git repository to begin"}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto pr-1">
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-3.5">
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

        {/* Detail Panel */}
        <RepoDetailPanel />
      </main>
    </div>
  );
}
