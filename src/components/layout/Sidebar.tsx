import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderOpen,
  Sparkles,
  FileText,
  Brain,
  BarChart3,
  Settings,
  Plus,
  Cpu,
  Database,
  Activity,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StatusDot } from "@/components/shared/StatusDot";
import { useHealthStore } from "@/stores/health-store";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/repositories", icon: FolderOpen, label: "Repositories" },
  { to: "/context-builder", icon: Sparkles, label: "Context Builder" },
  { to: "/packages", icon: FileText, label: "Packages" },
  { to: "/memory", icon: Brain, label: "Memory" },
  { to: "/benchmarks", icon: BarChart3, label: "Benchmarks" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

interface SidebarProps {
  onNewIndex?: () => void;
}

export function Sidebar({ onNewIndex }: SidebarProps) {
  const { backendOnline, ollamaRunning, cogneeIdle } = useHealthStore();

  return (
    <nav className="w-[240px] h-screen fixed left-0 top-0 bg-surface-container-lowest border-r border-outline-variant flex flex-col py-6 px-4 z-20">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-8 px-2">
        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center border border-primary/20 shadow-[0_0_15px_rgba(173,198,255,0.1)]">
          <Sparkles className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-[20px] leading-[28px] font-medium tracking-tight text-on-surface">
            AndesContext
          </h1>
          <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            AI-Native Memory
          </p>
        </div>
      </div>

      {/* New Index CTA */}
      <button
        onClick={onNewIndex}
        className="mb-6 w-full bg-primary hover:bg-primary-fixed text-on-primary py-2 px-4 rounded-lg text-[12px] leading-[16px] tracking-[0.02em] font-medium flex items-center justify-center gap-2 transition-all active:scale-[0.99] shadow-[0_0_10px_rgba(173,198,255,0.2)]"
      >
        <Plus className="w-[18px] h-[18px]" />
        New Index
      </button>

      {/* Navigation */}
      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 py-2 px-3 rounded-lg transition-colors duration-200",
                  isActive
                    ? "text-primary font-bold border-l-2 border-primary bg-primary/5"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high"
                )
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium">
                {item.label}
              </span>
            </NavLink>
          ))}
        </div>
      </ScrollArea>

      {/* Status Footer */}
      <div className="mt-auto pt-4 border-t border-outline-variant/30 space-y-3">
        <div className="flex items-center gap-2 px-2">
          <StatusDot status={backendOnline ? "online" : "error"} size="sm" />
          <Activity className="w-4 h-4 text-on-surface-variant" />
          <span className="text-[11px] leading-[12px] font-bold text-on-surface-variant">
            Backend: {backendOnline ? "Online" : "Offline"}
          </span>
        </div>
        <div className="flex items-center gap-2 px-2">
          <StatusDot status={ollamaRunning ? "online" : "error"} size="sm" />
          <Cpu className="w-4 h-4 text-on-surface-variant" />
          <span className="text-[11px] leading-[12px] font-bold text-on-surface-variant">
            Ollama: {ollamaRunning ? "Running" : "Stopped"}
          </span>
        </div>
        <div className="flex items-center gap-2 px-2">
          <StatusDot status={cogneeIdle ? "idle" : "error"} size="sm" />
          <Database className="w-4 h-4 text-on-surface-variant" />
          <span className="text-[11px] leading-[12px] font-bold text-on-surface-variant">
            Cognee: {cogneeIdle ? "Idle" : "Off"}
          </span>
        </div>
      </div>
    </nav>
  );
}
