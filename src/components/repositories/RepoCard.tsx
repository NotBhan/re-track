import { Folder, RefreshCw, Trash2 } from "lucide-react";
import { LanguageBadge } from "./LanguageBadge";
import { cn } from "@/lib/utils";
import type { RepositorySummaryInfo } from "@/lib/api";
import { useRepositoryStore } from "@/stores/repository-store";

interface RepoCardProps {
  repo: RepositorySummaryInfo;
  selected: boolean;
  onSelect: () => void;
}

export function RepoCard({ repo, selected, onSelect }: RepoCardProps) {
  const { indexRepo, removeRepo } = useRepositoryStore();

  return (
    <div
      onClick={onSelect}
      className={cn(
        "bg-surface-container rounded-xl p-5 transition-all cursor-pointer group relative overflow-hidden",
        selected
          ? "border border-primary shadow-[0_0_15px_rgba(173,198,255,0.1)]"
          : "border border-outline-variant hover:border-outline-variant hover:scale-[1.01] hover:shadow-[0_0_15px_rgba(173,198,255,0.05)]"
      )}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3
            className={cn(
              "text-[20px] leading-[28px] font-medium flex items-center gap-2",
              selected ? "text-primary" : "text-on-surface"
            )}
          >
            <Folder className="w-5 h-5" />
            {repo.name}
          </h3>
          <p className="font-mono text-[13px] leading-[20px] text-on-surface-variant mt-1">
            {repo.path}
          </p>
        </div>
        <div className="flex gap-1">
          {repo.languages.map((lang) => (
            <LanguageBadge key={lang} language={lang} />
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            Files
          </p>
          <p className="text-[14px] leading-[20px] text-on-surface">
            {repo.file_count.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            Memory Size
          </p>
          <p className="text-[14px] leading-[20px] text-on-surface">
            {repo.memory_size}
          </p>
        </div>
        <div>
          <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            Last Indexed
          </p>
          <p className="text-[14px] leading-[20px] text-on-surface">
            {repo.last_indexed}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            indexRepo(repo.path, repo.name);
          }}
          className="flex-1 bg-surface-variant hover:bg-surface-bright text-on-surface text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded py-1.5 transition-colors flex items-center justify-center gap-1"
        >
          <RefreshCw className="w-4 h-4" />
          Re-index
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            removeRepo(repo.id);
          }}
          className="bg-surface-variant hover:bg-error-container hover:text-on-error-container text-on-surface text-[12px] leading-[16px] tracking-[0.02em] font-medium rounded px-3 py-1.5 transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
