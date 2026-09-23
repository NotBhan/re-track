import { FolderOpen } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";

export function StorageSettings() {
  const status = useHealthStore((s) => s.status);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white tracking-tight mb-0.5">
          Storage &amp; Cache
        </h2>
        <p className="text-xs text-neutral-500">
          Manage where RE:Track stores embeddings, graphs, and persistent metadata.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-4">
        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
          <div className="md:w-1/3">
            <label className="text-xs font-medium text-neutral-200 block">
              Data Root
            </label>
            <span className="text-xs text-neutral-500 mt-0.5 block">
              Storage root for LanceDB and Kùzu graphs.
            </span>
          </div>
          <div className="md:w-2/3 flex gap-2">
            <input
              type="text"
              readOnly
              defaultValue={status?.data_root ?? "~/.retrack/data"}
              className="w-full bg-[#050505] h-8 px-3 rounded-md border border-[#222222] text-neutral-400 font-mono text-xs cursor-default outline-none select-all"
            />
            <div className="p-2 h-8 bg-[#0a0a0a] border border-[#222222] rounded-md text-neutral-400 flex items-center justify-center">
              <FolderOpen className="w-3.5 h-3.5" />
            </div>
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-t border-[#181818] pt-4">
          <div className="md:w-1/3">
            <label className="text-xs font-medium text-neutral-200 block">
              System Root
            </label>
            <span className="text-xs text-neutral-500 mt-0.5 block">
              Storage root for Cognee system caches and manifests.
            </span>
          </div>
          <div className="md:w-2/3 flex gap-2">
            <input
              type="text"
              readOnly
              defaultValue={status?.system_root ?? "~/.retrack/system"}
              className="w-full bg-[#050505] h-8 px-3 rounded-md border border-[#222222] text-neutral-400 font-mono text-xs cursor-default outline-none select-all"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
