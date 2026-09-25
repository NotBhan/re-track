import React from "react";
import type { MemoryDataItem } from "../../types/api";
import { FileText, Hash } from "lucide-react";
import { formatBytes } from "../../lib/utils";
import { Badge } from "../../components/Badge";

interface IngestedFilesViewProps {
  items: MemoryDataItem[];
  loading?: boolean;
}

export const IngestedFilesView: React.FC<IngestedFilesViewProps> = ({ items, loading }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-xs text-[#a1a1a1]">
        Loading ingested records...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="p-8 text-center border border-[#262626] rounded-lg text-[#a1a1a1] text-xs">
        No documents currently recorded for this dataset.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-12 px-3 py-2 text-[11px] font-semibold text-[#a1a1a1] uppercase tracking-wider border-b border-[#262626]">
        <div className="col-span-5">Document Name</div>
        <div className="col-span-2">Type</div>
        <div className="col-span-2">Size</div>
        <div className="col-span-3">Content Hash</div>
      </div>

      <div className="flex flex-col gap-1 max-h-[480px] overflow-y-auto pr-1">
        {items.map((item) => (
          <div
            key={item.id}
            className="grid grid-cols-12 items-center px-3 py-2.5 rounded-lg bg-[#0a0a0a] border border-[#262626] hover:bg-[#121212] text-xs transition-colors"
          >
            <div className="col-span-5 flex items-center gap-2 truncate font-mono text-[#ededed]">
              <FileText className="w-3.5 h-3.5 text-[#a1a1a1] shrink-0" />
              <span className="truncate">{item.name}</span>
            </div>

            <div className="col-span-2">
              <Badge variant="default" size="sm">
                {item.extension || "text"}
              </Badge>
            </div>

            <div className="col-span-2 text-[#a1a1a1] font-mono">
              {formatBytes(item.data_size || 0)}
            </div>

            <div className="col-span-3 flex items-center gap-1.5 text-[#707070] font-mono text-[11px] truncate">
              <Hash className="w-3 h-3 shrink-0" />
              <span className="truncate">{item.content_hash || item.id}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
