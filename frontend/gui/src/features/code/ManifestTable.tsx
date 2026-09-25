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
        <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
            <FileCode className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-[#a1a1a1] font-medium">Source Files</div>
            <div className="text-sm font-semibold text-[#ededed] font-mono">
              {formatNumber(repository.file_count || 0)}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
            <HardDrive className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-[#a1a1a1] font-medium">Disk Size</div>
            <div className="text-sm font-semibold text-[#ededed] font-mono">
              {formatBytes(repository.size_bytes || 0)}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-[#a1a1a1] font-medium">Languages</div>
            <div className="text-sm font-semibold text-[#ededed]">
              {repository.languages?.length || 0}
            </div>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
            <PlayCircle className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-[#a1a1a1] font-medium">Entry Points</div>
            <div className="text-sm font-semibold text-[#ededed]">
              {repository.entry_points?.length || 0}
            </div>
          </div>
        </div>
      </div>

      {/* Languages & Frameworks breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Languages */}
        <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626]">
          <h5 className="text-xs font-semibold text-[#a1a1a1] mb-2.5">Languages & Technologies</h5>
          <div className="flex flex-wrap gap-1.5">
            {repository.languages && repository.languages.length > 0 ? (
              repository.languages.map((lang) => (
                <Badge key={lang} variant="accent">
                  {lang}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-[#707070] italic">No language data detected</span>
            )}
            {repository.frameworks && repository.frameworks.map((fw) => (
              <Badge key={fw} variant="default">
                {fw}
              </Badge>
            ))}
          </div>
        </div>

        {/* Entry Points */}
        <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626]">
          <h5 className="text-xs font-semibold text-[#a1a1a1] mb-2.5">Detected Entry Points</h5>
          {repository.entry_points && repository.entry_points.length > 0 ? (
            <div className="flex flex-col gap-1">
              {repository.entry_points.map((ep) => (
                <div
                  key={ep}
                  className="text-xs font-mono p-1.5 rounded-md bg-[#0a0a0a] border border-[#262626] text-[#a1a1a1] truncate"
                >
                  {ep}
                </div>
              ))}
            </div>
          ) : (
            <span className="text-xs text-[#707070] italic">No entry points identified</span>
          )}
        </div>
      </div>

      {/* Repository Summary if present */}
      {repository.summary && (
        <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626]">
          <h5 className="text-xs font-semibold text-[#a1a1a1] mb-1.5">Repository Summary</h5>
          <p className="text-xs text-[#a1a1a1] leading-relaxed">{repository.summary}</p>
        </div>
      )}
    </div>
  );
};
