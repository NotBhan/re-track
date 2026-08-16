import { TopBar } from "@/components/layout/TopBar";
import { SettingsNav } from "@/components/settings/SettingsNav";
import { BackendSettings } from "@/components/settings/BackendSettings";
import { CogneeSettings } from "@/components/settings/CogneeSettings";
import { OllamaSettings } from "@/components/settings/OllamaSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { useSettingsStore } from "@/stores/settings-store";
import { Badge } from "@/components/ui/badge";

const tabComponents: Record<string, React.FC> = {
  backend: BackendSettings,
  cognee: CogneeSettings,
  ollama: OllamaSettings,
  storage: StorageSettings,
  theme: () => (
    <div className="space-y-2">
      <h2 className="text-base font-bold text-foreground">
        Appearance & Theme
      </h2>
      <p className="text-xs text-muted-foreground">
        The application is optimized for standard high-contrast dark mode.
      </p>
    </div>
  ),
  about: () => (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="text-base font-bold text-foreground">
          About RE:Track
        </h2>
        <Badge variant="secondary" className="text-xs font-mono">
          v0.1.0
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">
        High-Performance local-first AI context engine for software engineering agents.
        Transforms repository graphs and semantic memories into token-budgeted Markdown packages.
      </p>
    </div>
  ),
};

export default function Settings() {
  const { activeTab } = useSettingsStore();
  const ActiveContent = tabComponents[activeTab] || BackendSettings;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground">
      <TopBar title="RE:Track | Settings & Engine Models" />
      <main className="flex-1 flex bg-background overflow-hidden">
        <SettingsNav />
        <div className="flex-1 h-full overflow-y-auto p-6 lg:p-8">
          <div className="max-w-3xl">
            <ActiveContent />
          </div>
        </div>
      </main>
    </div>
  );
}
