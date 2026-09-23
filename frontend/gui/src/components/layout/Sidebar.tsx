import { NavLink, useLocation } from "react-router-dom";
import { useState } from "react";
import {
  FolderGit2,
  Sparkles,
  Brain,
  Gauge,
  Plus,
  Layers,
  RefreshCw,
  X,
  ChevronDown,
  ChevronUp,
  Settings,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useHealthStore } from "@/stores/health-store";
import { cn } from "@/lib/utils";

const navItems = [
  {
    to: "/workspace",
    icon: FolderGit2,
    label: "Workspace",
    description: "Repositories & AST",
    match: (pathname: string) =>
      pathname === "/" || pathname.startsWith("/workspace") || pathname.startsWith("/repositories"),
  },
  {
    to: "/studio",
    icon: Sparkles,
    label: "Context Studio",
    description: "Context Engine",
    match: (pathname: string) =>
      pathname.startsWith("/studio") || pathname.startsWith("/context-builder") || pathname.startsWith("/packages"),
  },
  {
    to: "/memory",
    icon: Brain,
    label: "Memory Engine",
    description: "Cognee & Vectors",
    match: (pathname: string) => pathname.startsWith("/memory"),
  },
  {
    to: "/system",
    icon: Gauge,
    label: "System & Telemetry",
    description: "Hardware & Health",
    match: (pathname: string) =>
      pathname.startsWith("/system") || pathname.startsWith("/benchmarks"),
  },
  {
    to: "/settings",
    icon: Settings,
    label: "Settings",
    description: "Provider & Preferences",
    match: (pathname: string) => pathname.startsWith("/settings"),
  },
];

interface SidebarProps {
  onNewIndex?: () => void;
  onCloseMobile?: () => void;
  isMobile?: boolean;
}

