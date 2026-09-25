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
import { Select } from "../../components/Select";
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#262626]">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-[#ededed] flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-[#a1a1a1]" />
            <span>Memory Engine</span>
          </h2>
          <p className="text-xs text-[#a1a1a1] mt-0.5">
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
            <Sparkles className="w-3.5 h-3.5 mr-1 text-[#a1a1a1]" />
            <span>Cognify Dataset</span>
          </Button>
        </div>
      </div>

      {/* Prominent Epistemic Notice */}
      <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] text-[#a1a1a1] flex items-start gap-3">
        <Info className="w-4 h-4 text-[#707070] shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <strong className="font-semibold text-[#ededed]">Derived Storage Notice:</strong> This memory engine
          contains synthesized vector chunks (LanceDB) and entity relationship graphs (Kùzu). All records here
          represent derived knowledge extracted from the repository, not raw ground-truth source files.
        </div>
      </div>

      {/* Dataset Scope Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3 rounded-lg bg-[#0a0a0a] border border-[#262626]">
        <div className="flex items-center gap-2 min-w-0">
          <Database className="w-4 h-4 text-[#707070] shrink-0" />
          <span className="text-xs font-semibold text-[#a1a1a1] shrink-0">Dataset scope:</span>
          <Select
            value={selectedDatasetId || ""}
            onChange={(value) => selectDataset(value || null)}
            options={datasets.map((d) => ({
              value: d.id,
              label: d.name,
              hint: `${d.file_count || 0} files`,
            }))}
            placeholder="No datasets"
            ariaLabel="Dataset scope"
            className="w-[240px] max-w-[50vw]"
          />
        </div>

        {stats && (
          <div className="text-xs font-mono text-[#707070]">
            Total derived memory: <strong className="text-[#ededed]">{stats.total_size_display}</strong>
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
