import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  MoreVertical,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Trash2,
  ArrowUpRight,
  Zap,
} from "lucide-react";
import { LanguageBadge } from "./LanguageBadge";
import { cn } from "@/lib/utils";
import type { Repository } from "@/types/repository";
import { useRepositoryStore } from "@/stores/repository-store";
import { Badge } from "@/components/ui/badge";
import { ReindexModal } from "./ReindexModal";
import { QuickContextModal } from "./QuickContextModal";
import { motion } from "motion/react";

interface RepositoryCardProps {
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

export function RepositoryCard({ repo, selected, onSelect }: RepositoryCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showReindexModal, setShowReindexModal] = useState(false);
  const [showQuickContext, setShowQuickContext] = useState(false);
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
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      onClick={onSelect}
      className={cn(
        "rounded-lg p-4 transition-colors cursor-pointer group relative bg-[#0a0a0a] border",
        selected
          ? "border-neutral-400 bg-[#121212]"
          : "border-[#1e1e1e] hover:border-[#2e2e2e] hover:bg-[#0d0d0d]"
      )}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-2.5">
        <div className="flex-1 min-w-0 pr-2">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-sm font-semibold text-white tracking-tight truncate">
              {repo.name}
            </h3>
            <Badge
              variant={
                repo.status === "indexed"
                  ? "success"
                  : repo.status === "error"
                  ? "destructive"
                  : "outline"
              }
              className="text-[10px] uppercase font-mono px-1.5 py-0"
            >
              {repo.status}
            </Badge>

            {repo.architecture && (
              <span className="text-[10px] font-mono text-neutral-400 border border-[#222222] px-1 py-0 rounded bg-[#0f0f0f]">
                {repo.architecture}
              </span>
            )}
          </div>

          <p className="font-mono text-xs text-neutral-500 truncate" title={repo.local_path}>
            {repo.local_path}
          </p>
        </div>

        {/* Action buttons & Overflow menu */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Quick Context Generator Trigger */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowQuickContext(true);
            }}
            title="Quick Context Package"
            className="h-7 px-2 rounded-md bg-[#121212] border border-[#222222] text-neutral-300 hover:text-white hover:border-[#333333] transition-colors flex items-center gap-1 text-xs font-medium cursor-pointer"
          >
            <Zap className="w-3 h-3 text-amber-400 fill-amber-400" />
            <span className="hidden sm:inline">Context</span>
          </button>

          {/* Context Studio Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/studio?repo=${repo.id}`);
            }}
            title="Open Context Studio"
            className="h-7 px-2.5 rounded-md bg-white text-black text-xs font-medium hover:bg-neutral-200 transition-colors flex items-center gap-1 shadow-xs cursor-pointer"
          >
            <span>Studio</span>
            <ArrowUpRight className="w-3 h-3" />
          </button>

          {/* More Actions Menu */}
          <div ref={menuRef} className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(!menuOpen);
              }}
              title="More options"
              aria-label="More options"
              className="h-7 w-7 rounded-md border border-[#222222] bg-[#0c0c0c] text-neutral-400 hover:text-white hover:border-[#333333] flex items-center justify-center transition-colors cursor-pointer"
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-[#0a0a0a] border border-[#262626] rounded-lg shadow-xl z-50 py-1 overflow-hidden">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    navigate(`/knowledge/${repo.id}`);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-neutral-300 hover:text-white hover:bg-[#141414] transition-colors cursor-pointer"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-neutral-400" />
                  Knowledge Graph
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    setShowQuickContext(true);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-neutral-300 hover:text-white hover:bg-[#141414] transition-colors cursor-pointer"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Quick Context
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    navigate(`/studio?repo=${repo.id}`);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-neutral-300 hover:text-white hover:bg-[#141414] transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-neutral-400" />
                  Context Studio
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    indexRepo(repo.id);
                    setShowReindexModal(true);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-neutral-300 hover:text-white hover:bg-[#141414] transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-neutral-400" />
                  Re-index
                </button>
                <div className="border-t border-[#1e1e1e] my-1" />
                {confirmDelete ? (
                  <div className="px-3 py-2 bg-[#121212]">
                    <p className="text-xs text-neutral-300 mb-2">Confirm delete?</p>
                    <div className="flex gap-1.5">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeRepo(repo.id);
                          setMenuOpen(false);
                          setConfirmDelete(false);
                        }}
                        className="flex-1 bg-red-600 text-white text-xs font-medium rounded px-2 py-1 hover:bg-red-700 transition-colors cursor-pointer"
                      >
                        Delete
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmDelete(false);
                        }}
                        className="flex-1 bg-[#222222] text-neutral-300 text-xs rounded px-2 py-1 hover:text-white transition-colors cursor-pointer"
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
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-400 hover:bg-red-950/30 transition-colors cursor-pointer"
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
        <div className="flex flex-wrap gap-1 mb-2.5">
          {repo.languages.slice(0, 5).map((lang) => (
            <LanguageBadge key={lang} language={lang} />
          ))}
          {repo.languages.length > 5 && (
            <span className="text-[11px] font-mono text-neutral-500 px-1 py-0.5">
              +{repo.languages.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Summary */}
      {repo.summary && (
        <p className="text-xs text-neutral-400 line-clamp-2 mb-3 leading-relaxed">
          {repo.summary}
        </p>
      )}

      {/* Flattened Inline Stats (Quiet & Scannable) */}
      <div className="pt-2 border-t border-[#181818] flex items-center justify-between text-xs text-neutral-400 font-mono">
        <div className="flex items-center gap-2">
          <span>{repo.file_count.toLocaleString()} files</span>
          <span className="text-neutral-600">·</span>
          <span>{formatBytes(repo.size_bytes)}</span>
          <span className="text-neutral-600">·</span>
          <span className="capitalize">{repo.source_type}</span>
        </div>
      </div>

      {/* Reindex Modal */}
      <ReindexModal
        repoId={repo.id}
        open={showReindexModal}
        onOpenChange={setShowReindexModal}
      />

      {/* Quick Context Modal */}
      <QuickContextModal
        repo={repo}
        open={showQuickContext}
        onOpenChange={setShowQuickContext}
      />
    </motion.div>
  );
}
