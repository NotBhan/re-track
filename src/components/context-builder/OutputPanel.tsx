import { useState, type ReactNode } from "react";
import { Copy, Check, Save, Download, FileText, Plus } from "lucide-react";
import { useContextStore } from "@/stores/context-store";
import { useContextPackageStore } from "@/stores/context-package-store";
import { useRepositoryStore } from "@/stores/repository-store";
import { cn } from "@/lib/utils";

export function OutputPanel() {
  const { result, loading, error, selectedRepoId } = useContextStore();
  const { savePackage, appendToPackage, fetchPackages } = useContextPackageStore();
  const repositories = useRepositoryStore((s) => s.repositories);
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [appending, setAppending] = useState(false);

  const selectedRepo = selectedRepoId
    ? repositories.find((r) => r.id === selectedRepoId)
    : null;

  const handleCopy = async () => {
    if (!result?.markdown) return;
    try {
      await navigator.clipboard.writeText(result.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  };

  const handleSave = async () => {
    if (!result) return;
    const name = prompt("Package name:");
    if (!name) return;

    setSaving(true);
    try {
      await savePackage({
        name,
        task: result.task,
        objective: result.objective,
        repository_id: selectedRepoId || "",
        repository_name: selectedRepo?.name || "",
        repository_branch: selectedRepo?.branch || "",
        repository_commit: selectedRepo?.commit_hash || "",
        markdown: result.markdown,
        section_count: result.section_count,
        token_estimate: result.token_estimate,
        retrieved_memories: result.retrieved_memories,
        deduplicated_memories: result.deduplicated_memories,
        compression_ratio: result.compression_ratio,
        total_time_ms: result.total_time_ms,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleAppend = async () => {
    if (!result) return;

    setAppending(true);
    try {
      await fetchPackages();
      const packages = useContextPackageStore.getState().packages;

      if (packages.length === 0) {
        alert("No saved packages found. Save a package first.");
        return;
      }

      const packageNames = packages.map((p, i) => `${i + 1}. ${p.name}`).join("\n");
      const selection = prompt(
        `Select a package to append to:\n${packageNames}\n\nEnter number:`
      );
      if (!selection) return;

      const index = parseInt(selection, 10) - 1;
      if (index < 0 || index >= packages.length) {
        alert("Invalid selection.");
        return;
      }

      await appendToPackage(
        packages[index].id,
        result.task,
        result.markdown,
        result.objective
      );
    } finally {
      setAppending(false);
    }
  };

  return (
    <div className="w-1/3 flex flex-col bg-surface-container rounded-xl border border-outline-variant shadow-lg shadow-black/20 flex-1 relative">
      {/* Toolbar */}
      <div className="p-3 border-b border-outline-variant bg-surface-container-high/50 flex justify-between items-center sticky top-0 z-10">
        <div className="flex gap-2">
          <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface px-2 py-1 bg-surface-container-lowest rounded border border-outline-variant">
            Markdown
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/10 rounded transition-colors"
            title="Copy Markdown"
          >
            {copied ? (
              <Check className="w-5 h-5 text-secondary" />
            ) : (
              <Copy className="w-5 h-5" />
            )}
          </button>
          <button
            onClick={handleSave}
            disabled={!result || saving}
            className="p-1.5 text-on-surface-variant hover:text-secondary hover:bg-secondary/10 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Save Package"
          >
            {saving ? (
              <div className="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
            ) : (
              <Save className="w-5 h-5" />
            )}
          </button>
          <button
            onClick={handleAppend}
            disabled={!result || appending}
            className="p-1.5 text-on-surface-variant hover:text-tertiary hover:bg-tertiary/10 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Append to Package"
          >
            {appending ? (
              <div className="animate-spin w-5 h-5 border-2 border-current border-t-transparent rounded-full" />
            ) : (
              <Plus className="w-5 h-5" />
            )}
          </button>
          <button
            className="p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-variant rounded transition-colors"
            title="Export"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-5 overflow-y-auto font-mono text-[13px] leading-[20px] text-on-surface-variant bg-[#05080f]">
        {loading ? (
          <div className="flex items-center justify-center h-full text-primary">
            <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : result ? (
          <MarkdownContent content={result.markdown} />
        ) : error ? (
          <div className="text-center py-12 text-error">{error}</div>
        ) : (
          <div className="text-center py-12 opacity-50">
            <FileText className="w-12 h-12 mx-auto mb-4" />
            <p>Enter a question and click Generate</p>
            <p className="text-sm mt-1">or press Ctrl+Enter</p>
          </div>
        )}
      </div>
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: ReactNode[] = [];
  let currentList: string[] = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul
          key={`list-${elements.length}`}
          className="list-disc pl-6 space-y-1 my-2"
        >
          {currentList.map((item, i) => (
            <li key={i} className="text-on-surface-variant">
              {renderInlineCode(item.replace(/^- /, ""))}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("# ")) {
      flushList();
      elements.push(
        <h1
          key={i}
          className="text-primary text-lg font-bold mt-6 mb-3"
        >
          {line.slice(2)}
        </h1>
      );
    } else if (line.startsWith("## ")) {
      flushList();
      elements.push(
        <h2
          key={i}
          className="text-secondary text-base font-semibold mt-5 mb-2"
        >
          {line.slice(3)}
        </h2>
      );
    } else if (line.startsWith("### ")) {
      flushList();
      elements.push(
        <h3
          key={i}
          className="text-on-surface text-sm font-medium mt-4 mb-2"
        >
          {line.slice(4)}
        </h3>
      );
    } else if (line.startsWith("- ")) {
      currentList.push(line);
    } else if (line === "---") {
      flushList();
      elements.push(
        <hr key={i} className="my-4 border-outline-variant" />
      );
    } else if (line.trim()) {
      flushList();
      elements.push(
        <p key={i} className="text-on-surface-variant my-1">
          {renderInlineCode(line)}
        </p>
      );
    } else {
      flushList();
    }
  }
  flushList();

  return <div className="opacity-70">{elements}</div>;
}

function renderInlineCode(text: string): ReactNode {
  const parts = text.split(/`([^`]+)`/);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <code
        key={i}
        className={cn(
          "px-1 py-0.5 bg-surface-container-lowest rounded text-[12px] font-mono"
        )}
      >
        {part}
      </code>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}
