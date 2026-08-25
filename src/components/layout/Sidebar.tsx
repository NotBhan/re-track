import { NavLink } from "react-router-dom";
import { useState } from "react";
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  Brain,
  BarChart3,
  Settings,
  Plus,
  Layers,
  RefreshCw,
  X,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useHealthStore } from "@/stores/health-store";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: FolderOpen, label: "Repositories" },
  { to: "/studio", icon: LayoutDashboard, label: "Context Studio" },
  { to: "/packages", icon: FileText, label: "Context Packages" },
  { to: "/memory", icon: Brain, label: "Memory Graph" },
  { to: "/benchmarks", icon: BarChart3, label: "Benchmarks" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

interface SidebarProps {
  onNewIndex?: () => void;
  onCloseMobile?: () => void;
  isMobile?: boolean;
}

export function Sidebar({ onNewIndex, onCloseMobile, isMobile = false }: SidebarProps) {
  const {
    health,
    backendOnline,
    engineState,
    providerIdentity,
    activeModel,
    configuredModel,
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

  const displayModel = activeModel
    ? activeModel.split(":")[0]
    : configuredModel
    ? configuredModel.split(":")[0]
    : "No active model";

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
            className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-[#141414] transition-colors"
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

      {/* Navigation Links */}
      <ScrollArea className="flex-1 px-3 py-2">
        <div className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={handleNavClick}
              className={({ isActive }) =>
                cn(
                  "flex items-center justify-between px-3 py-2.25 rounded-lg text-xs font-normal group transition-colors",
                  isActive
                    ? "bg-[#181818] text-white font-medium shadow-xs"
                    : "text-neutral-400 hover:text-white hover:bg-[#121212]"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <div className="flex items-center gap-2.5">
                    <item.icon
                      className={cn(
                        "w-4 h-4 transition-colors",
                        isActive
                          ? "text-white"
                          : "text-neutral-500 group-hover:text-neutral-300"
                      )}
                    />
                    <span>{item.label}</span>
                  </div>
                  {isActive && (
                    <span className="w-1 h-1 rounded-full bg-white" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </ScrollArea>

      {/* Engine Core Status Deck (Restrained & Calm) */}
      <div className="p-3.5 border-t border-[#1a1a1a] bg-[#050505] space-y-2.5 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={cn(
                "w-1.5 h-1.5 rounded-full shrink-0",
                isHealthy
                  ? "bg-emerald-400"
                  : isDegraded
                  ? "bg-amber-400"
                  : "bg-red-500"
              )}
            />
            <div className="min-w-0">
              <div className="text-xs font-medium text-neutral-200 truncate">
                {engineLabel}
              </div>
              <div className="text-[11px] text-neutral-500 font-mono truncate">
                {displayModel} · {providerLabel}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={handleRefresh}
              className="text-neutral-500 hover:text-white p-1 rounded hover:bg-[#141414] transition-colors cursor-pointer"
              title="Refresh telemetry"
            >
              <RefreshCw className={cn("w-3 h-3", refreshing && "animate-spin text-white")} />
            </button>
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="text-neutral-500 hover:text-white p-1 rounded hover:bg-[#141414] transition-colors cursor-pointer"
              title={showDetails ? "Hide hardware stats" : "Show hardware stats"}
            >
              {showDetails ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* Detailed Hardware Stats (Collapsible/Flattened) */}
        {showDetails && (
          <div className="pt-2 border-t border-[#181818] space-y-1.5 text-[11px] font-mono text-neutral-400">
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
                {vramTotal > 0 ? `${vramUsed.toFixed(1)} / ${vramTotal.toFixed(0)} GB` : "--"}
              </span>
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

