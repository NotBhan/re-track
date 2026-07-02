import { Folder, RefreshCw, Trash2 } from "lucide-react";
import { LanguageBadge } from "./LanguageBadge";
import { cn } from "@/lib/utils";
import type { Repository } from "@/types/repository";
import { useRepositoryStore } from "@/stores/repository-store";

interface RepoCardProps {
  repo: Repository;
  selected: boolean;
  onSelect: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
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
            {repo.local_path}
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
            Size
          </p>
          <p className="text-[14px] leading-[20px] text-on-surface">
            {formatBytes(repo.size_bytes)}
          </p>
        </div>
        <div>
          <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            Status
          </p>
          <p className="text-[14px] leading-[20px] text-on-surface">
            {repo.status}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            indexRepo(repo.id);
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
