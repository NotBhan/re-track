import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  Brain,
  BarChart3,
  Settings,
  Plus,
  Sparkles,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useHealthStore } from "@/stores/health-store";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Context Studio" },
  { to: "/repositories", icon: FolderOpen, label: "Repositories" },
  { to: "/packages", icon: FileText, label: "Context Packages" },
  { to: "/memory", icon: Brain, label: "Memory Graph" },
  { to: "/benchmarks", icon: BarChart3, label: "Benchmarks" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

interface SidebarProps {
  onNewIndex?: () => void;
}

export function Sidebar({ onNewIndex }: SidebarProps) {
  const { backendOnline } = useHealthStore();

  return (
    <aside className="w-[240px] h-screen fixed left-0 top-0 bg-card/90 backdrop-blur-md border-r border-border/80 flex flex-col py-4 px-3 z-20">
      {/* Brand Header */}
      <div className="flex items-center gap-3 mb-5 px-2">
        <div className="w-8 h-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center shadow-xs">
          <Sparkles className="w-4 h-4" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <h1 className="text-sm font-bold tracking-tight text-foreground">
              RE:Track
            </h1>
            <Badge variant="outline" className="text-[10px] font-mono px-1 py-0 h-4 border-border/70">
              v0.1
            </Badge>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono">AI Context Hub</span>
        </div>
      </div>

      {/* Index Repo Button */}
      <div className="px-1 mb-4">
        <Button
          onClick={onNewIndex}
          variant="secondary"
          size="sm"
          className="w-full justify-start gap-2 h-9 text-xs font-semibold shadow-xs border border-border/60 hover:bg-secondary/80"
        >
          <Plus className="w-4 h-4 text-primary" />
          <span>Index Repository</span>
        </Button>
      </div>

      {/* Navigation Links */}
      <ScrollArea className="flex-1 px-1">
        <div className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 py-2 px-3 rounded-lg text-xs font-medium transition-all duration-150",
                  isActive
                    ? "bg-primary/10 text-primary font-semibold border border-primary/30 shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                )
              }
            >
              <item.icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </ScrollArea>

      {/* Footer Engine Status */}
      <div className="mt-auto pt-3 border-t border-border/70 px-2 flex items-center justify-between text-xs text-muted-foreground font-mono">
        <span className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${backendOnline ? "bg-emerald-500 shadow-[0_0_6px_#10b981]" : "bg-red-500"}`} />
          Engine Core
        </span>
        <span className="font-semibold text-foreground">{backendOnline ? "Ready" : "Offline"}</span>
      </div>
    </aside>
  );
}
