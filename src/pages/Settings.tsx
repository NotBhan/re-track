import { TopBar } from "@/components/layout/TopBar";
import { SettingsNav } from "@/components/settings/SettingsNav";
import { BackendSettings } from "@/components/settings/BackendSettings";
import { CogneeSettings } from "@/components/settings/CogneeSettings";
import { OllamaSettings } from "@/components/settings/OllamaSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { useSettingsStore } from "@/stores/settings-store";
import { Badge } from "@/components/ui/badge";
import { Moon, Monitor, Laptop, Check } from "lucide-react";

function ThemeSettingsView() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white tracking-tight mb-0.5">
          Appearance &amp; Theme
        </h2>
        <p className="text-xs text-neutral-500">
          Customize interface styling, contrast, and font rendering.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-4">
        <label className="text-xs font-medium text-neutral-200 block">
          Active Color Scheme
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3.5 rounded-lg bg-black border border-white flex flex-col gap-1.5 cursor-pointer shadow-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-white">
                <Moon className="w-3.5 h-3.5" />
                <span className="text-xs font-semibold">Geist Dark</span>
              </div>
              <Check className="w-3.5 h-3.5 text-white" />
            </div>
            <p className="text-xs text-neutral-400">
              Pure black `#000000` canvas with high contrast borders and Geist Mono.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-[#080808] border border-[#1e1e1e] opacity-50 flex flex-col gap-1.5 cursor-not-allowed">
            <div className="flex items-center gap-1.5 text-neutral-400">
              <Laptop className="w-3.5 h-3.5" />
              <span className="text-xs font-semibold">OLED Slate</span>
            </div>
            <p className="text-xs text-neutral-500">
              Deep slate tones for AMOLED displays (Coming soon).
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-[#080808] border border-[#1e1e1e] opacity-50 flex flex-col gap-1.5 cursor-not-allowed">
            <div className="flex items-center gap-1.5 text-neutral-400">
              <Monitor className="w-3.5 h-3.5" />
              <span className="text-xs font-semibold">System Default</span>
            </div>
            <p className="text-xs text-neutral-500">
              Syncs with operating system theme preferences.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function AboutSettingsView() {
  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <h2 className="text-sm font-semibold text-white tracking-tight">
            About RE:Track
          </h2>
          <Badge variant="outline" className="text-[10px] font-mono">
            v0.1.0-alpha
          </Badge>
        </div>
        <p className="text-xs text-neutral-500">
          RefinedEngine Track — Local-First Intelligent Code Context Engine
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-3">
        <p className="text-xs text-neutral-300 leading-relaxed">
          RE:Track is an autonomous context orchestration layer designed for pair-programming agents and developers. It indexes repositories into embedded vector embeddings (LanceDB) and property graph structures (Kùzu), synthesizes multi-layer AST call graphs, and produces token-budgeted Markdown context packages for high-precision code generation.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#181818] font-mono text-xs">
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">Architecture</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">Tauri + FastAPI</div>
          </div>
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">Vector Store</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">LanceDB Local</div>
          </div>
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">Graph DB</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">Kùzu Embedded</div>
          </div>
          <div className="p-2.5 bg-[#050505] rounded-md border border-[#1a1a1a]">
            <div className="text-[10px] text-neutral-500">License</div>
            <div className="text-xs font-semibold text-neutral-200 mt-0.5">MIT Open Source</div>
          </div>
        </div>
      </div>
    </div>
  );
}

const tabComponents: Record<string, React.FC> = {
  backend: BackendSettings,
  cognee: CogneeSettings,
  ollama: OllamaSettings,
  storage: StorageSettings,
  theme: ThemeSettingsView,
  about: AboutSettingsView,
};

export default function Settings() {
  const { activeTab } = useSettingsStore();
  const ActiveContent = tabComponents[activeTab] || BackendSettings;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-black text-foreground antialiased">
      <TopBar title="RE:Track | Settings &amp; Engine Models" subtitle="Preferences &amp; Providers" />
      <main className="flex-1 flex flex-col md:flex-row bg-black overflow-hidden">
        <SettingsNav />
        <div className="flex-1 h-full overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-3xl mx-auto md:mx-0">
            <ActiveContent />
          </div>
        </div>
      </main>
    </div>
  );
}
