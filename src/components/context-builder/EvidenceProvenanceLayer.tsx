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

    // 2. Data Models & Schemas
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
        relevanceReason: sym.toLowerCase().includes("model") ? "Schema" : "Domain Entity",
      };
    });

    // 3. Components, Services & Middleware
    const serviceSymbols = agentResponse.extracted_symbols.filter(
      (s) => !modelSymbols.includes(s)
    );

    const serviceItems: EvidenceItem[] = serviceSymbols.slice(0, 6).map((sym) => {
      const lower = sym.toLowerCase();
      let reason = "Target Symbol";
      if (lower.includes("auth") || lower.includes("oauth") || lower.includes("session")) {
        reason = "Auth & Session";
      } else if (lower.includes("client") || lower.includes("api") || lower.includes("notion")) {
        reason = "API Client";
      } else if (lower.includes("middleware") || lower.includes("handler")) {
        reason = "Middleware & Routing";
      } else if (lower.includes("test")) {
        reason = "Verification";
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

    // 4. Structural Call Flow
    const callFlowItems: EvidenceItem[] = [
      ...agentResponse.callers.slice(0, 4).map((c) => ({
        id: `caller-${c}`,
        name: c,
        kind: "caller" as const,
        relevanceReason: "Caller (Upstream)",
      })),
      ...agentResponse.callees.slice(0, 4).map((c) => ({
        id: `callee-${c}`,
        name: c,
        kind: "callee" as const,
        relevanceReason: "Callee (Downstream)",
      })),
    ];

    // 5. Verified Source Files
    const fileItems: EvidenceItem[] = Array.from(
      new Set([...parsedSnippets.map((s) => s.path), ...agentResponse.related_files])
    )
      .slice(0, 8)
      .map((filePath) => {
        const snippet = parsedSnippets.find((s) => s.path === filePath);
        let reason = "Source Code";
        const lower = filePath.toLowerCase();
        if (lower.includes("model")) reason = "Data Schemas";
        else if (lower.includes("auth") || lower.includes("session")) reason = "Auth Logic";
        else if (lower.includes("test")) reason = "Test Scenarios";
        else if (lower.includes("api")) reason = "API Operations";

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
        title: "Target Components & Handlers",
        icon: Layers,
        items: serviceItems,
      });
    }

    if (fileItems.length > 0) {
      activeGroups.push({
        id: "files",
        title: "Source Files & Code Citations",
        icon: FileCode,
        items: fileItems,
      });
    }

    if (callFlowItems.length > 0) {
      activeGroups.push({
        id: "callflow",
        title: "Structural Call Invocations",
        icon: GitFork,
        items: callFlowItems,
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
        "rounded-lg bg-[#050505] border border-[#1a1a1a] p-3 space-y-2",
        className
      )}
    >
      {/* Provenance Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#141414] pb-2">
        <div className="flex items-center gap-1.5">
          <Workflow className="w-3.5 h-3.5 text-neutral-300" />
          <span className="text-xs font-semibold text-white tracking-tight">
            Evidence &amp; Source Provenance
          </span>
        </div>

        {/* Evidence Badges */}
        <div className="flex items-center gap-1.5 flex-wrap text-xs font-mono">
          {totalSources > 0 && (
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 border-[#262626] text-neutral-300"
            >
              {totalSources} {totalSources === 1 ? "source file" : "source files"}
            </Badge>
          )}
          {totalSymbols > 0 && (
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 border-[#262626] text-neutral-300"
            >
              {totalSymbols} {totalSymbols === 1 ? "symbol" : "symbols"}
            </Badge>
          )}
        </div>
      </div>

      {/* Collapsible Evidence Groups */}
      <div className="space-y-1">
        {groups.map((group) => {
          const isExpanded = expandedGroups[group.id] ?? true;
          const GroupIcon = group.icon;

          return (
            <div
              key={group.id}
              className="rounded-md border border-[#161616] bg-[#080808] overflow-hidden"
            >
              {/* Group Toggle Header */}
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className="w-full px-2.5 py-1.5 flex items-center justify-between text-xs text-neutral-300 hover:text-white bg-[#0a0a0a] hover:bg-[#101010] transition-colors cursor-pointer"
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
                    className="divide-y divide-[#121212] px-2.5 py-0.5 bg-black"
                  >
                    {group.items.map((item) => (
                      <div
                        key={item.id}
                        className="py-1 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-xs font-mono group"
                      >
                        {/* WHAT -> FROM -> WHERE Chain */}
                        <div className="flex items-center gap-1.5 min-w-0 flex-1">
                          {/* WHAT (Symbol / Entity Name) */}
                          <span className="font-semibold text-neutral-200 shrink-0">
                            {item.name}
                          </span>

                          {/* FROM (Source Path) */}
                          {item.path && (
                            <span
                              className="text-[11px] text-neutral-500 truncate hover:text-neutral-300 transition-colors cursor-pointer"
                              title={`Click to copy path: ${item.path}`}
                              onClick={() => handleCopyPath(item.id, item.path!)}
                            >
                              {item.path}
                            </span>
                          )}

                          {/* WHERE (Line citation) */}
                          {item.lineRange && (
                            <span className="text-[10px] text-emerald-400 bg-emerald-950/30 border border-emerald-500/20 px-1 rounded shrink-0">
                              {item.lineRange}
                            </span>
                          )}

                          {/* Copy Path Action */}
                          {item.path && (
                            <button
                              type="button"
                              onClick={() => handleCopyPath(item.id, item.path!)}
                              className="opacity-0 group-hover:opacity-100 text-neutral-500 hover:text-white transition-opacity shrink-0 cursor-pointer p-0.5"
                              title="Copy file path"
                              aria-label="Copy file path"
                            >
                              {copiedId === item.id ? (
                                <Check className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          )}
                        </div>

                        {/* Relevance Tag */}
                        <div className="shrink-0 flex items-center gap-1 self-start sm:self-auto">
                          <span className="text-[10px] text-neutral-500 bg-[#0c0c0c] border border-[#1a1a1a] px-1.5 py-0.2 rounded">
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
