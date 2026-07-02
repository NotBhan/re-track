import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Folder, MoreVertical, ExternalLink, Sparkles, RefreshCw, Trash2 } from "lucide-react";
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
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { indexRepo, removeRepo } = useRepositoryStore();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
        setConfirmDelete(false);
      }
    }
    if (menuOpen) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  const statusColor = {
    indexed: "bg-secondary text-on-secondary",
    scanning: "bg-tertiary text-on-tertiary",
    indexing: "bg-tertiary text-on-tertiary",
    registered: "bg-outline text-on-surface-variant",
    error: "bg-error text-on-error",
  }[repo.status] ?? "bg-outline text-on-surface-variant";

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
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3
              className={cn(
                "text-[20px] leading-[28px] font-medium flex items-center gap-2 truncate",
                selected ? "text-primary" : "text-on-surface"
              )}
            >
              <Folder className="w-5 h-5 flex-shrink-0" />
              <span className="truncate">{repo.name}</span>
            </h3>
            <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded capitalize flex-shrink-0", statusColor)}>
              {repo.status}
            </span>
          </div>
          <p className="font-mono text-[13px] leading-[20px] text-on-surface-variant mt-1 truncate">
            {repo.local_path}
          </p>
        </div>

        {/* Overflow menu */}
        <div ref={menuRef} className="relative flex-shrink-0 ml-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen(!menuOpen);
            }}
            className="p-1 rounded hover:bg-surface-variant transition-colors text-on-surface-variant hover:text-on-surface"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-surface-container-low border border-outline-variant rounded-lg shadow-lg z-50 py-1 overflow-hidden">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(false);
                  navigate(`/knowledge/${repo.id}`);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-on-surface hover:bg-surface-variant transition-colors"
              >
                <ExternalLink className="w-4 h-4 text-on-surface-variant" />
                View Knowledge
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(false);
                  navigate(`/context-builder?repo=${repo.id}`);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-on-surface hover:bg-surface-variant transition-colors"
              >
                <Sparkles className="w-4 h-4 text-on-surface-variant" />
                Generate Context
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpen(false);
                  indexRepo(repo.id);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-on-surface hover:bg-surface-variant transition-colors"
              >
                <RefreshCw className="w-4 h-4 text-on-surface-variant" />
                Re-index
              </button>
              <div className="border-t border-outline-variant my-1" />
              {confirmDelete ? (
                <div className="px-3 py-2">
                  <p className="text-[12px] text-on-surface-variant mb-2">Delete this repo?</p>
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeRepo(repo.id);
                        setMenuOpen(false);
                        setConfirmDelete(false);
                      }}
                      className="flex-1 bg-error text-on-error text-[12px] font-medium rounded px-2 py-1 hover:bg-error/80 transition-colors"
                    >
                      Confirm
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmDelete(false);
                      }}
                      className="flex-1 bg-surface-variant text-on-surface text-[12px] font-medium rounded px-2 py-1 hover:bg-surface-bright transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmDelete(true);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-error hover:bg-error-container transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Languages */}
      {repo.languages.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {repo.languages.slice(0, 5).map((lang) => (
            <LanguageBadge key={lang} language={lang} />
          ))}
          {repo.languages.length > 5 && (
            <span className="text-[10px] text-on-surface-variant px-1 py-1">+{repo.languages.length - 5}</span>
          )}
        </div>
      )}

      {/* Summary */}
      {repo.summary && (
        <p className="text-[13px] leading-[18px] text-on-surface-variant line-clamp-2 mb-4">
          {repo.summary}
        </p>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
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
            Source
          </p>
          <p className="text-[14px] leading-[20px] text-on-surface capitalize">
            {repo.source_type}
          </p>
        </div>
      </div>
    </div>
  );
}
