import React from "react";
import { Settings2, Cpu, Activity, Database, FileText, Gauge } from "lucide-react";
import { useSystemStore, type SystemTab } from "../../stores/systemStore";
import { ProviderSettings } from "./ProviderSettings";
import { TelemetryGauges } from "./TelemetryGauges";
import { StorageSettings } from "./StorageSettings";
import { DiagnosticsViewer } from "./DiagnosticsViewer";
import { BenchmarkRunner } from "./BenchmarkRunner";
import { DisplaySettings } from "./DisplaySettings";
import { Tabs } from "../../components/Tabs";
import { Monitor } from "lucide-react";

export const SystemHub: React.FC = () => {
  const { activeTab, setActiveTab } = useSystemStore();

  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 bg-[#000000]">
      {/* Top Header */}
      <div className="pb-5 border-b border-[#262626]">
        <h2 className="text-xl font-bold tracking-tight text-[#ededed] flex items-center gap-2">
          <Settings2 className="w-5 h-5 text-[#a1a1a1]" />
          <span>System & Settings</span>
        </h2>
        <p className="text-xs text-[#a1a1a1] mt-0.5">
          Configure inference runtimes, inspect hardware telemetry, manage storage, adjust UI scaling, and audit diagnostics.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-col gap-5">
        <Tabs
          items={[
            { id: "providers", label: "Providers & Models", icon: <Cpu className="w-3.5 h-3.5" /> },
            { id: "telemetry", label: "Hardware Telemetry", icon: <Activity className="w-3.5 h-3.5" /> },
            { id: "storage", label: "Storage & Pipeline", icon: <Database className="w-3.5 h-3.5" /> },
            { id: "display", label: "Display & Scaling", icon: <Monitor className="w-3.5 h-3.5" /> },
            { id: "diagnostics", label: "Diagnostics", icon: <FileText className="w-3.5 h-3.5" /> },
            { id: "benchmarks", label: "Benchmarks", icon: <Gauge className="w-3.5 h-3.5" /> },
          ]}
          activeId={activeTab}
          onChange={(id) => setActiveTab(id as SystemTab)}
        />

        {activeTab === "providers" && <ProviderSettings />}
        {activeTab === "telemetry" && <TelemetryGauges />}
        {activeTab === "storage" && <StorageSettings />}
        {activeTab === "display" && <DisplaySettings />}
        {activeTab === "diagnostics" && <DiagnosticsViewer />}
        {activeTab === "benchmarks" && <BenchmarkRunner />}
      </div>
    </div>
  );
};
