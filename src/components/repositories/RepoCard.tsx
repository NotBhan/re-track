import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  MoreVertical,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Trash2,
  GitBranch,
  ArrowUpRight,
} from "lucide-react";
import { LanguageBadge } from "./LanguageBadge";
import { cn } from "@/lib/utils";
import type { Repository } from "@/types/repository";
import { useRepositoryStore } from "@/stores/repository-store";
import { Badge } from "@/components/ui/badge";
import { ReindexModal } from "./ReindexModal";

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
  const [showReindexModal, setShowReindexModal] = useState(false);
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

  return (
    <div
      onClick={onSelect}
      className={cn(
        "rounded-xl p-6 transition-all cursor-pointer group relative bg-[#0a0a0a] border",
        selected
          ? "border-white shadow-[0_0_20px_rgba(255,255,255,0.06)] bg-[#0e0e0e]"
          : "border-[#262626] hover:border-[#404040] hover:bg-[#0d0d0d]"
      )}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1 min-w-0 pr-3">
          <div className="flex items-center gap-2.5 mb-1.5">
            <div className="w-8 h-8 rounded-lg bg-black border border-[#2a2a2a] flex items-center justify-center text-white shrink-0 shadow-sm">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <h3 className="text-base font-bold text-white tracking-tight truncate flex items-center gap-2">
              <span>{repo.name}</span>
            </h3>
            <Badge
              variant="outline"
              className={cn(
                "text-[10px] font-mono uppercase px-2 py-0.5 border shrink-0",
                repo.status === "indexed"
                  ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                  : repo.status === "error"
                  ? "border-red-500/30 text-red-400 bg-red-500/10"
                  : "border-[#333333] text-neutral-400 bg-black"
              )}
            >
              {repo.status}
            </Badge>
          </div>

          <p className="font-mono text-xs text-neutral-400 truncate pl-1">
            {repo.local_path}
          </p>
        </div>

        {/* Action button & Overflow menu */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/studio?repo=${repo.id}`);
            }}
            className="px-3 py-1.5 rounded-lg bg-white text-black text-xs font-semibold hover:bg-neutral-200 transition-colors flex items-center gap-1.5 font-mono shadow-sm"
          >
            <span>Studio</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>

          <div ref={menuRef} className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(!menuOpen);
              }}
              className="p-1.5 rounded-lg border border-[#262626] bg-black text-neutral-400 hover:text-white hover:border-[#404040] transition-colors"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-52 bg-black border border-[#2e2e2e] rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    navigate(`/knowledge/${repo.id}`);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-neutral-300 hover:text-white hover:bg-[#1a1a1a] transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-neutral-400" />
                  View Knowledge
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    navigate(`/studio?repo=${repo.id}`);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-neutral-300 hover:text-white hover:bg-[#1a1a1a] transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5 text-neutral-400" />
                  Launch Context Studio
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    indexRepo(repo.id);
                    setShowReindexModal(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-neutral-300 hover:text-white hover:bg-[#1a1a1a] transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-neutral-400" />
                  Re-index
                </button>
                <div className="border-t border-[#262626] my-1" />
                {confirmDelete ? (
                  <div className="px-3.5 py-2.5 bg-[#141414]">
                    <p className="text-xs text-neutral-300 mb-2 font-mono">Confirm deletion?</p>
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeRepo(repo.id);
                          setMenuOpen(false);
                          setConfirmDelete(false);
                        }}
                        className="flex-1 bg-red-600 text-white text-xs font-semibold rounded-md px-2 py-1.5 hover:bg-red-700 transition-colors"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmDelete(false);
                        }}
                        className="flex-1 bg-[#222222] text-neutral-300 text-xs font-medium rounded-md px-2 py-1.5 hover:text-white transition-colors"
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
                    className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete Repository
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Languages */}
      {repo.languages.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4 pl-1">
          {repo.languages.slice(0, 5).map((lang) => (
            <LanguageBadge key={lang} language={lang} />
          ))}
          {repo.languages.length > 5 && (
            <span className="text-xs font-mono text-neutral-400 px-1 py-0.5">+{repo.languages.length - 5}</span>
          )}
        </div>
      )}

      {/* Summary */}
      {repo.summary && (
        <p className="text-xs text-neutral-300 line-clamp-2 mb-5 pl-1 leading-relaxed">
          {repo.summary}
        </p>
      )}

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-black border border-[#222222]">
        <div>
          <span className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider block mb-0.5">
            Files
          </span>
          <span className="text-sm font-bold text-white font-mono">
            {repo.file_count.toLocaleString()}
          </span>
        </div>
        <div>
          <span className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider block mb-0.5">
            Size
          </span>
          <span className="text-sm font-bold text-white font-mono">
            {formatBytes(repo.size_bytes)}
          </span>
        </div>
        <div>
          <span className="text-[11px] font-mono text-neutral-400 uppercase tracking-wider block mb-0.5">
            Source
          </span>
          <span className="text-sm font-bold text-white font-mono capitalize">
            {repo.source_type}
          </span>
        </div>
      </div>

      {/* Live Re-index Progress Modal */}
      <ReindexModal
        repoId={repo.id}
        open={showReindexModal}
        onOpenChange={setShowReindexModal}
      />
    </div>
  );
}
