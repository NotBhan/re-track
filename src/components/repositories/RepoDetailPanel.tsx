import { useNavigate } from "react-router-dom";
import {
  X,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Trash2,
  FolderGit2,
  Code,
  Layers,
  ArrowRightLeft,
  Box,
  Package,
  FileText,
} from "lucide-react";
import { useRepositoryStore } from "@/stores/repository-store";
import { StatusDot } from "@/components/shared/StatusDot";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function Section({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children: React.ReactNode }) {
  return (
    <section>
      <h4 className="flex items-center gap-1.5 text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
        <Icon className="w-3.5 h-3.5" />
        {title}
      </h4>
      <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant/50">
        {children}
      </div>
    </section>
  );
}

function TagList({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span
          key={item}
          className="text-[12px] leading-[16px] text-on-surface bg-surface-variant px-2 py-1 rounded"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function FileList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1">
      {items.map((item) => (
        <li key={item} className="text-[13px] leading-[20px] font-mono text-on-surface-variant flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-primary flex-shrink-0" />
          {item}
        </li>
      ))}
    </ul>
  );
}

export function RepoDetailPanel() {
  const { selected, select, indexRepo, removeRepo } = useRepositoryStore();
  const navigate = useNavigate();

  if (!selected) {
    return (
      <aside className="w-[400px] flex-shrink-0 bg-surface-container rounded-xl border border-outline-variant flex items-center justify-center h-full">
        <p className="text-on-surface-variant text-[14px] leading-[20px]">
          Select a repository to view details
        </p>
      </aside>
    );
  }

  const statusDot = selected.status === "indexed" ? "online" : selected.status === "error" ? "error" : "idle";
  const statusLabel = {
    indexed: "Indexed",
    scanning: "Scanning",
    indexing: "Indexing",
    registered: "Registered",
    error: "Error",
  }[selected.status] ?? selected.status;

  return (
    <aside className="w-[400px] flex-shrink-0 bg-surface-container rounded-xl flex flex-col overflow-hidden h-full">
      {/* Header */}
      <div className="p-5 border-b border-outline-variant bg-surface-container-low">
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1 min-w-0">
            <h3 className="text-[20px] leading-[28px] font-medium text-on-surface truncate">
              {selected.name}
            </h3>
            <p className="font-mono text-[13px] leading-[20px] text-on-surface-variant mt-0.5 truncate">
              {selected.local_path}
            </p>
          </div>
          <button
            onClick={() => select(null)}
            className="text-on-surface-variant hover:text-on-surface ml-2 flex-shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex items-center gap-2 font-mono text-[13px] leading-[20px]">
          <StatusDot status={statusDot} size="sm" />
          <span className="text-on-surface-variant">{statusLabel}</span>
          <span className="text-outline-variant">|</span>
          <span className="text-on-surface-variant capitalize">{selected.source_type}</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Summary */}
        {selected.summary && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Summary
            </h4>
            <p className="text-[13px] leading-[20px] text-on-surface-variant">
              {selected.summary}
            </p>
          </section>
        )}

        {/* Languages */}
        {selected.languages.length > 0 && (
          <Section icon={Code} title="Languages">
            <TagList items={selected.languages} />
          </Section>
        )}

        {/* Frameworks */}
        {selected.frameworks.length > 0 && (
          <Section icon={Layers} title="Frameworks">
            <TagList items={selected.frameworks} />
          </Section>
        )}

        {/* Architecture */}
        {selected.architecture && (
          <Section icon={ArrowRightLeft} title="Architecture">
            <p className="text-[13px] leading-[20px] text-on-surface">
              {selected.architecture}
            </p>
          </Section>
        )}

        {/* Entry Points */}
        {selected.entry_points.length > 0 && (
          <Section icon={FileText} title="Entry Points">
            <FileList items={selected.entry_points} />
          </Section>
        )}

        {/* Components */}
        {selected.components.length > 0 && (
          <Section icon={Box} title="Components">
            <FileList items={selected.components} />
          </Section>
        )}

        {/* Dependencies */}
        {selected.dependencies.length > 0 && (
          <Section icon={Package} title="Dependencies">
            <TagList items={selected.dependencies} />
          </Section>
        )}

        {/* File Statistics */}
        <section>
          <h4 className="flex items-center gap-1.5 text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
            <FolderGit2 className="w-3.5 h-3.5" />
            File Statistics
          </h4>
          <div className="bg-surface-container-lowest p-3 rounded border border-outline-variant/50 space-y-2">
            <div className="flex justify-between">
              <span className="text-[13px] leading-[20px] text-on-surface-variant">Files</span>
              <span className="text-[13px] leading-[20px] text-on-surface">{selected.file_count.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[13px] leading-[20px] text-on-surface-variant">Size</span>
              <span className="text-[13px] leading-[20px] text-on-surface">{formatBytes(selected.size_bytes)}</span>
            </div>
            {selected.indexed_at && (
              <div className="flex justify-between">
                <span className="text-[13px] leading-[20px] text-on-surface-variant">Last Indexed</span>
                <span className="text-[13px] leading-[20px] text-on-surface">
                  {new Date(selected.indexed_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </section>

        {/* Error */}
        {selected.error_message && (
          <section>
            <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
              Error
            </h4>
            <p className="text-[13px] leading-[20px] text-error bg-error-container p-3 rounded">
              {selected.error_message}
            </p>
          </section>
        )}

        {/* Actions */}
        <section className="pt-2">
          <h4 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mb-2 uppercase tracking-wider">
            Actions
          </h4>
          <div className="space-y-2">
            <button
              onClick={() => navigate(`/knowledge/${selected.id}`)}
              className="w-full flex items-center gap-2 bg-primary/10 hover:bg-primary/20 text-primary text-[13px] font-medium rounded-lg px-3 py-2 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              View Knowledge
            </button>
            <button
              onClick={() => navigate(`/context-builder?repo=${selected.id}`)}
              className="w-full flex items-center gap-2 bg-tertiary/10 hover:bg-tertiary/20 text-tertiary text-[13px] font-medium rounded-lg px-3 py-2 transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              Generate Context
            </button>
            <div className="flex gap-2">
              <button
                onClick={() => indexRepo(selected.id)}
                className="flex-1 flex items-center justify-center gap-1.5 bg-surface-variant hover:bg-surface-bright text-on-surface text-[12px] font-medium rounded-lg px-3 py-2 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Re-index
              </button>
              <button
                onClick={() => {
                  if (confirm("Delete this repository?")) {
                    removeRepo(selected.id);
                    select(null);
                  }
                }}
                className="flex-1 flex items-center justify-center gap-1.5 bg-error/10 hover:bg-error/20 text-error text-[12px] font-medium rounded-lg px-3 py-2 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
            </div>
          </div>
        </section>
      </div>
    </aside>
  );
}
