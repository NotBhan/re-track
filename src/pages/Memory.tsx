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
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground">
      <TopBar title="RE:Track | Memory Graph">
        <div className="relative w-64 hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search memory space..."
            className="h-8 pl-8 text-xs font-mono bg-background border-border/80"
          />
        </div>
      </TopBar>

      <main className="flex-1 overflow-y-auto p-5">
        <div className="max-w-6xl mx-auto space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border/80 pb-4">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  Cognee Semantic Memory Graph
                </h1>
                <Badge variant="secondary" className="text-xs font-mono">
                  {datasets.length} datasets
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Vector embeddings, knowledge graphs, and persistent repository concepts.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-24 text-center gap-3">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-xs font-mono text-muted-foreground">
                Connecting to Cognee graph store...
              </p>
            </div>
          ) : (
            <div className="flex flex-col lg:flex-row gap-5">
              <div className="flex-1">
                <DatasetTable onForget={setForgetDataset} />
              </div>
              <div className="w-full lg:w-80">
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
