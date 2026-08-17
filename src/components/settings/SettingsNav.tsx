import { useSettingsStore } from "@/stores/settings-store";
import { cn } from "@/lib/utils";
import { Server, Brain, Zap, HardDrive, Palette, Info } from "lucide-react";

const allTabs = [
  { id: "backend", label: "Backend", group: "Config", icon: Server },
  { id: "ollama", label: "Inference", group: "Config", icon: Zap },
  { id: "cognee", label: "Cognee", group: "Config", icon: Brain },
  { id: "storage", label: "Storage", group: "Config", icon: HardDrive },
  { id: "theme", label: "Theme", group: "App", icon: Palette },
  { id: "about", label: "About", group: "App", icon: Info },
];

const configTabs = allTabs.filter((t) => t.group === "Config");
const appTabs = allTabs.filter((t) => t.group === "App");

export function SettingsNav() {
  const { activeTab, setActiveTab } = useSettingsStore();

  return (
    <>
      {/* Mobile Horizontal Scrolling Tabs (< md screens) */}
      <div className="md:hidden w-full border-b border-[#262626] bg-[#050505] p-2 overflow-x-auto flex gap-1.5 shrink-0 scrollbar-none">
        {allTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                "flex items-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-mono font-medium whitespace-nowrap transition-colors cursor-pointer shrink-0",
                isActive
                  ? "text-white bg-[#1a1a1a] border border-[#333333] shadow-xs"
                  : "text-neutral-400 hover:text-white hover:bg-[#121212] border border-transparent"
              )}
            >
              <Icon className={cn("w-3.5 h-3.5", isActive ? "text-white" : "text-neutral-500")} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Desktop Vertical Sidebar (>= md screens) */}
      <div className="hidden md:flex w-[220px] lg:w-[240px] h-full border-r border-[#262626] bg-[#050505] flex-col py-6 px-3 overflow-y-auto select-none shrink-0">
        <h2 className="text-[11px] font-mono font-semibold text-neutral-500 uppercase tracking-wider mb-2.5 px-3">
          Configuration
        </h2>
        <nav className="space-y-1">
          {configTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={cn(
                  "w-full flex items-center gap-2.5 py-2 px-3 rounded-lg text-left transition-colors text-xs font-mono font-medium cursor-pointer",
                  isActive
                    ? "text-white bg-[#1a1a1a] border border-[#333333] shadow-xs"
                    : "text-neutral-400 hover:text-white hover:bg-[#121212] border border-transparent"
                )}
              >
                <Icon className={cn("w-3.5 h-3.5", isActive ? "text-white" : "text-neutral-500")} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        <h2 className="text-[11px] font-mono font-semibold text-neutral-500 uppercase tracking-wider mt-6 mb-2.5 px-3">
          Application
        </h2>
        <nav className="space-y-1">
          {appTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={cn(
                  "w-full flex items-center gap-2.5 py-2 px-3 rounded-lg text-left transition-colors text-xs font-mono font-medium cursor-pointer",
                  isActive
                    ? "text-white bg-[#1a1a1a] border border-[#333333] shadow-xs"
                    : "text-neutral-400 hover:text-white hover:bg-[#121212] border border-transparent"
                )}
              >
                <Icon className={cn("w-3.5 h-3.5", isActive ? "text-white" : "text-neutral-500")} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </>
  );
}
