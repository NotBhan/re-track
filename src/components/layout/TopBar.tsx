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
    <header className="h-12 w-full sticky top-0 z-30 bg-black/95 backdrop-blur-md flex items-center justify-between px-4 sm:px-5 border-b border-[#1e1e1e]">
      {/* Left: Mobile Menu Trigger + Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={toggleMobileMenu}
          className="lg:hidden p-1 rounded-md text-neutral-400 hover:text-white hover:bg-[#141414] transition-colors -ml-1 cursor-pointer"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2.5 min-w-0">
          <div className="lg:hidden w-5 h-5 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs shrink-0">
            <Layers className="w-3 h-3" />
          </div>
          <div className="min-w-0">
            <h2 className="text-xs font-semibold text-white tracking-tight truncate">
              {title || "RE:Track"}
            </h2>
            {subtitle && (
              <p className="text-[11px] text-neutral-500 truncate hidden sm:block">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {children && <div className="hidden md:flex items-center gap-2 ml-2">{children}</div>}
      </div>

      {/* Right: Engine Status */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md border border-[#222222] bg-[#0a0a0a] text-[11px] font-mono text-neutral-300">
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full shrink-0",
              engineOk ? "bg-emerald-400" : backendOnline ? "bg-amber-400" : "bg-red-500"
            )}
          />
          <span>{llmModel}</span>
          <span className="text-neutral-500">·</span>
          <span className={cn(engineOk ? "text-neutral-400" : "text-amber-400")}>
            {engineOk ? "Ready" : backendOnline ? "Degraded" : "Offline"}
          </span>
        </div>
      </div>
    </header>
  );
}
