import { useState, useMemo } from "react";
import {
  X,
  FileCode,
  Search,
  HardDrive,
  RefreshCw,
  FolderOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useMemoryStore } from "@/stores/memory-store";

interface DatasetItemsModalProps {
  datasetId: string;
  datasetName: string;
  isOpen: boolean;
  onClose: () => void;
}

export function DatasetItemsModal({
  datasetId,
  datasetName,
  isOpen,
  onClose,
}: DatasetItemsModalProps) {
  const { selectedDatasetItems, loadingItems } = useMemoryStore();
  const [search, setSearch] = useState("");

  const filteredItems = useMemo(() => {
    if (!search.trim()) return selectedDatasetItems;
    const q = search.toLowerCase();
    return selectedDatasetItems.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.mime_type.toLowerCase().includes(q) ||
        item.content_hash.toLowerCase().includes(q)
    );
  }, [selectedDatasetItems, search]);

  if (!isOpen) return null;

  const totalBytes = selectedDatasetItems.reduce((acc, it) => acc + (it.data_size || 0), 0);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-[#0a0a0a] border border-[#222222] rounded-xl w-full max-w-3xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden font-mono">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#1a1a1a] bg-[#070707]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-white">
              <FolderOpen className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-white">{datasetName}</h3>
                <Badge variant="outline" className="text-[10px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                  {selectedDatasetItems.length} Files
                </Badge>
              </div>
              <p className="text-[11px] text-neutral-500 mt-0.5">
                Ingested documents & raw memory chunks stored in Cognee
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-white p-1.5 rounded-md hover:bg-[#1f1f1f] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Action Bar */}
        <div className="p-3 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-500" />
            <Input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search stored files, hashes..."
              className="h-8 pl-8 text-xs bg-black border-[#222222] text-white placeholder:text-neutral-500 font-mono rounded"
            />
          </div>

          <div className="flex items-center gap-3 text-xs text-neutral-400 font-mono">
            <div className="flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-neutral-500" />
              <span>{formatSize(totalBytes)}</span>
            </div>
          </div>
        </div>

        {/* Content List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {loadingItems ? (
            <div className="flex flex-col items-center justify-center py-16 text-neutral-500 gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-neutral-400" />
              <span className="text-xs">Loading stored data items...</span>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-neutral-500">
              <FileCode className="w-8 h-8 mb-2 opacity-30" />
              <div className="text-xs font-semibold text-neutral-400">No Data Items Found</div>
              <p className="text-[11px] text-neutral-600 mt-1 max-w-xs">
                {search ? "No files match your search query." : "No files stored in this dataset partition."}
              </p>
            </div>
          ) : (
            <div className="space-y-1.5">
              {filteredItems.map((item) => (
                <div
                  key={item.id}
                  className="p-2.5 rounded-lg bg-[#050505] border border-[#1a1a1a] hover:border-[#333333] transition-colors flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <FileCode className="w-4 h-4 text-neutral-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-white font-medium truncate" title={item.name}>
                        {item.name}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-neutral-500 mt-0.5 font-mono">
                        <span>{item.mime_type}</span>
                        {item.content_hash && (
                          <>
                            <span>•</span>
                            <span className="truncate max-w-[120px]" title={item.content_hash}>
                              #{item.content_hash.slice(0, 10)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 font-mono text-[11px]">
                    <span className="text-neutral-400">{formatSize(item.data_size)}</span>
                    <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/20 text-emerald-400 bg-emerald-500/5">
                      Ingested
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[#1a1a1a] bg-[#070707] flex items-center justify-between text-xs text-neutral-500 font-mono">
          <span>Dataset ID: {datasetId.slice(0, 16)}...</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClose}
            className="h-7 text-xs border-[#262626] text-neutral-300 hover:text-white"
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
