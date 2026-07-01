import { useSettingsStore } from "@/stores/settings-store";
import { cn } from "@/lib/utils";

const configTabs = [
  { id: "backend", label: "Backend" },
  { id: "cognee", label: "Cognee" },
  { id: "ollama", label: "Ollama" },
  { id: "storage", label: "Storage" },
];
const appTabs = [
  { id: "theme", label: "Theme" },
  { id: "about", label: "About" },
];

export function SettingsNav() {
  const { activeTab, setActiveTab } = useSettingsStore();

  return (
    <div className="w-[220px] h-full border-r border-outline-variant bg-surface/50 flex flex-col py-8 px-4 overflow-y-auto">
      <h2 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-outline uppercase tracking-wider mb-4 px-2">
        Configuration
      </h2>
      <nav className="space-y-1">
        {configTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={cn(
              "w-full flex items-center justify-between py-2 px-3 rounded-md text-left transition-colors text-[14px] leading-[20px]",
              activeTab === tab.id
                ? "text-on-surface bg-surface-container-high font-medium"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <h2 className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-outline uppercase mt-8 mb-4 px-2">
        Application
      </h2>
      <nav className="space-y-1">
        {appTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={cn(
              "w-full flex items-center justify-between py-2 px-3 rounded-md text-left transition-colors text-[14px] leading-[20px]",
              activeTab === tab.id
                ? "text-on-surface bg-surface-container-high font-medium"
                : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
