import { useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { RepoCard } from "@/components/repositories/RepoCard";
import { RepoDetailPanel } from "@/components/repositories/RepoDetailPanel";
import { useRepositoryStore } from "@/stores/repository-store";
import { Search, FolderOpen, Loader2, Plus } from "lucide-react";
import { open } from "@tauri-apps/plugin-dialog";

export default function Repositories() {
  const {
    repositories,
    selectedId,
    searchQuery,
    setSearchQuery,
    select,
    fetchRepositories,
    indexRepo,
    loading,
  } = useRepositoryStore();

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  const filtered = repositories.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleNewIndex = async () => {
    const selected = await open({ directory: true, multiple: false });
    if (selected) {
      const name = selected.split("/").pop() || "repo";
      await indexRepo(selected, name);
    }
  };

  return (
    <>
      <TopBar>
        <div className="relative w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-on-surface-variant" />
          <input
            type="text"
            placeholder="Search repositories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent border-b border-transparent focus:border-primary border-t-0 border-x-0 outline-none text-on-surface text-[14px] leading-[20px] pl-10 py-2 transition-colors placeholder:text-on-surface-variant/50"
          />
        </div>
      </TopBar>
      <main className="flex-1 flex overflow-hidden p-6 gap-6">
        {/* Repo Grid */}
        <div className="flex-1 overflow-y-auto pr-2">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface">
              Active Repositories
            </h2>
            <div className="flex gap-2">
              <button
                onClick={handleNewIndex}
                className="bg-primary hover:bg-primary/90 text-on-primary text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded px-3 py-1.5 transition-colors flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                New Index
              </button>
              <button className="border border-outline-variant bg-transparent hover:bg-surface-variant text-on-surface text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded px-3 py-1.5 transition-colors flex items-center gap-2">
                Filter
              </button>
              <button className="border border-outline-variant bg-transparent hover:bg-surface-variant text-on-surface text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded px-3 py-1.5 transition-colors flex items-center gap-2">
                Sort
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-on-surface-variant text-[14px]">
                Loading repositories...
              </p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <FolderOpen className="w-12 h-12 text-on-surface-variant/50" />
              <p className="text-on-surface-variant text-[14px]">
                {searchQuery
                  ? "No repositories match your search"
                  : "No repositories indexed yet"}
              </p>
              {!searchQuery && (
                <button
                  onClick={handleNewIndex}
                  className="bg-primary hover:bg-primary/90 text-on-primary text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded px-4 py-2 transition-colors flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Index a Repository
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
              {filtered.map((repo) => (
                <RepoCard
                  key={repo.id}
                  repo={repo}
                  selected={repo.id === selectedId}
                  onSelect={() => select(repo.id === selectedId ? null : repo.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <RepoDetailPanel />
      </main>
    </>
  );
}
