import { TopBar } from "@/components/layout/TopBar";
import { RepoCard } from "@/components/repositories/RepoCard";
import { RepoDetailPanel } from "@/components/repositories/RepoDetailPanel";
import { useRepositoryStore } from "@/stores/repository-store";
import { Search } from "lucide-react";

export default function Repositories() {
  const { repositories, selectedId, searchQuery, setSearchQuery, select } =
    useRepositoryStore();

  const filtered = repositories.filter(
    (r) =>
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.path.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
              <button className="border border-outline-variant bg-transparent hover:bg-surface-variant text-on-surface text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded px-3 py-1.5 transition-colors flex items-center gap-2">
                Filter
              </button>
              <button className="border border-outline-variant bg-transparent hover:bg-surface-variant text-on-surface text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded px-3 py-1.5 transition-colors flex items-center gap-2">
                Sort
              </button>
            </div>
          </div>
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
        </div>

        {/* Detail Panel */}
        <RepoDetailPanel />
      </main>
    </>
  );
}
