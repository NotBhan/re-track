import React from "react";
import { Cpu, HardDrive, Zap, Activity } from "lucide-react";
import { useSystemStore } from "../../stores/systemStore";
import { Badge } from "../../components/Badge";

export const TelemetryGauges: React.FC = () => {
  const { health, backendOnline, providerReachable, providerHealthState } = useSystemStore();

  const isOnline = backendOnline && health !== null;

  const cpuDisplay = isOnline && health?.cpu_percent !== undefined
    ? `${health.cpu_percent.toFixed(1)}%`
    : "Unavailable";

  const ramDisplay = isOnline && health?.ram_used_gb !== undefined && health?.ram_total_gb !== undefined
    ? `${health.ram_used_gb.toFixed(1)} / ${health.ram_total_gb.toFixed(1)} GB (${health.ram_percent || 0}%)`
    : "Unavailable";

  const gpuDisplay = isOnline
    ? health?.gpu_presence && health.gpu_presence !== "None"
      ? `${health.gpu_name || health.gpu_presence} (${health.vram_used_gb?.toFixed(1) || 0} GB VRAM)`
      : "None detected"
    : "Unavailable";

  const deviceDisplay = isOnline && health?.execution_device
    ? health.execution_device
    : "Unavailable";

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      {/* Subsystems Health Status */}
      <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-3">
        <h4 className="text-xs font-semibold text-[#a1a1a1] uppercase tracking-wider">
          Runtime Health
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center justify-between">
            <span className="text-xs text-[#a1a1a1]">Backend Server</span>
            <Badge variant={isOnline ? "success" : "danger"}>
              {isOnline ? "Online (8765)" : "Unavailable"}
            </Badge>
          </div>

          <div className="p-3 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center justify-between">
            <span className="text-xs text-[#a1a1a1]">Inference Provider</span>
            <Badge variant={providerReachable ? "success" : "danger"}>
              {providerHealthState || (providerReachable ? "healthy" : "unavailable")}
            </Badge>
          </div>

          <div className="p-3 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center justify-between">
            <span className="text-xs text-[#a1a1a1]">Cognee Pipeline</span>
            <Badge variant={health?.cognee_initialized ? "success" : "default"}>
              {health?.cognee_state || (health?.cognee_initialized ? "ready" : "idle")}
            </Badge>
          </div>
        </div>
      </div>

      {/* Hardware Telemetry Gauges */}
      <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-[#a1a1a1] uppercase tracking-wider">
            Hardware & Resource Telemetry
          </h4>
          <span className="text-[11px] text-[#707070]">Live system metrics</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* CPU Gauge */}
          <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3.5">
            <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] text-[#a1a1a1] font-medium block">CPU Utilization</span>
              <span className="text-sm font-semibold text-[#ededed] font-mono">{cpuDisplay}</span>
            </div>
          </div>

          {/* RAM Gauge */}
          <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3.5">
            <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] text-[#a1a1a1] font-medium block">System RAM</span>
              <span className="text-sm font-semibold text-[#ededed] font-mono">{ramDisplay}</span>
            </div>
          </div>

          {/* GPU Gauge */}
          <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3.5">
            <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] text-[#a1a1a1] font-medium block">GPU Accelerator</span>
              <span className="text-sm font-semibold text-[#ededed] font-mono">{gpuDisplay}</span>
            </div>
          </div>

          {/* Execution Device */}
          <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] flex items-center gap-3.5">
            <div className="p-2 rounded-lg bg-[#121212] text-[#a1a1a1]">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] text-[#a1a1a1] font-medium block">Active Execution Device</span>
              <span className="text-sm font-semibold text-[#ededed] font-mono uppercase">{deviceDisplay}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
