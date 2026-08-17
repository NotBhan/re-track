import { useEffect, useState, useMemo } from "react";
import {
  FileText,
  Loader2,
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
        <div className="flex items-center gap-2">
          {compareList.length === 2 && (
            <Button
              size="sm"
              onClick={() => setShowCompareModal(true)}
              className="h-8 px-3 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 gap-1.5 shadow-sm cursor-pointer"
            >
              <ArrowRightLeft className="w-3.5 h-3.5" />
              <span>Compare 2 Packages</span>
            </Button>
          )}

          <Button
            onClick={() => navigate("/studio")}
            size="sm"
            className="gap-1.5 h-8 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Package</span>
          </Button>
        </div>
      </TopBar>

      <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Header & Filter Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#262626] pb-5">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  Context Packages Library
                </h1>
                <Badge variant="outline" className="text-xs font-mono border-[#333] bg-black text-neutral-300">
                  {filteredPackages.length} packages
                </Badge>
              </div>
              <p className="text-xs font-mono text-neutral-400 mt-1">
                Saved markdown packages synthesized for Cursor, Claude, and local AI coding assistants.
              </p>
            </div>

            {/* Search & Repository Filter */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative w-48 sm:w-60">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400" />
                <Input
                  type="text"
                  placeholder="Filter packages..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-8 pl-8 text-xs font-mono bg-[#0a0a0a] border-[#262626] rounded-lg text-white placeholder:text-neutral-500"
                />
              </div>

              {repoNames.length > 0 && (
                <select
                  value={selectedRepoFilter}
                  onChange={(e) => setSelectedRepoFilter(e.target.value)}
                  className="h-8 px-2.5 text-xs font-mono bg-[#0a0a0a] border border-[#262626] rounded-lg text-neutral-300 focus:outline-none focus:border-white cursor-pointer"
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
            <div className="bg-red-500/10 text-red-400 border border-red-500/30 rounded-xl p-4 text-xs font-mono">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-24 text-center gap-3">
              <Loader2 className="w-8 h-8 text-white animate-spin" />
              <p className="text-xs font-mono text-neutral-400">
                Loading saved packages...
              </p>
            </div>
          )}

          {/* Empty State */}
          {!loading && filteredPackages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center bg-[#0a0a0a] rounded-2xl border border-[#262626] p-8">
              <div className="w-14 h-14 rounded-2xl bg-black border border-[#262626] flex items-center justify-center mb-3 text-neutral-500 shadow-xl">
                <FileText className="w-7 h-7 text-neutral-400" />
              </div>
              <h3 className="text-base font-bold text-white tracking-tight">
                {searchQuery ? "No matching packages found" : "No context packages saved yet"}
              </h3>
              <p className="text-xs font-mono text-neutral-400 max-w-sm mt-1 mb-5">
                {searchQuery
                  ? "Try refining your search keyword or reset filters."
                  : "Synthesize task context in Context Studio and click 'Save to Library' to store reusable packages."}
              </p>
              <Button
                size="sm"
                onClick={() => navigate("/studio")}
                className="gap-2 text-xs font-mono font-bold bg-white text-black hover:bg-neutral-200 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Launch Context Studio</span>
              </Button>
            </div>
          )}

          {/* Package List */}
          {!loading && filteredPackages.length > 0 && (
            <div className="flex flex-col gap-3.5">
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
