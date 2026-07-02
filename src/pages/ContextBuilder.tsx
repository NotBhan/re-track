import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { InputParameters } from "@/components/context-builder/InputParameters";
import { PipelineVisualization } from "@/components/context-builder/PipelineVisualization";
import { OutputPanel } from "@/components/context-builder/OutputPanel";
import { useContextStore } from "@/stores/context-store";
import { useRepositoryStore } from "@/stores/repository-store";

export default function ContextBuilder() {
  const [searchParams] = useSearchParams();
  const repoId = searchParams.get("repo");
  const setSelectedRepoById = useContextStore((s) => s.setSelectedRepoById);

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
    <>
      <TopBar title="Context Builder" />
      <main className="flex-1 flex overflow-hidden p-6 gap-6">
        <InputParameters repoPreselected={!!repoId} />
        <PipelineVisualization />
        <OutputPanel />
      </main>
    </>
  );
}
