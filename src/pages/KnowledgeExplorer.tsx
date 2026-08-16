import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { useRepositoryStore } from "@/stores/repository-store";
import { ArrowLeft, BookOpen, Layers, Code, GitBranch, Terminal } from "lucide-react";

export default function KnowledgeExplorer() {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const { repositories, fetchRepositories } = useRepositoryStore();

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  const repo = repositories.find((r) => r.id === repoId);

  return (
    <>
      <TopBar>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/repositories")}
            className="p-1.5 rounded-md hover:bg-surface-variant text-on-surface-variant hover:text-on-surface transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-[16px] leading-[24px] font-semibold text-on-surface">
              Knowledge Explorer
            </h2>
            <p className="text-[12px] text-on-surface-variant font-mono">
              {repo ? repo.name : repoId}
            </p>
          </div>
        </div>
      </TopBar>

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {repo ? (
          <>
            {/* Quick Stats Grid */}
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-surface-container border border-outline-variant/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-on-surface-variant mb-2">
                  <BookOpen className="w-4 h-4 text-primary" />
                  <span className="text-[12px] font-medium uppercase tracking-wider">Indexed Files</span>
                </div>
                <div className="text-[24px] font-bold text-on-surface font-mono">
                  {repo.file_count || 0}
                </div>
              </div>

              <div className="bg-surface-container border border-outline-variant/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-on-surface-variant mb-2">
                  <Layers className="w-4 h-4 text-primary" />
                  <span className="text-[12px] font-medium uppercase tracking-wider">Repository ID</span>
                </div>
                <div className="text-[14px] font-medium text-on-surface font-mono truncate">
                  {repo.id}
                </div>
              </div>

              <div className="bg-surface-container border border-outline-variant/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-on-surface-variant mb-2">
                  <Code className="w-4 h-4 text-primary" />
                  <span className="text-[12px] font-medium uppercase tracking-wider">Status</span>
                </div>
                <div className="text-[14px] font-semibold text-primary uppercase">
                  {repo.status || "Ready"}
                </div>
              </div>

              <div className="bg-surface-container border border-outline-variant/30 rounded-lg p-4">
                <div className="flex items-center gap-2 text-on-surface-variant mb-2">
                  <GitBranch className="w-4 h-4 text-primary" />
                  <span className="text-[12px] font-medium uppercase tracking-wider">Indexed At</span>
                </div>
                <div className="text-[12px] text-on-surface font-mono">
                  {repo.indexed_at ? new Date(repo.indexed_at).toLocaleDateString() : "Never"}
                </div>
              </div>
            </div>

            {/* Architecture / Path Summary */}
            <div className="bg-surface-container border border-outline-variant/30 rounded-lg p-6 space-y-4">
              <h3 className="text-[16px] font-semibold text-on-surface flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" />
                Repository Path & Configuration
              </h3>
              <div className="bg-surface-variant/30 rounded p-3 text-[13px] font-mono text-on-surface break-all">
                {repo.local_path}
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-on-surface-variant">
            Repository not found.
          </div>
        )}
      </main>
    </>
  );
}
