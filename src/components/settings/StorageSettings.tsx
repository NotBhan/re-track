import { FolderOpen } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";

export function StorageSettings() {
  const status = useHealthStore((s) => s.status);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight mb-1">
          Storage &amp; Cache
        </h2>
        <p className="text-xs text-neutral-400">
          Manage where RE:Track stores embeddings, graphs, and persistent metadata.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 space-y-5 shadow-2xl">
        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
          <div className="md:w-1/3">
            <label className="text-xs font-mono font-medium text-white block">
              Data Root
            </label>
            <span className="text-[11px] text-neutral-400 mt-0.5 block">
              Storage root for LanceDB and Kùzu graphs.
            </span>
          </div>
          <div className="md:w-2/3 flex gap-2">
            <input
              type="text"
              readOnly
              defaultValue={status?.data_root ?? "~/.retrack/data"}
              className="w-full bg-[#0e0e0e] h-10 px-3 rounded-lg border border-[#262626] text-neutral-400 font-mono text-xs cursor-default outline-none select-all"
            />
            <div className="p-2.5 h-10 bg-black border border-[#262626] rounded-lg text-neutral-400 flex items-center justify-center">
              <FolderOpen className="w-4 h-4" />
            </div>
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-t border-[#1c1c1c] pt-5">
          <div className="md:w-1/3">
            <label className="text-xs font-mono font-medium text-white block">
              System Root
            </label>
            <span className="text-[11px] text-neutral-400 mt-0.5 block">
              Storage root for Cognee system caches and manifests.
            </span>
          </div>
          <div className="md:w-2/3 flex gap-2">
            <input
              type="text"
              readOnly
              defaultValue={status?.system_root ?? "~/.retrack/system"}
              className="w-full bg-[#0e0e0e] h-10 px-3 rounded-lg border border-[#262626] text-neutral-400 font-mono text-xs cursor-default outline-none select-all"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
