import { useState, useMemo } from "react";
import {
  Layers,
  FileCode,
  Database,
  GitFork,
  ChevronDown,
  ChevronRight,
  Workflow,
  Copy,
  Check,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";
import type { AgentContextResponse } from "@/lib/api";

interface EvidenceItem {
  id: string;
  name: string;
  path?: string;
  lineRange?: string;
  kind: "model" | "service" | "caller" | "callee" | "file" | "symbol";
  relevanceReason: string;
}

interface EvidenceGroup {
  id: string;
  title: string;
  icon: typeof Database;
  items: EvidenceItem[];
}

interface EvidenceProvenanceLayerProps {
  agentResponse: AgentContextResponse;
  className?: string;
}

export function EvidenceProvenanceLayer({
  agentResponse,
  className,
}: EvidenceProvenanceLayerProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    models: true,
    services: true,
    callflow: false,
    files: true,
  });

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  const handleCopyPath = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  // Parse evidence from actual AgentContextResponse metadata
  const { groups, totalSources, totalSymbols } = useMemo(() => {
    const rawMarkdown = agentResponse.context_markdown || "";

    // 1. Extract snippet file paths and line ranges from markdown headers
    // e.g. "### `accounts/models.py` (Lines 1-30)" or "### accounts/models.py (Lines 1-30)"
    const snippetRegex = /###\s*`?([^\n`]+)`?\s*(?:\(Lines\s*(\d+-\d+)\))?/g;
    const parsedSnippets: { path: string; lineRange?: string }[] = [];
    let match;
    while ((match = snippetRegex.exec(rawMarkdown)) !== null) {
      const p = match[1].trim();
      if (p && !p.startsWith("#") && (p.includes(".") || p.includes("/"))) {
        parsedSnippets.push({
          path: p,
          lineRange: match[2] ? `L${match[2].replace("-", "-L")}` : undefined,
        });
      }
    }

    // 2. Data Models & Entities
    const modelSymbols = agentResponse.extracted_symbols.filter((s) => {
      const lower = s.toLowerCase();
      return (
        lower.includes("model") ||
        lower.includes("user") ||
        lower.includes("customer") ||
        lower.includes("event") ||
        lower.includes("booking") ||
        lower.includes("item") ||
        lower.includes("quest") ||
        lower.includes("schema") ||
        lower.includes("config") ||
        /^[A-Z][a-zA-Z0-9]+(?:Model|Schema|Entity|Data|State|Info)?$/.test(s)
      );
    });

    const modelItems: EvidenceItem[] = modelSymbols.slice(0, 6).map((sym) => {
      // Find matching snippet or file
      const matchingFile = agentResponse.related_files.find((f) =>
        f.toLowerCase().includes(sym.toLowerCase()) || f.toLowerCase().includes("model")
      );
      const matchingSnippet = parsedSnippets.find((s) => s.path === matchingFile);

      return {
        id: `model-${sym}`,
        name: sym,
        path: matchingFile || agentResponse.related_files[0],
        lineRange: matchingSnippet?.lineRange,
        kind: "model",
        relevanceReason: sym.toLowerCase().includes("model") ? "Data Schema" : "Domain Entity",
      };
    });

    // 3. Handlers, Services & Middleware
    const serviceSymbols = agentResponse.extracted_symbols.filter(
      (s) => !modelSymbols.includes(s)
    );

    const serviceItems: EvidenceItem[] = serviceSymbols.slice(0, 6).map((sym) => {
      const lower = sym.toLowerCase();
      let reason = "Target Component";
      if (lower.includes("auth") || lower.includes("oauth") || lower.includes("session")) {
        reason = "Authentication & Sessions";
      } else if (lower.includes("client") || lower.includes("api") || lower.includes("notion")) {
        reason = "API Client Operation";
      } else if (lower.includes("middleware") || lower.includes("handler")) {
        reason = "Middleware & Routing";
      } else if (lower.includes("test")) {
        reason = "Test Verification";
      }

      const matchingFile = agentResponse.related_files.find((f) =>
        f.toLowerCase().includes(sym.toLowerCase())
      );
      const matchingSnippet = parsedSnippets.find((s) => s.path === matchingFile);

      return {
        id: `service-${sym}`,
        name: sym,
        path: matchingFile,
        lineRange: matchingSnippet?.lineRange,
        kind: "service",
        relevanceReason: reason,
      };
    });

    // 4. Structural Call Flow (Callers & Callees)
    const callFlowItems: EvidenceItem[] = [
      ...agentResponse.callers.slice(0, 4).map((c) => ({
        id: `caller-${c}`,
        name: c,
        kind: "caller" as const,
        relevanceReason: "Upstream Invocation (Caller)",
      })),
      ...agentResponse.callees.slice(0, 4).map((c) => ({
        id: `callee-${c}`,
        name: c,
        kind: "callee" as const,
        relevanceReason: "Downstream Invocation (Callee)",
      })),
    ];

    // 5. Matched Verified Files
    const fileItems: EvidenceItem[] = Array.from(
      new Set([...parsedSnippets.map((s) => s.path), ...agentResponse.related_files])
    )
      .slice(0, 8)
      .map((filePath) => {
        const snippet = parsedSnippets.find((s) => s.path === filePath);
        let reason = "Matched Code File";
        const lower = filePath.toLowerCase();
        if (lower.includes("model")) reason = "Data Models & Schemas";
        else if (lower.includes("auth") || lower.includes("session")) reason = "Auth & Session Logic";
        else if (lower.includes("test")) reason = "Test Scenarios";
        else if (lower.includes("notion") || lower.includes("api")) reason = "API Operations";

        return {
          id: `file-${filePath}`,
          name: filePath.split("/").pop() || filePath,
          path: filePath,
          lineRange: snippet?.lineRange,
          kind: "file",
          relevanceReason: reason,
        };
      });

    const activeGroups: EvidenceGroup[] = [];

    if (modelItems.length > 0) {
      activeGroups.push({
        id: "models",
        title: "Data Models & Schemas",
        icon: Database,
        items: modelItems,
      });
    }

    if (serviceItems.length > 0) {
      activeGroups.push({
        id: "services",
        title: "Components & Middleware",
        icon: Layers,
        items: serviceItems,
      });
    }

    if (callFlowItems.length > 0) {
      activeGroups.push({
        id: "callflow",
        title: "Structural Call Flow",
        icon: GitFork,
        items: callFlowItems,
      });
    }

    if (fileItems.length > 0) {
      activeGroups.push({
        id: "files",
        title: "Target Files & Code Citations",
        icon: FileCode,
        items: fileItems,
      });
    }

    const uniqueSourcesCount = Array.from(
      new Set([
        ...agentResponse.related_files,
        ...parsedSnippets.map((s) => s.path),
      ])
    ).length;

    const uniqueSymbolsCount = Array.from(
      new Set([
        ...agentResponse.extracted_symbols,
        ...agentResponse.callers,
        ...agentResponse.callees,
      ])
    ).length;

    return {
      groups: activeGroups,
      totalSources: uniqueSourcesCount || fileItems.length,
      totalSymbols: uniqueSymbolsCount || modelItems.length + serviceItems.length,
    };
  }, [agentResponse]);

  if (groups.length === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        "rounded-md bg-[#050505] border border-[#1a1a1a] p-3 space-y-2.5",
        className
      )}
    >
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#141414] pb-2">
        <div className="flex items-center gap-1.5">
          <Workflow className="w-3.5 h-3.5 text-neutral-300" />
          <span className="text-xs font-medium text-white tracking-tight">
            What RE:Track Found
          </span>
        </div>

        {/* Evidence Count Badges */}
        <div className="flex items-center gap-1 flex-wrap text-[11px] font-mono">
          {totalSources > 0 && (
            <Badge
              variant="success"
              className="text-[10px] px-1.5 py-0"
            >
              {totalSources} {totalSources === 1 ? "source" : "sources"}
            </Badge>
          )}
          {totalSymbols > 0 && (
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0"
            >
              {totalSymbols} {totalSymbols === 1 ? "symbol" : "symbols"}
            </Badge>
          )}
          <span className="text-neutral-500 text-[10px]">
            · {groups.length} {groups.length === 1 ? "group" : "groups"}
          </span>
        </div>
      </div>

      {/* Collapsible Evidence Groups */}
      <div className="space-y-1.5">
        {groups.map((group) => {
          const isExpanded = expandedGroups[group.id] ?? true;
          const GroupIcon = group.icon;

          return (
            <div
              key={group.id}
              className="rounded border border-[#161616] bg-[#080808] overflow-hidden"
            >
              {/* Group Toggle Header */}
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className="w-full px-2.5 py-1.5 flex items-center justify-between text-xs text-neutral-300 hover:text-white bg-[#0b0b0b] hover:bg-[#101010] transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-1.5">
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3 text-neutral-500" />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-neutral-500" />
                  )}
                  <GroupIcon className="w-3 h-3 text-neutral-400" />
                  <span className="font-medium text-neutral-200">{group.title}</span>
                  <span className="text-[11px] text-neutral-500 font-mono">
                    ({group.items.length})
                  </span>
                </div>
                <span className="text-[10px] text-neutral-500 font-mono">
                  {isExpanded ? "Hide" : "Show"}
                </span>
              </button>

              {/* Group Items List */}
              <AnimatePresence initial={false}>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    className="divide-y divide-[#121212] px-2.5 py-1 bg-black"
                  >
                    {group.items.map((item) => (
                      <div
                        key={item.id}
                        className="py-1 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs font-mono group"
                      >
                        {/* Name & Path */}
                        <div className="flex items-center gap-1.5 min-w-0 flex-1">
                          <span className="font-semibold text-neutral-200 shrink-0">
                            {item.name}
                          </span>

                          {item.path && (
                            <span
                              className="text-[11px] text-neutral-500 truncate hover:text-neutral-300 transition-colors cursor-pointer"
                              title={`Click to copy: ${item.path}`}
                              onClick={() => handleCopyPath(item.id, item.path!)}
                            >
                              {item.path}
                            </span>
                          )}

                          {item.lineRange && (
                            <span className="text-[10px] text-emerald-400 bg-emerald-950/30 border border-emerald-500/20 px-1 rounded shrink-0">
                              {item.lineRange}
                            </span>
                          )}

                          {item.path && (
                            <button
                              type="button"
                              onClick={() => handleCopyPath(item.id, item.path!)}
                              className="opacity-0 group-hover:opacity-100 text-neutral-500 hover:text-white transition-opacity shrink-0 cursor-pointer"
                              title="Copy path"
                            >
                              {copiedId === item.id ? (
                                <Check className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          )}
                        </div>

                        {/* Relevance Explanation Badge */}
                        <div className="shrink-0 flex items-center gap-1 self-start sm:self-auto">
                          <span className="text-[10px] text-neutral-500 bg-[#0e0e0e] border border-[#1c1c1c] px-1.5 py-0.5 rounded">
                            {item.relevanceReason}
                          </span>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </div>
  );
}
