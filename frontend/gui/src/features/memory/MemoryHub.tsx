import React, { useEffect } from "react";
import {
  BrainCircuit,
  Database,
  Binary,
  GitFork,
  FileText,
  Sparkles,
  Info,
  RefreshCw,
} from "lucide-react";
import { useMemoryEngineStore } from "../../stores/memoryStore";
import { IngestedFilesView } from "./IngestedFilesView";
import { VectorSpaceView } from "./VectorSpaceView";
import { KnowledgeGraphView } from "./KnowledgeGraphView";
import { Button } from "../../components/Button";
import { Tabs } from "../../components/Tabs";
import { toast } from "../../app/providers/ToastProvider";

export const MemoryHub: React.FC = () => {
  const {
    datasets,
    selectedDatasetId,
    selectDataset,
    datasetItems,
    stats,
    vectors,
    graph,
    activeTab,
    setActiveTab,
    loadingItems,
    loadingGraph,
    loadingVectors,
    cognifying,
    cognify,
    fetchDatasets,
    fetchStats,
    refreshAll,
  } = useMemoryEngineStore();

  useEffect(() => {
    fetchDatasets();
    fetchStats();
  }, [fetchDatasets, fetchStats]);

  const handleCognify = async () => {
    const success = await cognify();
    if (success) {
      toast.success("Cognification complete: Vector index and knowledge graph updated.");
    } else {
      toast.error("Cognification failed.");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
      {/* Top Header & Cognify Action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-white/[0.06]">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-indigo-400" />
            <span>Memory Engine</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Derived semantic memory, vector indexes, and entity knowledge graphs.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => refreshAll()}
            title="Refresh memory state"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>

          <Button size="sm" loading={cognifying} onClick={handleCognify}>
            <Sparkles className="w-3.5 h-3.5 mr-1 text-sky-300" />
            <span>Cognify Dataset</span>
          </Button>
        </div>
      </div>

      {/* Prominent Epistemic Notice */}
      <div className="p-3.5 rounded-xl bg-sky-950/20 border border-sky-500/20 text-sky-200 flex items-start gap-3">
        <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <strong className="font-semibold text-sky-100">Derived Storage Notice:</strong> This memory engine
          contains synthesized vector chunks (LanceDB) and entity relationship graphs (Kùzu). All records here
          represent derived knowledge extracted from the repository, not raw ground-truth source files.
        </div>
      </div>

      {/* Dataset Scope Selector */}
      <div className="flex items-center justify-between gap-4 p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Dataset Scope:</span>
          <select
            value={selectedDatasetId || ""}
            onChange={(e) => selectDataset(e.target.value || null)}
            className="bg-[#11141a] text-xs font-medium text-slate-200 border border-white/[0.08] rounded-md px-2.5 py-1 outline-none cursor-pointer"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.file_count || 0} files)
              </option>
            ))}
          </select>
        </div>

        {stats && (
          <div className="text-xs font-mono text-slate-400">
            Total derived memory: <strong className="text-slate-200">{stats.total_size_display}</strong>
          </div>
        )}
      </div>

      {/* Tabs: Documents, Vectors, Graph */}
      <div className="flex flex-col gap-4">
        <Tabs
          items={[
            { id: "documents", label: "Documents", count: datasetItems.length, icon: <FileText className="w-3.5 h-3.5" /> },
            { id: "vectors", label: "Vector Space", icon: <Binary className="w-3.5 h-3.5" /> },
            { id: "graph", label: "Knowledge Graph", icon: <GitFork className="w-3.5 h-3.5" /> },
          ]}
          activeId={activeTab}
          onChange={(id) => setActiveTab(id as any)}
        />

        {activeTab === "documents" && (
          <IngestedFilesView items={datasetItems} loading={loadingItems} />
        )}
        {activeTab === "vectors" && (
          <VectorSpaceView vectors={vectors} loading={loadingVectors} />
        )}
        {activeTab === "graph" && (
          <KnowledgeGraphView graph={graph} loading={loadingGraph} />
        )}
      </div>
    </div>
  );
};
