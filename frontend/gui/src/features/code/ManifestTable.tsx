import React from "react";
import type { Repository } from "../../types/api";
import { Badge } from "../../components/Badge";
import { formatBytes, formatNumber } from "../../lib/utils";
import { FileCode, Layers, PlayCircle, HardDrive } from "lucide-react";

interface ManifestTableProps {
  repository: Repository;
}

export const ManifestTable: React.FC<ManifestTableProps> = ({ repository }) => {
  return (
    <div className="flex flex-col gap-4">
      {/* Top summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
            <FileCode className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Source Files</div>
            <div className="text-sm font-semibold text-slate-100 font-mono">
              {formatNumber(repository.file_count || 0)}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <HardDrive className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Disk Size</div>
            <div className="text-sm font-semibold text-slate-100 font-mono">
              {formatBytes(repository.size_bytes || 0)}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Languages</div>
            <div className="text-sm font-semibold text-slate-100">
              {repository.languages?.length || 0}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <PlayCircle className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Entry Points</div>
            <div className="text-sm font-semibold text-slate-100">
              {repository.entry_points?.length || 0}
            </div>
          </div>
        </div>
      </div>

      {/* Languages & Frameworks breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Languages */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <h5 className="text-xs font-semibold text-slate-300 mb-2.5">Languages & Technologies</h5>
          <div className="flex flex-wrap gap-1.5">
            {repository.languages && repository.languages.length > 0 ? (
              repository.languages.map((lang) => (
                <Badge key={lang} variant="accent">
                  {lang}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-slate-500 italic">No language data detected</span>
            )}
            {repository.frameworks && repository.frameworks.map((fw) => (
              <Badge key={fw} variant="default">
                {fw}
              </Badge>
            ))}
          </div>
        </div>

        {/* Entry Points */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <h5 className="text-xs font-semibold text-slate-300 mb-2.5">Detected Entry Points</h5>
          {repository.entry_points && repository.entry_points.length > 0 ? (
            <div className="flex flex-col gap-1">
              {repository.entry_points.map((ep) => (
                <div
                  key={ep}
                  className="text-xs font-mono p-1.5 rounded-md bg-white/[0.02] border border-white/[0.04] text-slate-300 truncate"
                >
                  {ep}
                </div>
              ))}
            </div>
          ) : (
            <span className="text-xs text-slate-500 italic">No entry points identified</span>
          )}
        </div>
      </div>

      {/* Repository Summary if present */}
      {repository.summary && (
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <h5 className="text-xs font-semibold text-slate-300 mb-1.5">Repository Summary</h5>
          <p className="text-xs text-slate-400 leading-relaxed">{repository.summary}</p>
        </div>
      )}
    </div>
  );
};
