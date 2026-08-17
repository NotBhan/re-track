import { TopBar } from "@/components/layout/TopBar";
import { SettingsNav } from "@/components/settings/SettingsNav";
import { BackendSettings } from "@/components/settings/BackendSettings";
import { CogneeSettings } from "@/components/settings/CogneeSettings";
import { OllamaSettings } from "@/components/settings/OllamaSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { useSettingsStore } from "@/stores/settings-store";
import { Badge } from "@/components/ui/badge";
import { Moon, Monitor, Laptop, ShieldCheck, Check } from "lucide-react";

function ThemeSettingsView() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight mb-1">
          Appearance &amp; Theme
        </h2>
        <p className="text-xs text-neutral-400">
          Customize interface styling, contrast, and font rendering.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 space-y-5 shadow-2xl">
        <label className="text-xs font-mono font-medium text-white block">
          Active Color Scheme
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-4 rounded-xl bg-black border-2 border-white flex flex-col gap-2 cursor-pointer shadow-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-white">
                <Moon className="w-4 h-4" />
                <span className="text-xs font-mono font-bold">Vercel Geist Dark</span>
              </div>
              <Check className="w-4 h-4 text-white" />
            </div>
            <p className="text-[11px] text-neutral-400 font-mono">
              Pure black `#000000` canvas with high contrast borders and Geist Mono.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#0e0e0e] border border-[#262626] opacity-60 flex flex-col gap-2 cursor-not-allowed">
            <div className="flex items-center gap-2 text-neutral-400">
              <Laptop className="w-4 h-4" />
              <span className="text-xs font-mono font-bold">OLED Slate</span>
            </div>
            <p className="text-[11px] text-neutral-500 font-mono">
              Deep slate tones for AMOLED displays (Coming soon).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#0e0e0e] border border-[#262626] opacity-60 flex flex-col gap-2 cursor-not-allowed">
            <div className="flex items-center gap-2 text-neutral-400">
              <Monitor className="w-4 h-4" />
              <span className="text-xs font-mono font-bold">System Default</span>
            </div>
            <p className="text-[11px] text-neutral-500 font-mono">
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
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h2 className="text-xl font-bold text-white tracking-tight">
            About RE:Track
          </h2>
          <Badge variant="outline" className="text-xs font-mono border-[#333333] bg-black text-neutral-300">
            v0.1.0-alpha
          </Badge>
        </div>
        <p className="text-xs text-neutral-400">
          RefinedEngine Track — Local-First Intelligent Code Context Engine
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 space-y-4 shadow-2xl">
        <p className="text-xs text-neutral-300 leading-relaxed font-mono">
          RE:Track is an autonomous context orchestration layer designed for pair-programming agents and developers. It indexes repositories into embedded vector embeddings (LanceDB) and property graph structures (Kùzu), synthesizes multi-layer AST call graphs, and produces token-budgeted Markdown context packages for high-precision code generation.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-[#1c1c1c]">
          <div className="p-3 bg-black rounded-lg border border-[#222222]">
            <div className="text-[10px] font-mono uppercase text-neutral-500">Architecture</div>
            <div className="text-xs font-mono font-bold text-white mt-0.5">Tauri + FastAPI</div>
          </div>
          <div className="p-3 bg-black rounded-lg border border-[#222222]">
            <div className="text-[10px] font-mono uppercase text-neutral-500">Vector Store</div>
            <div className="text-xs font-mono font-bold text-white mt-0.5">LanceDB Local</div>
          </div>
          <div className="p-3 bg-black rounded-lg border border-[#222222]">
            <div className="text-[10px] font-mono uppercase text-neutral-500">Graph DB</div>
            <div className="text-xs font-mono font-bold text-white mt-0.5">Kùzu Embedded</div>
          </div>
          <div className="p-3 bg-black rounded-lg border border-[#222222]">
            <div className="text-[10px] font-mono uppercase text-neutral-500">License</div>
            <div className="text-xs font-mono font-bold text-white mt-0.5 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>MIT</span>
            </div>
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
