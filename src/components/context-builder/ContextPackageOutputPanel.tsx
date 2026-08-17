import { useState, type ReactNode } from "react";
import { Copy, Check, Save, Download, FileText, Plus } from "lucide-react";
import { useContextStore } from "@/stores/context-store";
import { useContextPackageStore } from "@/stores/context-package-store";
import { useRepositoryStore } from "@/stores/repository-store";
import { Button } from "@/components/ui/button";

export function ContextPackageOutputPanel() {
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

  const handleDownload = () => {
    if (!result?.markdown) return;
    const blob = new Blob([result.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `context-package-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
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
    <div className="w-1/3 flex flex-col bg-[#0a0a0a] rounded-xl border border-[#262626] shadow-2xl flex-1 relative overflow-hidden">
      {/* Toolbar */}
      <div className="p-3 border-b border-[#222222] bg-[#0c0c0c] flex justify-between items-center sticky top-0 z-10">
        <div className="flex gap-2">
          <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-neutral-300 px-2 py-1 bg-black rounded border border-[#262626]">
            Markdown Output
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={!result?.markdown}
            className="h-8 px-2 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white"
            title="Copy Markdown"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSave}
            disabled={!result || saving}
            className="h-8 px-2 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white"
            title="Save Package"
          >
            {saving ? (
              <div className="animate-spin w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleAppend}
            disabled={!result || appending}
            className="h-8 px-2 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white"
            title="Append to Package"
          >
            <Plus className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={!result?.markdown}
            className="h-8 px-2 text-xs font-mono border-[#262626] bg-black text-neutral-300 hover:text-white"
            title="Download .md"
          >
            <Download className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-5 overflow-y-auto font-mono text-xs text-neutral-300 bg-black leading-relaxed select-text">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full text-neutral-400 gap-3">
            <div className="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full" />
            <span className="text-xs font-mono">Synthesizing context package...</span>
          </div>
        ) : result ? (
          <MarkdownContent content={result.markdown} />
        ) : error ? (
          <div className="text-center py-12 text-red-400 font-mono text-xs">{error}</div>
        ) : (
          <div className="text-center py-16 text-neutral-600 flex flex-col items-center justify-center">
            <FileText className="w-10 h-10 mb-3 opacity-40" />
            <p className="text-xs font-mono text-neutral-400">Enter a prompt and click Generate</p>
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
          className="list-disc pl-5 space-y-1 my-2 text-neutral-400"
        >
          {currentList.map((item, i) => (
            <li key={i} className="text-neutral-300">
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
          className="text-white text-base font-bold mt-4 mb-2 pb-1 border-b border-[#262626]"
        >
          {line.slice(2)}
        </h1>
      );
    } else if (line.startsWith("## ")) {
      flushList();
      elements.push(
        <h2
          key={i}
          className="text-neutral-200 text-sm font-semibold mt-4 mb-1.5"
        >
          {line.slice(3)}
        </h2>
      );
    } else if (line.startsWith("### ")) {
      flushList();
      elements.push(
        <h3
          key={i}
          className="text-neutral-400 text-xs font-semibold mt-3 mb-1"
        >
          {line.slice(4)}
        </h3>
      );
    } else if (line.startsWith("- ")) {
      currentList.push(line);
    } else if (line === "---") {
      flushList();
      elements.push(
        <hr key={i} className="my-3 border-[#262626]" />
      );
    } else if (line.trim()) {
      flushList();
      elements.push(
        <p key={i} className="text-neutral-300 my-1">
          {renderInlineCode(line)}
        </p>
      );
    } else {
      flushList();
    }
  }
  flushList();

  return <div className="space-y-1">{elements}</div>;
}

function renderInlineCode(text: string): ReactNode {
  const parts = text.split(/`([^`]+)`/);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <code
        key={i}
        className="px-1 py-0.5 bg-[#141414] border border-[#262626] rounded text-[11px] font-mono text-neutral-200"
      >
        {part}
      </code>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}
