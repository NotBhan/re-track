import { X, GitBranch, Database } from "lucide-react";
import { useRepositoryStore } from "@/stores/repository-store";
import { StatusDot } from "@/components/shared/StatusDot";

const archIcons: Record<string, typeof GitBranch> = {
  "git-branch": GitBranch,
  database: Database,
};

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
          <StatusDot status="online" size="sm" />
          Index Healthy
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Purpose */}
        {selected.purpose && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Purpose
            </h4>
            <p className="text-[14px] leading-[20px] text-on-surface bg-surface-container-lowest p-3 rounded border border-outline-variant/50">
              {selected.purpose}
            </p>
          </section>
        )}

        {/* Architecture */}
        {selected.architecture && selected.architecture.length > 0 && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Architecture
            </h4>
            <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant/50 space-y-2">
              {selected.architecture.map((item, i) => {
                const Icon = archIcons[item.icon] || GitBranch;
                return (
                  <div key={i} className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-primary" />
                    <span className="text-[14px] leading-[20px] text-on-surface">
                      {item.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Key Components */}
        {selected.keyComponents && selected.keyComponents.length > 0 && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Key Components
            </h4>
            <ul className="space-y-2">
              {selected.keyComponents.map((comp, i) => (
                <li
                  key={i}
                  className="font-mono text-[13px] leading-[20px] text-on-surface bg-surface-variant px-2 py-1.5 rounded flex justify-between"
                >
                  <span>{comp.path}</span>
                  <span className="text-on-surface-variant">{comp.centrality}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </aside>
  );
}
