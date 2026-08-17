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
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
      onClick={onSelect}
      className={cn(
        "rounded-xl p-5 sm:p-6 transition-all cursor-pointer group relative bg-[#0a0a0a] border",
        selected
          ? "border-white shadow-[0_0_24px_rgba(255,255,255,0.08)] bg-[#0d0d0d]"
          : "border-[#262626] hover:border-[#404040] hover:bg-[#0c0c0c]"
      )}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1 min-w-0 pr-3">
          <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
            <div className="w-8 h-8 rounded-lg bg-black border border-[#2a2a2a] flex items-center justify-center text-white shrink-0 shadow-sm">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <h3 className="text-base font-bold text-white tracking-tight truncate">
              {repo.name}
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

            {repo.architecture && (
              <span className="text-[10px] font-mono text-neutral-400 border border-[#262626] px-1.5 py-0.5 rounded bg-black">
                {repo.architecture}
              </span>
            )}
          </div>

          <p className="font-mono text-xs text-neutral-400 truncate pl-0.5">
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
            className="px-2.5 py-1.5 rounded-lg bg-[#1a1a1a] border border-[#333] text-white hover:bg-white hover:text-black transition-all flex items-center gap-1.5 text-xs font-mono font-medium shadow-sm cursor-pointer"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
            <span className="hidden sm:inline">Context</span>
          </button>

          {/* Context Studio Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/studio?repo=${repo.id}`);
            }}
            title="Open Context Studio"
            className="px-3 py-1.5 rounded-lg bg-white text-black text-xs font-semibold hover:bg-neutral-200 transition-colors flex items-center gap-1 font-mono shadow-sm cursor-pointer"
          >
            <span>Studio</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>

          {/* More Actions Menu */}
          <div ref={menuRef} className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(!menuOpen);
              }}
              className="p-1.5 rounded-lg border border-[#262626] bg-black text-neutral-400 hover:text-white hover:border-[#404040] transition-colors cursor-pointer"
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
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-neutral-300 hover:text-white hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-neutral-400" />
                  Explore Knowledge Graph
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    setShowQuickContext(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-neutral-300 hover:text-white hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Quick Context Package
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    navigate(`/studio?repo=${repo.id}`);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-neutral-300 hover:text-white hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-neutral-400" />
                  Launch Full Studio
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(false);
                    indexRepo(repo.id);
                    setShowReindexModal(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-neutral-300 hover:text-white hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-neutral-400" />
                  Re-index Codebase
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
                        className="flex-1 bg-red-600 text-white text-xs font-semibold rounded-md px-2 py-1.5 hover:bg-red-700 transition-colors cursor-pointer"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmDelete(false);
                        }}
                        className="flex-1 bg-[#222222] text-neutral-300 text-xs font-medium rounded-md px-2 py-1.5 hover:text-white transition-colors cursor-pointer"
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
                    className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
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
        <div className="flex flex-wrap gap-1.5 mb-3.5 pl-0.5">
          {repo.languages.slice(0, 5).map((lang) => (
            <LanguageBadge key={lang} language={lang} />
          ))}
          {repo.languages.length > 5 && (
            <span className="text-xs font-mono text-neutral-400 px-1 py-0.5">
              +{repo.languages.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Summary */}
      {repo.summary && (
        <p className="text-xs text-neutral-300 line-clamp-2 mb-4 pl-0.5 leading-relaxed font-sans">
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