export function Sidebar({ onNewIndex, onCloseMobile, isMobile = false }: SidebarProps) {
  const location = useLocation();
  const {
    health,
    backendOnline,
    engineState,
    providerIdentity,
    activeModel,
    configuredModel,
    activeModelState,
    lastExecutingModel,
    cogneeState,
    cogneeInitialized,
    fetchDashboardStats,
    pollHealth,
  } = useHealthStore();

  const [refreshing, setRefreshing] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchDashboardStats(), pollHealth()]);
    setTimeout(() => setRefreshing(false), 500);
  };

  const ramUsed = health?.ram_used_gb ?? 0;
  const ramTotal = health?.ram_total_gb ?? 16;
  const vramUsed = health?.vram_used_gb ?? 0;
  const vramTotal = health?.vram_total_gb ?? 0;
  const cpuPct = health?.cpu_percent ?? 0;

  const isHealthy = engineState === "healthy";
  const isDegraded = engineState === "degraded";

  const engineLabel = isHealthy
    ? "Engine ready"
    : isDegraded
    ? "Engine degraded"
    : backendOnline
    ? "Engine unavailable"
    : "Engine offline";

  const providerLabel =
    providerIdentity === "lmstudio"
      ? "LM Studio"
      : providerIdentity === "ollama"
      ? "Ollama"
      : providerIdentity === "openai_compatible"
      ? "OpenAI Compatible"
      : providerIdentity
      ? providerIdentity.charAt(0).toUpperCase() + providerIdentity.slice(1)
      : "Local";

  const handleNavClick = () => {
    if (isMobile && onCloseMobile) {
      onCloseMobile();
    }
  };

  return (
    <aside
      className={cn(
        "h-screen bg-black border-r border-[#1e1e1e] flex flex-col z-40 select-none",
        isMobile
          ? "w-[260px] max-w-[85vw] shadow-2xl"
          : "w-[240px] fixed left-0 top-0 hidden lg:flex"
      )}
    >
      {/* Brand Header — Aligned with TopBar height */}
      <div className="h-13 sm:h-14 px-4.5 border-b border-[#1a1a1a] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs shrink-0 shadow-xs">
            <Layers className="w-3.5 h-3.5" />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-white tracking-tight">
              RE:Track
            </span>
            <span className="text-[10px] text-neutral-500 font-mono">
              v0.1
            </span>
          </div>
        </div>

        {isMobile && (
          <button
            onClick={onCloseMobile}
            className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-[#141414] transition-colors cursor-pointer"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Primary Action Button */}
      <div className="px-3.5 pt-3.5 pb-2 shrink-0">
        <button
          onClick={() => {
            if (isMobile && onCloseMobile) onCloseMobile();
            onNewIndex?.();
          }}
          className="w-full h-9 rounded-lg bg-white text-black font-medium text-xs flex items-center justify-center gap-1.5 hover:bg-neutral-200 transition-colors shadow-xs cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-black stroke-[2.5]" />
          <span>Index Repository</span>
        </button>
      </div>

      {/* 4-Pillar Navigation Links */}
      <ScrollArea className="flex-1 px-3 py-2">
        <div className="space-y-1">
          {navItems.map((item) => {
            const active = item.match(location.pathname);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={handleNavClick}
                className={cn(
                  "flex items-center justify-between px-3 py-2.5 rounded-lg text-xs group transition-colors",
                  active
                    ? "bg-[#181818] text-white font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white hover:bg-[#121212]"
                )}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <item.icon
                    className={cn(
                      "w-4 h-4 shrink-0 transition-colors",
                      active
                        ? "text-white"
                        : "text-neutral-500 group-hover:text-neutral-300"
                    )}
                  />
                  <div className="min-w-0">
                    <div className="truncate font-medium leading-tight">
                      {item.label}
                    </div>
                    <div className="text-[10px] text-neutral-500 font-mono truncate leading-none mt-0.5">
                      {item.description}
                    </div>
                  </div>
                </div>
                {active && (
                  <span className="w-1.5 h-1.5 rounded-full bg-white shrink-0 ml-1" />
                )}
              </NavLink>
            );
          })}
        </div>
      </ScrollArea>

      {/* Provider Runtime Truth Deck (Footer) */}
      <div className="p-3 border-t border-[#1a1a1a] bg-[#050505] space-y-2 shrink-0">
        {/* Header: Engine Status & Telemetry Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={cn(
                "w-2 h-2 rounded-full shrink-0",
                isHealthy
                  ? "bg-emerald-400"
                  : isDegraded
                  ? "bg-amber-400"
                  : "bg-red-500"
              )}
            />
            <div className="min-w-0">
              <div className="text-xs font-semibold text-neutral-200 truncate">
                {engineLabel}
              </div>
              <div className="text-[10px] text-neutral-500 font-mono truncate">
                {providerLabel}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={handleRefresh}
              className="text-neutral-500 hover:text-white p-1 rounded hover:bg-[#141414] transition-colors cursor-pointer"
              title="Refresh telemetry"
              aria-label="Refresh telemetry"
            >
              <RefreshCw className={cn("w-3 h-3", refreshing && "animate-spin text-white")} />
            </button>
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-neutral-500 hover:text-white p-1 rounded hover:bg-[#141414] transition-colors cursor-pointer"
              title={showDetails ? "Hide telemetry details" : "Show telemetry details"}
              aria-label={showDetails ? "Hide telemetry details" : "Show telemetry details"}
            >
              {showDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* 3 Independent Runtime Identities */}
        <div className="rounded-md border border-[#1a1a1a] bg-[#0a0a0a] p-2 space-y-1.5 text-[10px] font-mono">
          {/* Configured Identity */}
          <div className="flex items-start justify-between gap-1">
            <span className="text-neutral-500 uppercase tracking-wider shrink-0 text-[9px]">
              Configured:
            </span>
            <span className="text-neutral-300 truncate max-w-[130px] text-right" title={configuredModel || "None"}>
              {configuredModel || "None"}
            </span>
          </div>

          {/* Verified Active Identity */}
          <div className="flex items-start justify-between gap-1">
            <span className="text-neutral-500 uppercase tracking-wider shrink-0 text-[9px]">
              Verified Active:
            </span>
            <span
              className={cn(
                "truncate max-w-[130px] text-right font-medium",
                activeModel ? "text-emerald-400" : "text-neutral-500"
              )}
              title={activeModel ? `${activeModel} (${activeModelState})` : "None verified"}
            >
              {activeModel ? `${activeModel}` : "None verified"}
            </span>
          </div>

          {/* Executing Identity */}
          <div className="flex items-start justify-between gap-1">
            <span className="text-neutral-500 uppercase tracking-wider shrink-0 text-[9px]">
              Last Executing:
            </span>
            <span
              className={cn(
                "truncate max-w-[130px] text-right",
                lastExecutingModel ? "text-cyan-400 font-medium" : "text-neutral-500"
              )}
              title={lastExecutingModel || "None (Idle)"}
            >
              {lastExecutingModel || "None (Idle)"}
            </span>
          </div>
        </div>

        {/* Collapsible Hardware Telemetry */}
        {showDetails && (
          <div className="pt-2 border-t border-[#181818] space-y-1 text-[10px] font-mono text-neutral-400">
            <div className="flex items-center justify-between">
              <span className="text-neutral-500">RAM</span>
              <span className="text-neutral-200">
                {ramUsed > 0 ? ramUsed.toFixed(1) : "--"} / {ramTotal.toFixed(0)} GB
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-neutral-500">CPU</span>
              <span className="text-neutral-200">{cpuPct > 0 ? `${cpuPct}%` : "Idle"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-neutral-500">VRAM</span>
              <span className="text-neutral-200">
                {vramTotal > 0 ? `${vramUsed.toFixed(1)} / ${vramTotal.toFixed(0)} GB` : "None"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-neutral-500">Device</span>
              <span className="text-neutral-200">{health?.execution_device || "Unavailable"}</span>
            </div>
            <div className="flex items-center justify-between pt-1 border-t border-[#181818]">
              <span className="text-neutral-500">Cognee</span>
              <span className={cn(cogneeInitialized || cogneeState === "healthy" ? "text-emerald-400" : "text-neutral-500")}>
                {cogneeInitialized || cogneeState === "healthy" ? "ready" : "offline"}
              </span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
