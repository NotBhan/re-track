import { useEffect, useState, useMemo } from "react";
import {
  FileText,
  Sparkles,
  Plus,
  Search,
  ArrowRightLeft,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { ContextPackageCard } from "@/components/context-packages/ContextPackageCard";
import { useContextPackageStore } from "@/stores/context-package-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { PackageCardSkeleton } from "@/components/ui/skeleton-loaders";
import type { SavedContextPackage } from "@/lib/api";

export default function ContextPackages() {
  const { packages, loading, error, fetchPackages } = useContextPackageStore();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRepoFilter, setSelectedRepoFilter] = useState("all");
  const [compareList, setCompareList] = useState<SavedContextPackage[]>([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  // Extract unique repo names
  const repoNames = useMemo(() => {
    const set = new Set<string>();
    packages.forEach((p) => {
      if (p.repository_name) set.add(p.repository_name);
    });
    return Array.from(set);
  }, [packages]);

  const filteredPackages = useMemo(() => {
    return packages.filter((pkg) => {
      const matchesSearch =
        !searchQuery ||
        pkg.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        pkg.task.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (pkg.repository_name && pkg.repository_name.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesRepo =
        selectedRepoFilter === "all" || pkg.repository_name === selectedRepoFilter;

      return matchesSearch && matchesRepo;
    });
  }, [packages, searchQuery, selectedRepoFilter]);

  const handleToggleCompare = (pkg: SavedContextPackage) => {
    if (compareList.some((p) => p.id === pkg.id)) {
      setCompareList(compareList.filter((p) => p.id !== pkg.id));
    } else {
      if (compareList.length >= 2) {
        setCompareList([compareList[1], pkg]);
      } else {
        setCompareList([...compareList, pkg]);
      }
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased font-sans">
      <TopBar title="RE:Track | Context Packages" subtitle="Versioned Context Library">
        <div className="flex items-center gap-1.5 sm:gap-2">
          {compareList.length === 2 && (
            <Button
              size="sm"
              onClick={() => setShowCompareModal(true)}
              className="h-8 px-2.5 sm:px-3 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 gap-1.5 shadow-sm cursor-pointer"
            >
              <ArrowRightLeft className="w-3.5 h-3.5" />
              <span className="hidden xs:inline">Compare</span>
              <span className="hidden sm:inline">2 Packages</span>
            </Button>
          )}

          <Button
            onClick={() => navigate("/studio")}
            size="sm"
            className="gap-1.5 h-8 px-2.5 sm:px-3.5 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden xs:inline">New Package</span>
          </Button>
        </div>
      </TopBar>

      <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 lg:p-6">
        <div className="max-w-5xl mx-auto space-y-5">
          {/* Header & Filter Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1a1a1a] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-white">
                  Context Packages Library
                </h1>
                <Badge variant="outline" className="text-[11px] font-mono">
                  {filteredPackages.length} packages
                </Badge>
              </div>
              <p className="text-xs text-neutral-500 mt-0.5">
                Saved markdown packages synthesized for Cursor, Claude, and local AI coding assistants.
              </p>
            </div>

            {/* Search & Repository Filter */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative w-48 sm:w-56">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-400" />
                <Input
                  type="text"
                  placeholder="Filter packages..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-7.5 pl-7 pr-6 text-xs bg-[#050505] border-[#222222] rounded-md text-white placeholder:text-neutral-500"
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

              {repoNames.length > 0 && (
                <select
                  value={selectedRepoFilter}
                  onChange={(e) => setSelectedRepoFilter(e.target.value)}
                  className="h-7.5 px-2.5 text-xs font-sans bg-[#050505] border border-[#222222] rounded-md text-neutral-300 focus:outline-none focus:border-neutral-400 cursor-pointer"
                >
                  <option value="all">All Codebases</option>
                  {repoNames.map((rn) => (
                    <option key={rn} value={rn}>
                      {rn}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="bg-red-950/20 text-red-400 border border-red-500/20 rounded-md p-3 text-xs font-mono">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col gap-2.5">
              <PackageCardSkeleton />
              <PackageCardSkeleton />
              <PackageCardSkeleton />
            </div>
          )}

          {/* Empty State */}
          {!loading && filteredPackages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center bg-[#050505] rounded-lg border border-[#1e1e1e] p-6">
              <div className="w-10 h-10 rounded-lg bg-[#0f0f0f] border border-[#222222] flex items-center justify-center mb-3 text-neutral-400">
                <FileText className="w-5 h-5 text-neutral-300" />
              </div>
              <h3 className="text-sm font-semibold text-white tracking-tight">
                {searchQuery || selectedRepoFilter !== "all" ? "No matching packages found" : "No context packages saved yet"}
              </h3>
              <p className="text-xs text-neutral-500 max-w-sm mt-1 mb-4 leading-relaxed">
                {searchQuery || selectedRepoFilter !== "all"
                  ? "Try refining your search keyword or reset filters."
                  : "Synthesize task context in Context Studio and click 'Save to Library' to store reusable packages."}
              </p>
              {searchQuery || selectedRepoFilter !== "all" ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchQuery("");
                    setSelectedRepoFilter("all");
                  }}
                  className="h-7.5 px-3 text-xs"
                >
                  Reset filters
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={() => navigate("/studio")}
                  className="gap-1.5 h-7.5 px-3 text-xs bg-white text-black font-medium hover:bg-neutral-200 cursor-pointer shadow-xs"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>Launch Context Studio</span>
                </Button>
              )}
            </div>
          )}

          {/* Package List */}
          {!loading && filteredPackages.length > 0 && (
            <div className="flex flex-col gap-2.5">
              {filteredPackages.map((pkg) => (
                <ContextPackageCard
                  key={pkg.id}
                  pkg={pkg}
                  onCompareSelect={handleToggleCompare}
                  isCompareSelected={compareList.some((p) => p.id === pkg.id)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Compare Modal */}
      {showCompareModal && compareList.length === 2 && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-5xl h-[85vh] bg-[#0a0a0a] border border-[#262626] rounded-2xl shadow-2xl flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[#262626] bg-[#0d0d0d] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-white" />
                <h3 className="text-sm font-bold text-white">Side-by-Side Context Package Comparison</h3>
              </div>
              <button
                onClick={() => setShowCompareModal(false)}
                className="p-1 rounded hover:bg-[#222] text-neutral-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 min-h-0 grid grid-cols-2 divide-x divide-[#262626] overflow-hidden">
              {compareList.map((p, idx) => (
                <div key={p.id} className="flex flex-col h-full overflow-hidden p-5 space-y-3">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-neutral-500 block">Package #{idx + 1}</span>
                    <h4 className="text-sm font-bold text-white truncate">{p.name}</h4>
                    <p className="text-xs font-mono text-neutral-400 mt-0.5 truncate">{p.task}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant="outline" className="text-[10px] font-mono">~{p.token_estimate} tokens</Badge>
                      <span className="text-[10px] font-mono text-neutral-500">{p.repository_name}</span>
                    </div>
                  </div>

                  <div className="flex-1 min-h-0 bg-black rounded-xl border border-[#222] p-4 overflow-y-auto font-mono text-xs text-neutral-300 whitespace-pre-wrap">
                    {p.markdown}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
