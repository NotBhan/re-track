import { X } from "lucide-react";
import { useRepositoryStore } from "@/stores/repository-store";
import { StatusDot } from "@/components/shared/StatusDot";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export function RepoDetailPanel() {
  const { selected, select } = useRepositoryStore();

  if (!selected) {
    return (
      <aside className="w-[400px] flex-shrink-0 bg-surface-container rounded-xl border border-outline-variant flex items-center justify-center h-full">
        <p className="text-on-surface-variant text-[14px] leading-[20px]">
          Select a repository to view details
        </p>
      </aside>
    );
  }

  return (
    <aside className="w-[400px] flex-shrink-0 bg-surface-container rounded-xl flex flex-col overflow-hidden h-full">
      {/* Header */}
      <div className="p-5 border-b border-outline-variant bg-surface-container-low">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-[20px] leading-[28px] font-medium text-on-surface">
            {selected.name}
          </h3>
          <button
            onClick={() => select(null)}
            className="text-on-surface-variant hover:text-on-surface"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex items-center gap-2 font-mono text-[13px] leading-[20px] text-primary">
          <StatusDot
            status={selected.status === "indexed" ? "online" : selected.status === "error" ? "error" : "idle"}
            size="sm"
          />
          {selected.status === "indexed" ? "Index Healthy" : selected.status}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Basic Info */}
        <section>
          <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
            Details
          </h4>
          <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant/50 space-y-2">
            <div className="flex justify-between">
              <span className="text-[14px] leading-[20px] text-on-surface-variant">Source</span>
              <span className="text-[14px] leading-[20px] text-on-surface">{selected.source_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[14px] leading-[20px] text-on-surface-variant">Files</span>
              <span className="text-[14px] leading-[20px] text-on-surface">{selected.file_count.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[14px] leading-[20px] text-on-surface-variant">Size</span>
              <span className="text-[14px] leading-[20px] text-on-surface">{formatBytes(selected.size_bytes)}</span>
            </div>
            {selected.indexed_at && (
              <div className="flex justify-between">
                <span className="text-[14px] leading-[20px] text-on-surface-variant">Last Indexed</span>
                <span className="text-[14px] leading-[20px] text-on-surface">
                  {new Date(selected.indexed_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </section>

        {/* Languages */}
        {selected.languages.length > 0 && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Languages
            </h4>
            <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant/50">
              <div className="flex flex-wrap gap-2">
                {selected.languages.map((lang) => (
                  <span
                    key={lang}
                    className="text-[13px] leading-[20px] text-on-surface bg-surface-variant px-2 py-1 rounded"
                  >
                    {lang}
                  </span>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Frameworks */}
        {selected.frameworks.length > 0 && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Frameworks
            </h4>
            <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant/50">
              <div className="flex flex-wrap gap-2">
                {selected.frameworks.map((fw) => (
                  <span
                    key={fw}
                    className="text-[13px] leading-[20px] text-on-surface bg-surface-variant px-2 py-1 rounded"
                  >
                    {fw}
                  </span>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Error */}
        {selected.error_message && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Error
            </h4>
            <p className="text-[14px] leading-[20px] text-error bg-error-container p-3 rounded">
              {selected.error_message}
            </p>
          </section>
        )}
      </div>
    </aside>
  );
}
