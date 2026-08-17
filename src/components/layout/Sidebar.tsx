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
  HardDrive,
  Cpu,
  Activity,
  RefreshCw,
  Zap,
  Network,
  X,
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

/** Compact status dot with optional glow */
function StatusDot({ online }: { online: boolean }) {
  return (
    <span
      className={cn(
        "inline-block w-1.5 h-1.5 rounded-full flex-shrink-0",
        online
          ? "bg-emerald-400 shadow-[0_0_6px_#34d399]"
          : "bg-neutral-600"
      )}
    />
  );
}

/** One provider row inside the telemetry deck */
function ProviderRow({
  icon: Icon,
  label,
  detail,
  online,
}: {
  icon: React.ElementType;
  label: string;
  detail?: string;
  online: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-1.5 text-[10px] text-neutral-400 min-w-0">
        <Icon className="w-3 h-3 text-neutral-500 flex-shrink-0" />
        <span className="truncate">{label}</span>
        {detail && (
          <span className="truncate text-neutral-600 hidden sm:block">{detail}</span>
        )}
      </div>
      <div className="flex items-center gap-1 flex-shrink-0">
        <StatusDot online={online} />
        <span
          className={cn(
            "text-[10px] font-mono",
            online ? "text-emerald-400" : "text-neutral-600"
          )}
        >
          {online ? "online" : "offline"}
        </span>
      </div>
    </div>
  );
}

export function Sidebar({ onNewIndex, onCloseMobile, isMobile = false }: SidebarProps) {
  const { health, status, backendOnline, ollamaRunning, cogneeIdle, fetchDashboardStats, pollHealth } =
    useHealthStore();
  const [refreshing, setRefreshing] = useState(false);

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

  // Model labels from BackendStatusResponse (trimmed for display)
  const llmModel = status?.llm_model?.split(":")[0] ?? "";
  const embedModel = status?.embedding_model?.split(":")[0] ?? "";

  // Overall engine status
  const engineOk = backendOnline && ollamaRunning;

  const handleNavClick = () => {
    if (isMobile && onCloseMobile) {
      onCloseMobile();
    }
  };

  return (
    <aside
      className={cn(
        "h-screen bg-black border-r border-[#222222] flex flex-col z-40 select-none",
        isMobile
          ? "w-[280px] max-w-[85vw] shadow-2xl"
          : "w-[260px] fixed left-0 top-0 hidden lg:flex"
      )}
    >
      {/* Brand Header */}
      <div className="p-5 pb-4 border-b border-[#1c1c1c] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white text-black flex items-center justify-center font-bold text-sm tracking-tighter shadow-md">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white tracking-tight">
                RE:Track
              </span>
              <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-[#1f1f1f] text-neutral-400 border border-[#2f2f2f]">
                v0.1
              </span>
            </div>
            <span className="text-[11px] font-mono text-neutral-400 block">
              Context Engine
            </span>
          </div>
        </div>

        {isMobile && (
          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-[#1f1f1f] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Primary Action Button */}
      <div className="p-3.5 pb-2">
        <button
          onClick={() => {
            if (isMobile && onCloseMobile) onCloseMobile();
            onNewIndex?.();
          }}
          className="w-full h-10 rounded-lg bg-white text-black font-semibold text-xs flex items-center justify-center gap-2 hover:bg-neutral-200 transition-colors shadow-sm font-mono tracking-tight cursor-pointer"
        >
          <Plus className="w-4 h-4 text-black stroke-[2.5]" />
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
                  "flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium group select-none transition-all",
                  isActive
                    ? "bg-[#141414] text-white font-semibold border border-[#2a2a2a] shadow-xs"
                    : "text-neutral-400 hover:text-white hover:bg-[#0f0f0f] border border-transparent"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <div className="flex items-center gap-3">
                    <item.icon
                      className={cn(
                        "w-4 h-4 transition-colors",
                        isActive
                          ? "text-white"
                          : "text-neutral-400 group-hover:text-white"
                      )}
                    />
                    <span>{item.label}</span>
                  </div>
                  {isActive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-white shadow-[0_0_6px_#ffffff]" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </ScrollArea>

      {/* Telemetry Hardware Deck */}
      <div className="p-4 border-t border-[#1c1c1c] bg-[#080808] space-y-3">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                engineOk
                  ? "bg-emerald-400 shadow-[0_0_8px_#34d399]"
                  : backendOnline
                  ? "bg-amber-400 shadow-[0_0_8px_#fbbf24]"
                  : "bg-red-500"
              )}
            />
            <span className="text-white font-semibold text-[11px] font-mono">
              Engine Core
            </span>
            <span
              className={cn(
                "text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border",
                engineOk
                  ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                  : backendOnline
                  ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
                  : "text-neutral-500 border-neutral-700 bg-neutral-900"
              )}
            >
              {engineOk ? "Ready" : backendOnline ? "Degraded" : "Offline"}
            </span>
          </div>

          <button
            onClick={handleRefresh}
            className="text-neutral-400 hover:text-white p-1 rounded-md hover:bg-[#1f1f1f] transition-colors cursor-pointer"
            title="Refresh engine & hardware metrics"
          >
            <RefreshCw className={cn("w-3 h-3", refreshing && "animate-spin text-white")} />
          </button>
        </div>

        {/* AI provider status rows */}
        <div className="rounded-lg bg-[#0e0e0e] border border-[#222222] px-2.5 py-1.5 space-y-0.5 font-mono">
          <ProviderRow
            icon={Zap}
            label={llmModel ? `Ollama · ${llmModel}` : "Ollama"}
            online={ollamaRunning}
          />
          <div className="border-t border-[#1a1a1a]" />
          <ProviderRow
            icon={Network}
            label={embedModel ? `Embed · ${embedModel}` : "Embeddings"}
            online={ollamaRunning && !!embedModel}
          />
          <div className="border-t border-[#1a1a1a]" />
          <ProviderRow
            icon={Brain}
            label="Cognee"
            online={!!cogneeIdle}
          />
        </div>

        {/* Hardware telemetry grid */}
        <div className="space-y-1.5 font-mono text-[11px]">
          <div className="grid grid-cols-2 gap-1.5">
            <div className="p-2 rounded-lg bg-[#0e0e0e] border border-[#222222] flex flex-col gap-0.5">
              <div className="flex items-center gap-1.5 text-neutral-400 text-[10px]">
                <HardDrive className="w-3 h-3 text-neutral-300" />
                <span>RAM</span>
              </div>
              <div className="text-white font-bold">
                {ramUsed > 0 ? ramUsed.toFixed(1) : "--"}{" "}
                <span className="text-neutral-400 font-normal text-[10px]">/ {ramTotal.toFixed(0)}G</span>
              </div>
            </div>

            <div className="p-2 rounded-lg bg-[#0e0e0e] border border-[#222222] flex flex-col gap-0.5">
              <div className="flex items-center gap-1.5 text-neutral-400 text-[10px]">
                <Activity className="w-3 h-3 text-neutral-300" />
                <span>CPU</span>
              </div>
              <div className="text-white font-bold">
                {cpuPct > 0 ? `${cpuPct}%` : "Idle"}
              </div>
            </div>
          </div>

          <div className="p-2 rounded-lg bg-[#0e0e0e] border border-[#222222] flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-neutral-400 text-[10px]">
              <Cpu className="w-3 h-3 text-neutral-300" />
              <span>VRAM (GPU)</span>
            </div>
            <div className="text-white font-bold">
              {vramTotal > 0
                ? `${vramUsed.toFixed(1)} / ${vramTotal.toFixed(0)}G`
                : "-- / -- GB"}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
