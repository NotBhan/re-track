/**
 * Settings — dedicated first-class configuration surface.
 *
 * Follows the current application patterns: TopBar chrome, an in-page segmented
 * tab row (as used by Workspace / Memory / System & Telemetry), and single-column
 * quiet sections. Only settings backed by the existing implementation are shown;
 * every section delegates to the shared configuration components so behaviour is
 * identical to the System & Telemetry surfaces.
 *
 * Active tab is URL-driven (`/settings?tab=provider|storage|diagnostics`) so the
 * page supports deep links. Legacy tab identifiers are still resolved.
 */

import { useSearchParams } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { OllamaSettings } from "@/components/settings/OllamaSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { CogneeSettings } from "@/components/settings/CogneeSettings";
import { DiagnosticsSettings } from "@/components/settings/DiagnosticsSettings";
import { ConnectivityCheck } from "@/components/settings/ConnectivityCheck";
import { cn } from "@/lib/utils";
import { Cpu, Database, Terminal } from "lucide-react";

export type SettingsTab = "provider" | "storage" | "diagnostics";

const tabs: { id: SettingsTab; label: string; icon: typeof Cpu }[] = [
  { id: "provider", label: "Provider & Runtime", icon: Cpu },
  { id: "storage", label: "Storage & Memory", icon: Database },
  { id: "diagnostics", label: "Diagnostics", icon: Terminal },
];

/** Retired tab identifiers from the previous Settings navigation. */
const LEGACY_TAB_ALIASES: Record<string, SettingsTab> = {
  ollama: "provider",
  inference: "provider",
  cognee: "storage",
  backend: "diagnostics",
};

function resolveTab(raw: string | null): SettingsTab {
  if (!raw) return "provider";
  if (tabs.some((t) => t.id === raw)) return raw as SettingsTab;
  return LEGACY_TAB_ALIASES[raw] ?? "provider";
}

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveTab(searchParams.get("tab"));

  const setTab = (tab: SettingsTab) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", tab);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased font-sans">
      <TopBar
        title="RE:Track | Settings"
        subtitle="Provider, storage and diagnostics"
      />

      <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 lg:p-6">
        <div className="max-w-4xl mx-auto space-y-5">
          {/* Header & Section Switcher */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1a1a1a] pb-4">
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-white">Settings</h1>
              <p className="text-xs text-neutral-500 mt-0.5">
                Configuration is persisted by the local backend and applies immediately.
              </p>
            </div>

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

          {/* SECTION 1: PROVIDER & RUNTIME */}
          {activeTab === "provider" && <OllamaSettings />}

          {/* SECTION 2: STORAGE & MEMORY */}
          {activeTab === "storage" && (
            <div className="space-y-5">
              <StorageSettings />
              <CogneeSettings />
            </div>
          )}

          {/* SECTION 3: DIAGNOSTICS */}
          {activeTab === "diagnostics" && (
            <div className="space-y-5">
              <ConnectivityCheck />
              <DiagnosticsSettings />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
