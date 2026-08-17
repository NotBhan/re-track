import { ReactNode } from "react";
import { useHealthStore } from "@/stores/health-store";
import { Badge } from "@/components/ui/badge";
import { useLayout } from "./LayoutContext";
import { Menu, Layers } from "lucide-react";

interface TopBarProps {
  title?: string;
  subtitle?: string;
  children?: ReactNode;
}

export function TopBar({ title, subtitle, children }: TopBarProps) {
  const { backendOnline, status, ollamaRunning } = useHealthStore();
  const { toggleMobileMenu } = useLayout();

  const llmModel = status?.llm_model?.split(":")[0] || "phi-4-mini";
  const engineOk = backendOnline && ollamaRunning;

  return (
    <header className="h-14 w-full sticky top-0 z-30 bg-black/90 backdrop-blur-md flex items-center justify-between px-4 sm:px-6 border-b border-[#222222]">
      {/* Left: Mobile Menu Trigger + Minimal Title / Workspace Pill */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={toggleMobileMenu}
          className="lg:hidden p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-[#141414] transition-colors -ml-1 cursor-pointer"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 min-w-0">
          <div className="lg:hidden w-6 h-6 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs shrink-0">
            <Layers className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-white tracking-tight truncate">
              {title || "RE:Track"}
            </h2>
            {subtitle && (
              <p className="text-[10px] font-mono text-neutral-400 truncate hidden sm:block">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {children && <div className="hidden md:flex items-center gap-2 ml-2">{children}</div>}
      </div>

      {/* Right: Engine Telemetry & Status Badges */}
      <div className="flex items-center gap-2 shrink-0">
        <Badge
          variant="outline"
          className="hidden sm:inline-flex text-[11px] font-mono px-2.5 py-0.5 border-[#2a2a2a] bg-[#0c0c0c] text-neutral-300"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-2 inline-block shadow-[0_0_6px_#34d399]" />
          {llmModel}
        </Badge>

        <Badge
          variant="outline"
          className={`text-[10px] font-mono uppercase px-2.5 py-0.5 border ${
            engineOk
              ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10 shadow-[0_0_8px_rgba(52,211,153,0.15)]"
              : backendOnline
              ? "border-amber-500/30 text-amber-400 bg-amber-500/10"
              : "border-red-500/30 text-red-400 bg-red-500/10"
          }`}
        >
          {engineOk ? "Engine Online" : backendOnline ? "Degraded" : "Offline"}
        </Badge>
      </div>
    </header>
  );
}
