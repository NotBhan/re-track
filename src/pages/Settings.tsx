import { TopBar } from "@/components/layout/TopBar";
import { SettingsNav } from "@/components/settings/SettingsNav";
import { BackendSettings } from "@/components/settings/BackendSettings";
import { CogneeSettings } from "@/components/settings/CogneeSettings";
import { OllamaSettings } from "@/components/settings/OllamaSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { useSettingsStore } from "@/stores/settings-store";

const tabComponents: Record<string, React.FC> = {
  backend: BackendSettings,
  cognee: CogneeSettings,
  ollama: OllamaSettings,
  storage: StorageSettings,
  theme: () => (
    <div>
      <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface mb-2">
        Theme
      </h2>
      <p className="text-[14px] leading-[20px] text-on-surface-variant">
        Theme settings coming soon. The application currently uses dark mode.
      </p>
    </div>
  ),
  about: () => (
    <div>
      <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface mb-2">
        About
      </h2>
      <p className="text-[14px] leading-[20px] text-on-surface-variant mb-4">
        RE:Track (RefinedEngine Track) v0.1.0
      </p>
      <p className="text-[14px] leading-[20px] text-on-surface-variant">
        Local-first AI memory for software development. Transform repository
        knowledge into structured context for coding assistants.
      </p>
    </div>
  ),
};

export default function Settings() {
  const { activeTab } = useSettingsStore();
  const ActiveContent = tabComponents[activeTab] || BackendSettings;

  return (
    <>
      <TopBar />
      <main className="flex-1 flex bg-background h-full overflow-hidden">
        <SettingsNav />
        <div className="flex-1 h-full overflow-y-auto p-8 lg:p-12">
          <div className="max-w-3xl mx-auto">
            <ActiveContent />
          </div>
        </div>
      </main>
    </>
  );
}
