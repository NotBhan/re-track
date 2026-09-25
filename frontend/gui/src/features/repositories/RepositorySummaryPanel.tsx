import React from "react";
import type { Repository } from "../../types/api";
import { Badge } from "../../components/Badge";
import { formatBytes, formatDate, formatNumber } from "../../lib/utils";

interface RepositorySummaryPanelProps {
  repository: Repository;
}

interface SummaryRowProps {
  label: string;
  children: React.ReactNode;
  mono?: boolean;
}

const SummaryRow: React.FC<SummaryRowProps> = ({ label, children, mono }) => (
  <div className="flex items-start justify-between gap-4 py-1.5">
    <dt className="text-[11px] text-[#707070] shrink-0 pt-px">{label}</dt>
    <dd
      className={
        mono
          ? "text-[11px] font-mono text-[#a1a1a1] text-right break-all min-w-0"
          : "text-xs text-[#ededed] text-right min-w-0"
      }
    >
      {children}
    </dd>
  </div>
);

export const RepositorySummaryPanel: React.FC<RepositorySummaryPanelProps> = ({ repository }) => {
  const isGithub = repository.source_type === "github";
  const source = isGithub
    ? repository.source_url || "Remote repository"
    : repository.local_path || "Local directory";

  return (
    <div className="flex flex-col gap-4">
      <dl className="divide-y divide-[#1f1f1f]">
        <SummaryRow label="Source" mono>
          {source}
        </SummaryRow>
        <SummaryRow label="Type">
          {isGithub ? "GitHub / remote" : "Local directory"}
        </SummaryRow>
        <SummaryRow label="Branch" mono>
          {repository.branch || "—"}
        </SummaryRow>
        <SummaryRow label="Commit" mono>
          {repository.commit_hash ? repository.commit_hash.slice(0, 12) : "—"}
        </SummaryRow>
        <SummaryRow label="Source files">
          <span className="font-mono">{formatNumber(repository.file_count || 0)}</span>
        </SummaryRow>
        <SummaryRow label="Size">
          <span className="font-mono">{formatBytes(repository.size_bytes || 0)}</span>
        </SummaryRow>
        <SummaryRow label="Index state">
          <span className="inline-flex items-center gap-2">
            <Badge variant={repository.status === "indexed" ? "success" : "default"}>
              {repository.status || "registered"}
            </Badge>
          </span>
        </SummaryRow>
        <SummaryRow label="Last indexed">
          <span className="font-mono">{formatDate(repository.indexed_at)}</span>
        </SummaryRow>
        <SummaryRow label="Call graph">
          <span className="font-mono">
            {(repository.call_graph_nodes?.length || 0)} nodes ·{" "}
            {(repository.call_graph_edges?.length || 0)} edges
          </span>
        </SummaryRow>
        <SummaryRow label="Auto-update">Not available in this backend</SummaryRow>
      </dl>

      <div className="flex flex-col gap-2">
        <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
          Languages
        </span>
        {repository.languages && repository.languages.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {repository.languages.map((lang) => (
              <Badge key={lang} variant="default">
                {lang}
              </Badge>
            ))}
          </div>
        ) : (
          <span className="text-[11px] text-[#707070]">No language data detected</span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
          Frameworks
        </span>
        {repository.frameworks && repository.frameworks.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {repository.frameworks.map((fw) => (
              <Badge key={fw} variant="default">
                {fw}
              </Badge>
            ))}
          </div>
        ) : (
          <span className="text-[11px] text-[#707070]">No framework markers detected</span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
          Entry points
        </span>
        {repository.entry_points && repository.entry_points.length > 0 ? (
          <div className="flex flex-col gap-1">
            {repository.entry_points.map((ep) => (
              <span key={ep} className="text-[11px] font-mono text-[#a1a1a1] truncate" title={ep}>
                {ep}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-[11px] text-[#707070]">No entry points identified</span>
        )}
      </div>

      {repository.components && repository.components.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
            Top-level components
          </span>
          <div className="flex flex-wrap gap-1.5">
            {repository.components.map((component) => (
              <Badge key={component} variant="muted">
                {component}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {repository.summary && (
        <div className="flex flex-col gap-2">
          <span className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
            Summary
          </span>
          <p className="text-xs text-[#a1a1a1] leading-relaxed">{repository.summary}</p>
        </div>
      )}
    </div>
  );
};
