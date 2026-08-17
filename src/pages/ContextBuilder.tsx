import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { ContextPipelineInputs } from "@/components/context-builder/ContextPipelineInputs";
import { ContextPipelineVisualization } from "@/components/context-builder/ContextPipelineVisualization";
import { ContextPackageOutputPanel } from "@/components/context-builder/ContextPackageOutputPanel";
import { useContextStore } from "@/stores/context-store";
import { useRepositoryStore } from "@/stores/repository-store";
import { Sliders, GitMerge, FileText } from "lucide-react";

export default function ContextBuilder() {
  const [searchParams] = useSearchParams();
  const repoId = searchParams.get("repo");
  const setSelectedRepoById = useContextStore((s) => s.setSelectedRepoById);
  const [activeMobileTab, setActiveMobileTab] = useState<"input" | "pipeline" | "output">("input");

  useEffect(() => {
    if (repoId) {
      setSelectedRepoById(repoId);
    }
  }, [repoId, setSelectedRepoById]);

  const repositories = useRepositoryStore((s) => s.repositories);
  const fetchRepositories = useRepositoryStore((s) => s.fetchRepositories);

  useEffect(() => {
    if (repoId && repositories.length === 0) {
      fetchRepositories();
    }
  }, [repoId, repositories.length, fetchRepositories]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased">
      <TopBar title="RE:Track | Context Builder" subtitle="Multi-Stage Pipeline" />

      {/* Mobile Segmented Tab Switcher (< lg screens) */}
      <div className="lg:hidden px-4 pt-3 pb-1 border-b border-[#222222] bg-[#080808]">
        <div className="grid grid-cols-3 gap-1 bg-[#121212] p-1 rounded-lg border border-[#262626]">
          <button
            onClick={() => setActiveMobileTab("input")}
            className={`py-1.5 px-2 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeMobileTab === "input"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>1. Inputs</span>
          </button>

          <button
            onClick={() => setActiveMobileTab("pipeline")}
            className={`py-1.5 px-2 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeMobileTab === "pipeline"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <GitMerge className="w-3.5 h-3.5" />
            <span>2. Pipeline</span>
          </button>

          <button
            onClick={() => setActiveMobileTab("output")}
            className={`py-1.5 px-2 text-xs font-mono font-medium rounded-md transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
              activeMobileTab === "output"
                ? "bg-white text-black font-semibold shadow-sm"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>3. Output</span>
          </button>
        </div>
      </div>

      {/* Main Responsive Grid/Flex Body */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden p-4 sm:p-6 gap-6 max-w-[1800px] w-full mx-auto">
        <div
          className={`flex-1 h-full overflow-hidden ${
            activeMobileTab !== "input" ? "hidden lg:flex" : "flex"
          }`}
        >
          <ContextPipelineInputs repoPreselected={!!repoId} />
        </div>

        <div
          className={`flex-1 h-full overflow-hidden ${
            activeMobileTab !== "pipeline" ? "hidden lg:flex" : "flex"
          }`}
        >
          <ContextPipelineVisualization />
        </div>

        <div
          className={`flex-1 h-full overflow-hidden ${
            activeMobileTab !== "output" ? "hidden lg:flex" : "flex"
          }`}
        >
          <ContextPackageOutputPanel />
        </div>
      </main>
    </div>
  );
}
