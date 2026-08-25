import { useState, useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { DatasetTable } from "@/components/memory/DatasetTable";
import { VectorSpaceView } from "@/components/memory/VectorSpaceView";
import { KnowledgeGraphView } from "@/components/memory/KnowledgeGraphView";
import { MemoryStats } from "@/components/memory/MemoryStats";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Search, Loader2, Database, Layers, Share2 } from "lucide-react";
import { useMemoryStore, type MemoryTabType } from "@/stores/memory-store";
import { useHealthStore } from "@/stores/health-store";
import { forgetDataset as forgetDatasetApi } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export default function Memory() {
  const [forgetDataset, setForgetDataset] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const {
    providerIdentity,
    providerReachable,
    activeModel,
    configuredModel,
    cogneeInitialized,
  } = useHealthStore();

  const providerLabel =
    providerIdentity === "lmstudio"
      ? "LM Studio"
      : providerIdentity === "ollama"
      ? "Ollama"
      : providerIdentity === "openai_compatible"
      ? "OpenAI Compatible"
      : providerIdentity || "Provider";

  const {
    loading,
    fetchDatasets,
    fetchStats,
    fetchMemoryVectors,
    fetchMemoryGraph,
    datasets,
    activeTab,
    setActiveTab,
    searchQuery,
    setSearchQuery,
  } = useMemoryStore();

  useEffect(() => {
    fetchDatasets();
    fetchStats();
  }, [fetchDatasets, fetchStats]);

  const handleConfirmForget = async () => {
    if (forgetDataset) {
      try {
        await forgetDatasetApi({ dataset: forgetDataset.name });
        await fetchDatasets();
        await fetchStats();
        if (activeTab === "vectors") await fetchMemoryVectors();
        if (activeTab === "graph") await fetchMemoryGraph();
      } catch (error) {
        console.error("Failed to forget dataset:", error);
      }
      setForgetDataset(null);
    }
  };

  const tabs: { id: MemoryTabType; label: string; icon: typeof Database; badge?: string | number }[] = [
    {
      id: "datasets",
      label: "Datasets & Files",
      icon: Database,
      badge: datasets?.length || 0,
    },
    {
      id: "vectors",
      label: "Vector Space",
      icon: Layers,
    },
    {
      id: "graph",
      label: "Knowledge Graph",
      icon: Share2,
    },
  ];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased font-sans">
      <TopBar title="RE:Track | Memory Graph" subtitle="Cognee Semantic Graph & Vectors">
        <div className="relative w-48 sm:w-64 hidden sm:block">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-500" />
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memory..."
            className="h-8 pl-8 pr-3 text-xs bg-[#0a0a0a] border-[#222222] text-white placeholder:text-neutral-500 focus:border-white rounded-md font-mono"
          />
        </div>
      </TopBar>

      <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 lg:p-6">
        <div className="max-w-6xl mx-auto space-y-5">
          {/* Header & Tabs Navigation */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1a1a1a] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-white">
                  Cognee Semantic Memory Graph
                </h1>
                <Badge variant="outline" className="text-[11px] font-mono">
                  {datasets?.length || 0} datasets
                </Badge>
                {/* Independent Inference Provider Status */}
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono border",
                    providerReachable
                      ? "bg-emerald-950/30 text-emerald-300 border-emerald-500/30"
                      : "bg-red-950/30 text-red-300 border-red-500/30"
                  )}
                  title={`Inference Provider: ${providerLabel} (${providerReachable ? "Healthy" : "Offline"})`}
                >
                  <span
                    className={cn(
                      "w-1.5 h-1.5 rounded-full shrink-0",
                      providerReachable ? "bg-emerald-400" : "bg-red-400"
                    )}
                  />
                  <span>
                    {providerLabel}: {providerReachable ? (activeModel || configuredModel || "Ready") : "Offline"}
                  </span>
                </span>
                {/* Independent Cognee Memory Status */}
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono border",
                    cogneeInitialized
                      ? "bg-neutral-900 text-neutral-300 border-[#333]"
                      : "bg-amber-950/30 text-amber-300 border-amber-500/30"
                  )}
                  title={`Cognee Memory Engine: ${cogneeInitialized ? "Initialized" : "Offline / Uninitialized"}`}
                >
                  <span
                    className={cn(
                      "w-1.5 h-1.5 rounded-full shrink-0",
                      cogneeInitialized ? "bg-emerald-400" : "bg-amber-400"
                    )}
                  />
                  <span>
                    Cognee: {cogneeInitialized ? "Initialized" : "Offline"}
                  </span>
                </span>
              </div>
              <p className="text-xs text-neutral-500 mt-0.5">
                Vector embeddings, semantic knowledge graphs, and persistent repository concepts.
              </p>
            </div>

            {/* View Mode Tabs */}
            <div className="flex items-center gap-1 bg-[#0a0a0a] p-1 rounded-lg border border-[#222222]">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors cursor-pointer font-mono",
                      isActive
                        ? "bg-white text-black font-semibold shadow-xs"
                        : "text-neutral-400 hover:text-white hover:bg-[#141414]"
                    )}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                    {tab.badge !== undefined && (
                      <span
                        className={cn(
                          "ml-1 text-[10px] px-1.5 py-0.2 rounded-full",
                          isActive
                            ? "bg-black/15 text-black"
                            : "bg-[#222222] text-neutral-400"
                        )}
                      >
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-center gap-2 bg-[#050505] rounded-lg border border-[#1e1e1e]">
              <Loader2 className="w-5 h-5 text-neutral-400 animate-spin" />
              <p className="text-xs text-neutral-500 font-mono">
                Connecting to Cognee memory store...
              </p>
            </div>
          ) : (
            <div>
              {activeTab === "datasets" && (
                <div className="flex flex-col lg:flex-row gap-4">
                  <div className="flex-1 min-w-0">
                    <DatasetTable onForget={setForgetDataset} />
                  </div>
                  <div className="w-full lg:w-80 shrink-0">
                    <MemoryStats />
                  </div>
                </div>
              )}

              {activeTab === "vectors" && <VectorSpaceView />}

              {activeTab === "graph" && <KnowledgeGraphView />}
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
