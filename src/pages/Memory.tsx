import { useState, useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { DatasetTable } from "@/components/memory/DatasetTable";
import { MemoryStats } from "@/components/memory/MemoryStats";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Search, Loader2 } from "lucide-react";
import { useMemoryStore } from "@/stores/memory-store";
import { forgetDataset as forgetDatasetApi } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function Memory() {
  const [forgetDataset, setForgetDataset] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const { loading, fetchDatasets, fetchStats, datasets } = useMemoryStore();

  useEffect(() => {
    fetchDatasets();
    fetchStats();
  }, [fetchDatasets, fetchStats]);

  const handleConfirmForget = async () => {
    if (forgetDataset) {
      try {
        await forgetDatasetApi({ dataset: forgetDataset.name });
        await fetchDatasets();
      } catch (error) {
        console.error("Failed to forget dataset:", error);
      }
      setForgetDataset(null);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased font-sans">
      <TopBar title="RE:Track | Memory Graph" subtitle="Cognee Semantic Graph & Vectors">
        <div className="relative w-56 hidden md:block">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-500" />
          <Input
            type="text"
            placeholder="Search memory space..."
            className="h-7.5 pl-7 text-xs bg-[#0a0a0a] border-[#222222] text-white placeholder:text-neutral-500 focus:border-white rounded-md"
          />
        </div>
      </TopBar>

      <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5">
        <div className="max-w-6xl mx-auto space-y-4">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1a1a1a] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-white">
                  Cognee Semantic Memory Graph
                </h1>
                <Badge variant="outline" className="text-[11px] font-mono">
                  {datasets.length} datasets
                </Badge>
              </div>
              <p className="text-xs text-neutral-500 mt-0.5">
                Vector embeddings, knowledge graphs, and persistent repository concepts.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-center gap-2 bg-[#050505] rounded-lg border border-[#1e1e1e]">
              <Loader2 className="w-5 h-5 text-neutral-400 animate-spin" />
              <p className="text-xs text-neutral-500">
                Connecting to Cognee graph store...
              </p>
            </div>
          ) : (
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1 min-w-0">
                <DatasetTable onForget={setForgetDataset} />
              </div>
              <div className="w-full lg:w-80 shrink-0">
                <MemoryStats />
              </div>
            </div>
          )}
        </div>
      </main>

      <ConfirmDialog
        open={!!forgetDataset}
        onOpenChange={(open) => !open && setForgetDataset(null)}
        title="Forget Dataset"
        description={`Are you sure you want to permanently delete the memory index for "${forgetDataset?.name}"?`}
        warning="This action cannot be undone and will remove all vector embeddings."
        confirmLabel="Forget Dataset"
        variant="destructive"
        onConfirm={handleConfirmForget}
      />
    </div>
  );
}
