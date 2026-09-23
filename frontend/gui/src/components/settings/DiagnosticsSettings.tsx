import { useEffect, useState } from "react";
import {
  getDetailedHealth,
  exportDiagnostics,
  type DetailedHealthResponse,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Activity,
  RefreshCw,
  Download,
  HardDrive,
  Cpu,
  Layers,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  FileText,
  Search,
} from "lucide-react";

export function DiagnosticsSettings() {
  const [health, setHealth] = useState<DetailedHealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [exporting, setExporting] = useState<boolean>(false);
  const [exportResult, setExportResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logFilter, setLogFilter] = useState<string>("");

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDetailedHealth();
      setHealth(data);
    } catch (err) {
      console.error("Failed to load operational health:", err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleExport = async () => {
    setExporting(true);
    setExportResult(null);
    try {
      const res = await exportDiagnostics();
      setExportResult(res.export_path);
    } catch (err) {
      console.error("Failed to export diagnostics bundle:", err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  };

  const status = health?.health_state || (health?.status === "ok" ? "healthy" : "degraded");

  const filteredLogs = (health?.diagnostics_log_entries || []).filter((log) => {
    if (!logFilter) return true;
    const searchStr = `${log.level || ""} ${log.logger || ""} ${log.message || ""} ${log.event || ""}`.toLowerCase();
    return searchStr.includes(logFilter.toLowerCase());
  });

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#1e1e1e]">
        <div>
          <h2 className="text-sm font-semibold text-white tracking-tight mb-0.5 flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            Operational Diagnostics &amp; Health
          </h2>
          <p className="text-xs text-neutral-500">
            Real-time backend telemetry, concurrency queue metrics, and sanitized diagnostic bundles.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHealth}
            disabled={loading}
            className="h-8 text-xs font-medium bg-[#0a0a0a] border-[#262626] hover:bg-[#141414] text-neutral-300"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={handleExport}
            disabled={exporting}
            className="h-8 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            <Download className="w-3.5 h-3.5 mr-1.5" />
            {exporting ? "Exporting..." : "Export Bundle"}
          </Button>
        </div>
      </div>

      {exportResult && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg text-xs text-emerald-300 flex items-start gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-semibold text-white">Diagnostic Bundle Exported Successfully</div>
            <div className="font-mono text-[11px] text-emerald-200/80 break-all">{exportResult}</div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-lg text-xs text-red-300 flex items-start gap-2.5">
          <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* System Health */}
        <div className="p-3.5 bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-neutral-400">System State</span>
            <Badge
              variant="outline"
              className={
                status === "healthy"
                  ? "bg-emerald-950/50 text-emerald-400 border-emerald-800/60 text-[10px]"
                  : status === "degraded"
                  ? "bg-amber-950/50 text-amber-400 border-amber-800/60 text-[10px]"
                  : "bg-red-950/50 text-red-400 border-red-800/60 text-[10px]"
              }
            >
              {status.toUpperCase()}
            </Badge>
          </div>
          <div className="text-sm font-semibold text-white">RE:Track v{health?.version || "0.1.0"}</div>
          <div className="text-[11px] text-neutral-500 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            MCP Stdio Ready
          </div>
        </div>

        {/* LLM Provider */}
        <div className="p-3.5 bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-neutral-400">LLM Provider</span>
            <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
          </div>
          <div className="text-sm font-semibold text-white truncate" title={health?.active_model || "Local Provider"}>
            {health?.active_model || "phi4-mini"}
          </div>
          <div className="text-[11px] text-neutral-500">
            {health?.ollama_reachable ? (
              <span className="text-emerald-400">Online &amp; Reachable</span>
            ) : (
              <span className="text-amber-400">Offline Fallback Active</span>
            )}
          </div>
        </div>

        {/* Canonical Storage */}
        <div className="p-3.5 bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-neutral-400">Storage Health</span>
            <HardDrive className="w-3.5 h-3.5 text-neutral-400" />
          </div>
          <div className="text-sm font-semibold text-white">
            {health?.storage_canonical_writable ? "Writable &amp; Ready" : "Read-Only"}
          </div>
          <div className="text-[11px] text-neutral-500 truncate">
            {health?.legacy_storage_detected ? "Legacy ~/.andes/ detected" : "~/.retrack/ canonical"}
          </div>
        </div>

        {/* Concurrency Queue */}
        <div className="p-3.5 bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-neutral-400">Concurrency Queue</span>
            <Cpu className="w-3.5 h-3.5 text-neutral-400" />
          </div>
          <div className="text-sm font-semibold text-white">
            {health?.concurrency_queue_depth ?? 0} / {health?.concurrency_queue_capacity ?? 5} waiting
          </div>
          <div className="text-[11px] text-neutral-500">
            {health?.concurrency_available_slots ?? 1} execution slot(s) free
          </div>
        </div>
      </div>

      {/* Storage & Indexing Details */}
      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-3">
        <h3 className="text-xs font-semibold text-neutral-200 flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-neutral-400" />
          Workspaces &amp; Memory Topology
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-[#181818] font-mono text-xs">
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">Repositories</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">{health?.repository_count ?? 0} indexed</div>
          </div>
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">Context Packages</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">{health?.context_package_count ?? 0} saved</div>
          </div>
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">AST Cache</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">
              {health?.cache_files_count ?? 0} files ({roundKb(health?.cache_total_bytes)} KB)
            </div>
          </div>
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">RAM Pressure</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">
              {health?.ram_percent ? `${health.ram_percent.toFixed(1)}%` : "Normal"}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Diagnostic Logs */}
      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-neutral-400" />
            <h3 className="text-xs font-semibold text-neutral-200">Recent Structured Diagnostic Logs</h3>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-neutral-500" />
            <input
              type="text"
              placeholder="Filter log events..."
              value={logFilter}
              onChange={(e) => setLogFilter(e.target.value)}
              className="w-full bg-[#050505] border border-[#222] rounded-md pl-8 pr-2.5 py-1 text-xs text-neutral-200 placeholder:text-neutral-600 focus:outline-hidden focus:border-neutral-500"
            />
          </div>
        </div>

        <div className="bg-[#050505] border border-[#181818] rounded-md p-3 max-h-60 overflow-y-auto font-mono text-[11px] space-y-1.5 scrollbar-thin">
          {filteredLogs.length === 0 ? (
            <div className="text-neutral-500 text-center py-4">No recent diagnostic log records found.</div>
          ) : (
            filteredLogs.map((log, idx) => (
              <div key={idx} className="flex items-start gap-2 py-0.5 border-b border-[#111] last:border-0">
                <span className="text-neutral-600 shrink-0 text-[10px]">
                  {formatTime(String(log.timestamp || ""))}
                </span>
                <span
                  className={`text-[10px] px-1 rounded-xs font-bold uppercase shrink-0 ${
                    log.level === "ERROR"
                      ? "bg-red-950 text-red-400 border border-red-800/50"
                      : log.level === "WARNING"
                      ? "bg-amber-950 text-amber-400 border border-amber-800/50"
                      : "bg-neutral-900 text-neutral-400"
                  }`}
                >
                  {String(log.level || "INFO")}
                </span>
                <span className="text-neutral-400 truncate flex-1">{String(log.message || log.event || "")}</span>
                {log.duration_ms !== undefined && log.duration_ms !== null ? (
                  <span className="text-neutral-600 text-[10px] shrink-0">{String(log.duration_ms)}ms</span>
                ) : null}
              </div>
            ))
          )}
        </div>

        <div className="text-[10px] text-neutral-600 flex items-center gap-1.5 pt-1">
          <ShieldCheck className="w-3.5 h-3.5 text-neutral-500 shrink-0" />
          <span>Local-First Privacy Guarantee: All credentials, source codes, and task prompts are strictly omitted or redacted.</span>
        </div>
      </div>
    </div>
  );
}

function roundKb(bytes?: number): string {
  if (!bytes) return "0.0";
  return (bytes / 1024).toFixed(1);
}

function formatTime(isoStr: string): string {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString();
  } catch {
    return isoStr.slice(11, 19);
  }
}
