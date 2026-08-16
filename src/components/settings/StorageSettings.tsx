import { FolderOpen } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";

export function StorageSettings() {
  const status = useHealthStore((s) => s.status);
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface mb-2">
          Storage &amp; Cache
        </h2>
        <p className="text-[14px] leading-[20px] text-on-surface-variant">
          Manage where RE:Track stores local data.
        </p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
          <div className="md:w-1/3">
            <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
              Persistent Path
            </label>
          </div>
          <div className="md:w-2/3 flex gap-2">
            <input
              type="text"
              readOnly
              defaultValue={status?.data_root ?? "~/.retrack/data"}
              className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant text-outline font-mono text-[13px] leading-[20px] cursor-not-allowed"
            />
            <button className="px-3 h-10 bg-surface-container hover:bg-surface-bright border border-outline-variant rounded-md text-on-surface transition-colors">
              <FolderOpen className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
