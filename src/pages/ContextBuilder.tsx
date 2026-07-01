/**
 * ContextBuilder — generate Context Packages for development tasks.
 * Primary demo screen for the hackathon.
 */

import { useState, ReactNode } from "react";
import { Send, Copy, Check, Loader2, Clock, FileText, Layers } from "lucide-react";
import { generateContext, ContextResponse } from "../lib/api";

export default function ContextBuilder() {
  const [query, setQuery] = useState("");
  const [datasets, setDatasets] = useState("default");
  const [topK, setTopK] = useState(20);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ContextResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState<ContextResponse[]>([]);

  const handleGenerate = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const datasetList = datasets.split(",").map((d) => d.trim()).filter(Boolean);
      const response = await generateContext({
        task: query.trim(),
        datasets: datasetList,
        top_k: topK,
      });
      setResult(response);
      setHistory((prev) => [response, ...prev].slice(0, 10));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

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

  return (
    <div className="flex h-full">
      {/* Left Panel — Query Input */}
      <div className="w-80 border-r border-gray-200 dark:border-gray-700 p-4 flex flex-col">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Query
        </h2>

        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a development question...&#10;&#10;Example: How does the backend generate Context Packages?"
          className="flex-1 min-h-[120px] p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              handleGenerate();
            }
          }}
        />

        <div className="mt-3 space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Datasets
            </label>
            <input
              type="text"
              value={datasets}
              onChange={(e) => setDatasets(e.target.value)}
              placeholder="dataset1, dataset2"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              Top K: {topK}
            </label>
            <input
              type="range"
              min="5"
              max="50"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full"
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || !query.trim()}
            className="w-full py-2.5 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={16} />
                Generating...
              </>
            ) : (
              <>
                <Send size={16} />
                Generate
              </>
            )}
          </button>
        </div>

        {/* History */}
        {history.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-xs font-medium text-gray-500 mb-2">Recent</h3>
            <div className="space-y-1 max-h-40 overflow-auto">
              {history.map((h, i) => (
                <button
                  key={i}
                  onClick={() => setResult(h)}
                  className="w-full text-left px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded truncate"
                >
                  {h.task}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right Panel — Result */}
      <div className="flex-1 flex flex-col">
        {/* Stats Bar */}
        {result && (
          <div className="flex items-center gap-4 px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 text-sm">
            <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <Clock size={14} />
              {(result.total_time_ms / 1000).toFixed(1)}s
            </span>
            <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <FileText size={14} />
              {result.token_estimate} tokens
            </span>
            <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <Layers size={14} />
              {result.section_count} sections
            </span>
            <span className="text-gray-500">
              {result.retrieved_memories} memories → {result.deduplicated_memories} unique
            </span>
            <div className="flex-1" />
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        )}

        {/* Markdown Content */}
        <div className="flex-1 overflow-auto p-6">
          {result ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <MarkdownView content={result.markdown} />
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-500">{error}</div>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <FileText size={48} className="mx-auto mb-4 opacity-50" />
              <p>Enter a question and click Generate</p>
              <p className="text-sm mt-1">or press Ctrl+Enter</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Render inline code in text.
 */
function renderInlineCode(text: string): ReactNode {
  const parts = text.split(/`([^`]+)`/);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <code key={i} className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono">{part}</code>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

/**
 * Simple Markdown renderer that converts markdown headers and lists.
 */
function MarkdownView({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: ReactNode[] = [];
  let currentList: string[] = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="list-disc pl-6 space-y-1 my-2">
          {currentList.map((item, i) => (
            <li key={i} className="text-gray-700 dark:text-gray-300">
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
        <h1 key={i} className="text-2xl font-bold text-gray-900 dark:text-white mt-6 mb-3">
          {line.slice(2)}
        </h1>
      );
    } else if (line.startsWith("## ")) {
      flushList();
      elements.push(
        <h2 key={i} className="text-xl font-semibold text-gray-900 dark:text-white mt-5 mb-2">
          {line.slice(3)}
        </h2>
      );
    } else if (line.startsWith("### ")) {
      flushList();
      elements.push(
        <h3 key={i} className="text-lg font-medium text-gray-900 dark:text-white mt-4 mb-2">
          {line.slice(4)}
        </h3>
      );
    } else if (line.startsWith("- ")) {
      currentList.push(line);
    } else if (line === "---") {
      flushList();
      elements.push(<hr key={i} className="my-4 border-gray-200 dark:border-gray-700" />);
    } else if (line.trim()) {
      flushList();
      elements.push(
        <p key={i} className="text-gray-700 dark:text-gray-300 my-1">
          {line}
        </p>
      );
    } else {
      flushList();
    }
  }
  flushList();

  return <>{elements}</>;
}
