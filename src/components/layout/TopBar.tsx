import { ReactNode } from "react";
import { useHealthStore } from "@/stores/health-store";
import { cn } from "@/lib/utils";
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
    <header className="h-13 sm:h-14 w-full sticky top-0 z-30 bg-black/95 backdrop-blur-md flex items-center justify-between px-4 sm:px-6 border-b border-[#1e1e1e] select-none shrink-0">
      {/* Group A: Mobile Menu Trigger + Brand/Title/Subtitle */}
      <div className="flex items-center gap-3 sm:gap-4 min-w-0 flex-1 mr-3 sm:mr-4">
        <button
          onClick={toggleMobileMenu}
          className="lg:hidden p-1.5 rounded-md text-neutral-400 hover:text-white hover:bg-[#141414] transition-colors -ml-1 cursor-pointer shrink-0"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2.5 min-w-0">
          <div className="lg:hidden w-5 h-5 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs shrink-0">
            <Layers className="w-3 h-3" />
          </div>
          <div className="min-w-0 flex flex-col justify-center">
            <h2 className="text-xs sm:text-[13px] font-semibold text-white tracking-tight truncate leading-tight">
              {title || "RE:Track"}
            </h2>
            {subtitle && (
              <p className="text-[10px] sm:text-[11px] text-neutral-500 font-mono truncate hidden sm:block mt-0.5 leading-none">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Group B: Contextual Actions & Workspace Switcher */}
        {children && (
          <div className="flex items-center gap-2 sm:gap-3 ml-2 sm:ml-4 pl-2 sm:pl-4 border-l border-[#222222]">
            {children}
          </div>
        )}
      </div>

      {/* Group C: Engine Status & Telemetry */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#222222] bg-[#0a0a0a] text-[11px] font-mono text-neutral-300 shadow-xs">
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full shrink-0",
              engineOk ? "bg-emerald-400" : backendOnline ? "bg-amber-400" : "bg-red-500"
            )}
          />
          <span className="truncate max-w-[90px] sm:max-w-[140px]">{llmModel}</span>
          <span className="text-neutral-600 hidden xs:inline">·</span>
          <span className={cn("hidden xs:inline", engineOk ? "text-neutral-400" : "text-amber-400")}>
            {engineOk ? "Ready" : backendOnline ? "Degraded" : "Offline"}
          </span>
        </div>
      </div>
    </header>
  );
}

