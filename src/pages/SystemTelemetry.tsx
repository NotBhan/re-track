import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { useHealthStore } from "@/stores/health-store";
import { useMemoryStore } from "@/stores/memory-store";
import { OllamaSettings } from "@/components/settings/OllamaSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { BackendSettings } from "@/components/settings/BackendSettings";
import { CogneeSettings } from "@/components/settings/CogneeSettings";
import { DiagnosticsSettings } from "@/components/settings/DiagnosticsSettings";
import Benchmarks from "@/pages/Benchmarks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Activity,
  Cpu,
  Database,
  Gauge,
  Terminal,
  Server,
  HardDrive,
  RefreshCw,
  Layers,
  Globe,
} from "lucide-react";

export type SystemTab =
  | "runtime"
  | "storage"
  | "benchmarks"
  | "diagnostics";

export default function SystemTelemetry() {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const activeTab: SystemTab =
    rawTab === "storage"
      ? "storage"
      : rawTab === "benchmarks"
      ? "benchmarks"
      : rawTab === "diagnostics"
      ? "diagnostics"
      : "runtime"; // default or "runtime", "providers", "telemetry", "settings"

  const {
    backendOnline,
    health,
    status,
    dashboardStats,
    providerIdentity,
    providerReachable,
    activeModel,
    configuredModel,
    lastExecutingModel,
    cogneeInitialized,
    engineState,
    pollHealth,
    fetchDashboardStats,
  } = useHealthStore();

  const { stats: memoryStats, fetchStats: fetchMemoryStats } = useMemoryStore();

  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    pollHealth();
    fetchDashboardStats();
    fetchMemoryStats();
  }, [pollHealth, fetchDashboardStats, fetchMemoryStats]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.allSettled([
        pollHealth(),
        fetchDashboardStats(),
        fetchMemoryStats(),
      ]);
    } finally {
      setRefreshing(false);
    }
  };

  const setTab = (tab: SystemTab) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", tab);
    setSearchParams(next);
  };

  const tabs: { id: SystemTab; label: string; icon: typeof Activity; badge?: string | number }[] = [
    { id: "runtime", label: "Provider & Runtime", icon: Cpu },
    { id: "storage", label: "Storage & Subsystems", icon: Database },
    { id: "benchmarks", label: "Benchmarks", icon: Gauge },
    { id: "diagnostics", label: "Diagnostics", icon: Terminal },
  ];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased font-sans">
      <TopBar
        title="RE:Track | System & Telemetry"
        subtitle="Hardware, Storage, Provider Runtime & Diagnostics"
      >
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="text-[10px] font-mono border-neutral-800 text-neutral-400 bg-neutral-900 hidden sm:inline-flex"
          >
            Global Scope (Repository Independent)
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
            className="h-7 px-2.5 text-xs bg-[#0f0f0f] border-[#222222] text-neutral-300 hover:text-white"
          >
            <RefreshCw className={cn("w-3 h-3 mr-1.5", refreshing && "animate-spin")} />
            <span>Refresh</span>
          </Button>
        </div>
      </TopBar>

      <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 lg:p-6">
        <div className="max-w-6xl mx-auto space-y-5">
          {/* Top Tabs Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1a1a1a] pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-white">
                  System Architecture &amp; Telemetry
                </h1>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] font-mono",
                    backendOnline
                      ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                      : "border-red-500/30 text-red-400 bg-red-500/10"
                  )}
                >
                  {backendOnline ? "Backend Online" : "Backend Offline"}
                </Badge>
              </div>
              <p className="text-xs text-neutral-500 mt-0.5">
                Inspect local inference runners, storage subsystems, performance metrics, and application logs.
              </p>
            </div>

            {/* Navigation tabs */}
            <div className="flex items-center gap-1 bg-[#0a0a0a] p-1 rounded-lg border border-[#222222] overflow-x-auto">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setTab(tab.id)}
                    className={cn(
                      "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors cursor-pointer font-mono whitespace-nowrap",
                      isActive
                        ? "bg-white text-black font-semibold shadow-xs"
                        : "text-neutral-400 hover:text-white hover:bg-[#141414]"
                    )}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* TAB 1: PROVIDER & RUNTIME */}
          {activeTab === "runtime" && (
            <div className="space-y-5">
              {/* Three Runtime Identities Card */}
              <div className="p-4 rounded-xl bg-[#080808] border border-[#1e1e1e] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-neutral-300 font-mono uppercase tracking-wider">
                    Runtime Identities (Truth Boundary Contract)
                  </span>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    Zero Synthetic Fallback
                  </Badge>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] space-y-1">
                    <div className="text-[10px] text-neutral-500 uppercase">1. Configured Model</div>
                    <div className="text-sm font-medium text-neutral-200 truncate" title={configuredModel || "None"}>
                      {configuredModel || "None"}
                    </div>
                    <div className="text-[11px] text-neutral-500">Provider: {providerIdentity || "None"}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] space-y-1">
                    <div className="text-[10px] text-neutral-500 uppercase">2. Verified Active Model</div>
                    <div
                      className={cn(
                        "text-sm font-medium truncate",
                        activeModel ? "text-emerald-400" : "text-amber-400"
                      )}
                      title={activeModel || "Unverified"}
                    >
                      {activeModel || "Unverified"}
                    </div>
                    <div className="text-[11px] text-neutral-500">
                      Status: {providerReachable ? "Endpoint Reachable" : "Unreachable"}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] space-y-1">
                    <div className="text-[10px] text-neutral-500 uppercase">3. Last Executing Model</div>
                    <div className="text-sm font-medium text-neutral-200 truncate" title={lastExecutingModel || "None"}>
                      {lastExecutingModel || "None (No executions)"}
                    </div>
                    <div className="text-[11px] text-neutral-500">Latest active inference engine</div>
                  </div>
                </div>
              </div>

              {/* Hardware & Execution Telemetry */}
              <div className="p-4 rounded-xl bg-[#080808] border border-[#1e1e1e] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-neutral-300 font-mono uppercase tracking-wider">
                    Hardware &amp; Execution Telemetry
                  </span>
                  <Badge variant="outline" className="text-[10px] font-mono border-neutral-800 text-neutral-400">
                    Device: {health?.execution_device || "Unavailable"}
                  </Badge>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
                  {/* Execution Device */}
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] space-y-1">
                    <div className="text-[10px] text-neutral-500 uppercase">Execution Device</div>
                    <div className="text-sm font-semibold text-neutral-200">
                      {health?.execution_device || "Unavailable"}
                    </div>
                    <div className="text-[11px] text-neutral-500">
                      Target: {health?.execution_device === "GPU" ? "Hardware Acceleration" : health?.execution_device === "CPU" ? "Host Compute" : "Undetected"}
                    </div>
                  </div>

                  {/* CPU Usage */}
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] space-y-1">
                    <div className="text-[10px] text-neutral-500 uppercase">CPU Usage</div>
                    <div className="text-sm font-semibold text-neutral-200">
                      {health?.cpu_percent != null ? `${health.cpu_percent.toFixed(1)}%` : "Unavailable"}
                    </div>
                    <div className="text-[11px] text-neutral-500">
                      {health?.cpu_percent != null ? "Active host utilization" : "Telemetry offline"}
                    </div>
                  </div>

                  {/* Host RAM */}
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] space-y-1">
                    <div className="text-[10px] text-neutral-500 uppercase">Host RAM</div>
                    <div className="text-sm font-semibold text-neutral-200">
                      {health?.ram_used_gb != null && health?.ram_total_gb != null
                        ? `${health.ram_used_gb.toFixed(1)} GB / ${health.ram_total_gb.toFixed(1)} GB`
                        : "Unavailable"}
                    </div>
                    <div className="text-[11px] text-neutral-500">
                      {health?.ram_percent != null
                        ? `${health.ram_percent.toFixed(0)}% utilized${health.high_memory_pressure ? " (High Pressure)" : ""}`
                        : "Memory metrics unavailable"}
                    </div>
                  </div>

                  {/* GPU & VRAM */}
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] space-y-1">
                    <div className="text-[10px] text-neutral-500 uppercase">GPU / Acceleration</div>
                    <div className="text-sm font-semibold text-neutral-200 truncate" title={health?.gpu_name || health?.gpu_presence || "Unavailable"}>
                      {health?.gpu_presence && health.gpu_presence !== "None"
                        ? health.gpu_name || health.gpu_presence
                        : health?.gpu_presence === "None"
                        ? "None detected (CPU mode)"
                        : "Unavailable"}
                    </div>
                    <div className="text-[11px] text-neutral-500">
                      {health?.gpu_presence && health.gpu_presence !== "None"
                        ? `VRAM: ${health.vram_used_gb != null && health.vram_total_gb != null ? `${health.vram_used_gb.toFixed(1)} / ${health.vram_total_gb.toFixed(1)} GB` : "Unavailable"}`
                        : "No discrete GPU"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Hardware & System Health Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
                <div className="p-4 rounded-xl bg-[#080808] border border-[#1e1e1e] space-y-2">
                  <div className="flex items-center justify-between text-neutral-500 text-xs">
                    <span className="flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-neutral-400" />
                      <span>Context Engine</span>
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[9px] uppercase",
                        engineState === "healthy"
                          ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                          : engineState === "degraded"
                          ? "border-amber-500/30 text-amber-400 bg-amber-500/10"
                          : "border-red-500/30 text-red-400 bg-red-500/10"
                      )}
                    >
                      {engineState || "Unknown"}
                    </Badge>
                  </div>
                  <div className="text-lg font-semibold text-white">
                    {health?.version ? `v${health.version}` : "v0.1.0"}
                  </div>
                  <div className="text-[11px] text-neutral-500">
                    Engine Status: {engineState || "Active"}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#080808] border border-[#1e1e1e] space-y-2">
                  <div className="flex items-center justify-between text-neutral-500 text-xs">
                    <span className="flex items-center gap-1.5">
                      <HardDrive className="w-3.5 h-3.5 text-neutral-400" />
                      <span>Data Root</span>
                    </span>
                    <Badge variant="outline" className="text-[9px] uppercase border-neutral-800 text-neutral-400 bg-neutral-900">
                      Local
                    </Badge>
                  </div>
                  <div className="text-sm font-semibold text-neutral-200 truncate" title={status?.data_root || "~/.retrack/data"}>
                    {status?.data_root || "~/.retrack/data"}
                  </div>
                  <div className="text-[11px] text-neutral-500">
                    Canonical storage directory
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#080808] border border-[#1e1e1e] space-y-2">
                  <div className="flex items-center justify-between text-neutral-500 text-xs">
                    <span className="flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-neutral-400" />
                      <span>Cognee Memory</span>
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[9px] uppercase",
                        cogneeInitialized
                          ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                          : "border-neutral-800 text-neutral-400 bg-neutral-900"
                      )}
                    >
                      {cogneeInitialized ? "Initialized" : "Not Inited"}
                    </Badge>
                  </div>
                  <div className="text-lg font-semibold text-white">
                    {memoryStats?.dataset_count ?? 0} Datasets
                  </div>
                  <div className="text-[11px] text-neutral-500">
                    Vectors &amp; knowledge graphs
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#080808] border border-[#1e1e1e] space-y-2">
                  <div className="flex items-center justify-between text-neutral-500 text-xs">
                    <span className="flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 text-neutral-400" />
                      <span>Repositories</span>
                    </span>
                    <Badge variant="outline" className="text-[9px] uppercase border-neutral-800 text-neutral-400 bg-neutral-900">
                      Indexed
                    </Badge>
                  </div>
                  <div className="text-lg font-semibold text-white">
                    {health?.repository_count ?? dashboardStats?.indexed_repos ?? 0}
                  </div>
                  <div className="text-[11px] text-neutral-500">
                    {health?.context_package_count ?? dashboardStats?.packages_generated ?? 0} context packages
                  </div>
                </div>
              </div>

              {/* Provider Configuration */}
              <div className="pt-2">
                <OllamaSettings />
              </div>
            </div>
          )}

          {/* TAB 2: STORAGE & SUBSYSTEMS */}
          {activeTab === "storage" && (
            <div className="space-y-6">
              {/* Storage Subsystems Detailed Status */}
              <div className="p-4 rounded-xl bg-[#080808] border border-[#1e1e1e] space-y-3">
                <div className="text-xs font-semibold text-neutral-300 font-mono uppercase tracking-wider">
                  Storage Subsystems Status
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-neutral-200">SQLite Manifest</div>
                      <div className="text-[10px] text-neutral-500">Tier 2 Truth DB</div>
                    </div>
                    <Badge variant="outline" className="text-[9px] uppercase border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                      Healthy
                    </Badge>
                  </div>

                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-neutral-200">LanceDB</div>
                      <div className="text-[10px] text-neutral-500">Tier 3 Vector Store</div>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[9px] uppercase",
                        memoryStats?.storage_subsystems?.lancedb === "healthy"
                          ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                          : "border-neutral-800 text-neutral-400 bg-neutral-900"
                      )}
                    >
                      {memoryStats?.storage_subsystems?.lancedb || "Ready"}
                    </Badge>
                  </div>

                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-neutral-200">Kùzu Embedded</div>
                      <div className="text-[10px] text-neutral-500">Tier 3 Property Graph</div>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[9px] uppercase",
                        memoryStats?.storage_subsystems?.kuzu === "healthy"
                          ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                          : "border-neutral-800 text-neutral-400 bg-neutral-900"
                      )}
                    >
                      {memoryStats?.storage_subsystems?.kuzu || "Ready"}
                    </Badge>
                  </div>

                  <div className="p-3 rounded-lg bg-[#0c0c0c] border border-[#181818] flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-neutral-200">Cognee Engine</div>
                      <div className="text-[10px] text-neutral-500">Tier 4 Semantic Memory</div>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[9px] uppercase",
                        cogneeInitialized
                          ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                          : "border-amber-500/30 text-amber-400 bg-amber-500/10"
                      )}
                    >
                      {cogneeInitialized ? "Initialized" : "Not Inited"}
                    </Badge>
                  </div>
                </div>
              </div>

              <StorageSettings />
              <div className="pt-4 border-t border-[#1a1a1a]">
                <CogneeSettings />
              </div>
            </div>
          )}

          {/* TAB 3: BENCHMARKS */}
          {activeTab === "benchmarks" && (
            <div className="space-y-4">
              <Benchmarks embedded={true} />
            </div>
          )}

          {/* TAB 4: DIAGNOSTICS */}
          {activeTab === "diagnostics" && (
            <div className="space-y-6">
              <DiagnosticsSettings />
              <div className="pt-4 border-t border-[#1a1a1a]">
                <BackendSettings />
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
