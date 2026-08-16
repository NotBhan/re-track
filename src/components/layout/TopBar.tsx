import { useState } from "react";
import { Cpu, HardDrive, RefreshCw, Activity, Layers } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface TopBarProps {
  title?: string;
  children?: React.ReactNode;
}

export function TopBar({ title, children }: TopBarProps) {
  const { health, backendOnline, fetchDashboardStats, pollHealth } = useHealthStore();
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

  return (
    <header className="h-14 w-full sticky top-0 z-10 bg-black/90 backdrop-blur-md flex items-center justify-between px-6 border-b border-border">
      {/* Title & Eyebrow */}
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs tracking-tighter">
          <Layers className="w-4 h-4" />
        </div>
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-foreground tracking-tight">
            {title || "RE:Track"}
          </h2>
          <span className="text-xs text-muted-foreground hidden lg:inline font-mono border-l border-border pl-3">
            Local Context Engine
          </span>
        </div>
        {children}
      </div>

      {/* Vercel-style Telemetry Ladder */}
      <div className="flex items-center gap-3">
        {/* Host RAM */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary/80 border border-border text-xs text-muted-foreground font-mono">
          <HardDrive className="w-3.5 h-3.5 text-foreground" />
          <span>
            RAM <strong className="text-foreground">{ramUsed > 0 ? ramUsed.toFixed(1) : "--"}</strong>/{ramTotal.toFixed(1)} GB
          </span>
        </div>

        {/* Host CPU */}
        <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary/80 border border-border text-xs text-muted-foreground font-mono">
          <Activity className="w-3.5 h-3.5 text-foreground" />
          <span>CPU <strong className="text-foreground">{cpuPct > 0 ? `${cpuPct}%` : "Idle"}</strong></span>
        </div>

        {/* VRAM Gauge */}
        {vramTotal > 0 ? (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary/80 border border-border text-xs text-muted-foreground font-mono">
            <Cpu className="w-3.5 h-3.5 text-foreground" />
            <span>VRAM <strong className="text-foreground">{vramUsed.toFixed(1)}</strong>/{vramTotal.toFixed(1)} GB</span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary/80 border border-border text-xs text-muted-foreground font-mono">
            <Cpu className="w-3.5 h-3.5 text-foreground" />
            <span>VRAM <strong className="text-foreground">0.0</strong>/-- GB</span>
          </div>
        )}

        {/* Active Model Pill */}
        <Badge variant="outline" className="text-xs font-mono px-3 py-1 bg-secondary/60 border-border text-foreground">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 inline-block shadow-[0_0_6px_#10b981]" />
          phi-4-mini
        </Badge>

        {/* Engine Status */}
        <Badge variant={backendOnline ? "secondary" : "destructive"} className="text-xs font-mono px-3 py-1">
          {backendOnline ? "Core Online" : "Core Offline"}
        </Badge>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-md"
          title="Refresh Telemetry"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
        </Button>
      </div>
    </header>
  );
}
