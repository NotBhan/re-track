import { useState, useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { StructuralTreePane } from "@/components/context-builder/StructuralTreePane";
import { PromptInterceptorPane } from "@/components/context-builder/PromptInterceptorPane";
import { ContextPackagePane } from "@/components/context-builder/ContextPackagePane";
import { getAgentContext, AgentContextResponse } from "@/lib/api";
import { useRepositoryStore } from "@/stores/repository-store";

export default function Dashboard() {
  const [taskPrompt, setTaskPrompt] = useState(
    "Find where Settings are initialized and how LLM providers are configured"
  );
  const [maxTokens, setMaxTokens] = useState(8000);
  const [loading, setLoading] = useState(false);
  const [agentResponse, setAgentResponse] = useState<AgentContextResponse | null>(null);
  const [selectedSubfolder, setSelectedSubfolder] = useState("backend/app/services");

  const repositories = useRepositoryStore((s) => s.repositories);
  const fetchRepositories = useRepositoryStore((s) => s.fetchRepositories);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  const activeRepo = repositories[0] || {
    name: "andes-context",
    local_path: "/home/chandrabhan/Documents/Personal Projects/andes-context",
  };

  const handleExecuteContextPull = async () => {
    if (!taskPrompt.trim()) return;
    setLoading(true);
    try {
      const res = await getAgentContext({
        task_prompt: taskPrompt,
        repository_path: activeRepo.local_path,
        max_tokens: maxTokens,
        include_structural_graph: true,
      });
      setAgentResponse(res);
    } catch (err) {
      console.error("Context interception failed", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-background">
      <TopBar title="RE:Track | Context Studio" />
      
      {/* Responsive 3-Pane Main Studio Workspace */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden p-4 gap-4">
        {/* Left Pane: Structural Tree */}
        <StructuralTreePane
          repositoryName={activeRepo.name}
          selectedPath={selectedSubfolder}
          onSelectSubfolder={setSelectedSubfolder}
        />

        {/* Center Pane: Agent Prompt Interceptor */}
        <PromptInterceptorPane
          taskPrompt={taskPrompt}
          onPromptChange={setTaskPrompt}
          onExecuteContextPull={handleExecuteContextPull}
          loading={loading}
          maxTokens={maxTokens}
          onMaxTokensChange={setMaxTokens}
          agentResponse={agentResponse}
        />

        {/* Right Pane: Context Package Delivery */}
        <ContextPackagePane
          agentResponse={agentResponse}
          loading={loading}
        />
      </main>
    </div>
  );
}
