import { useState, useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { DatasetTable } from "@/components/memory/DatasetTable";
import { MemoryStats } from "@/components/memory/MemoryStats";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Search, Bell, User, Plus, Loader2 } from "lucide-react";
import { useMemoryStore } from "@/stores/memory-store";
import { forgetDataset as forgetDatasetApi } from "@/lib/api";

export default function Memory() {
  const [forgetDataset, setForgetDataset] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const { loading, fetchDatasets, fetchStats } = useMemoryStore();

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
    <>
      <TopBar>
        <h2 className="text-[16px] leading-[24px] font-semibold text-on-surface">
          Memory Browser
        </h2>
        <div className="flex-1 flex justify-end">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
            <input
              type="text"
              placeholder="Search semantic space..."
              className="bg-surface-container border border-outline-variant/30 text-on-surface text-[14px] leading-[20px] rounded-md pl-10 pr-4 py-1.5 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 w-64 transition-all placeholder:text-on-surface-variant/50"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1">
              <kbd className="font-mono text-on-surface-variant/50 border border-outline-variant/30 rounded px-1.5 text-[10px]">
                ⌘
              </kbd>
              <kbd className="font-mono text-on-surface-variant/50 border border-outline-variant/30 rounded px-1.5 text-[10px]">
                K
              </kbd>
            </div>
          </div>
          <div className="flex items-center gap-2 ml-4">
            <button className="text-on-surface-variant hover:text-on-surface hover:bg-surface-variant rounded-full p-2 transition-all relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full border border-background" />
            </button>
            <button className="text-on-surface-variant hover:text-on-surface hover:bg-surface-variant rounded-full p-2 transition-all">
              <User className="w-5 h-5" />
            </button>
            <button className="bg-primary text-white text-[12px] leading-[16px] tracking-[0.02em] font-medium px-4 py-2 rounded-md hover:bg-primary/90 transition-colors ml-2 shadow-[0_0_15px_rgba(59,130,246,0.2)]">
              <Plus className="w-4 h-4 inline mr-1" />
              New Index
            </button>
          </div>
        </div>
      </TopBar>

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-[1440px] mx-auto flex gap-6 h-full flex-col xl:flex-row">
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
          ) : (
            <>
              <DatasetTable onForget={setForgetDataset} />
              <MemoryStats />
            </>
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
    </>
  );
}
