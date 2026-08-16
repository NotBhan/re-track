import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  Brain,
  BarChart3,
  Settings,
  Plus,
  Layers,
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
    <aside className="w-[240px] h-screen fixed left-0 top-0 bg-black border-r border-border flex flex-col py-5 px-3 z-20">
      {/* Brand Header */}
      <div className="flex items-center gap-3 mb-6 px-3">
        <div className="w-8 h-8 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs tracking-tighter">
          <Layers className="w-4 h-4" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold tracking-tight text-foreground">
              RE:Track
            </h1>
            <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0 h-4 border-border text-muted-foreground">
              v0.1
            </Badge>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono">Context Hub</span>
        </div>
      </div>

      {/* Index Repo CTA */}
      <div className="px-2 mb-4">
        <Button
          onClick={onNewIndex}
          variant="secondary"
          size="sm"
          className="w-full justify-start gap-2.5 h-9 text-xs font-medium bg-secondary text-foreground hover:bg-accent border border-border rounded-md"
        >
          <Plus className="w-4 h-4 text-foreground" />
          <span>Index Repository</span>
        </Button>
      </div>

      {/* Navigation Links */}
      <ScrollArea className="flex-1 px-2">
        <div className="flex flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 py-2 px-3 rounded-md text-xs transition-colors",
                  isActive
                    ? "bg-accent text-white font-medium border border-border/80"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/70"
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
      <div className="mt-auto pt-4 border-t border-border px-3 flex items-center justify-between text-xs text-muted-foreground font-mono">
        <span className="flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${backendOnline ? "bg-emerald-500 shadow-[0_0_6px_#10b981]" : "bg-red-500"}`} />
          Engine Core
        </span>
        <span className="text-foreground">{backendOnline ? "Ready" : "Offline"}</span>
      </div>
    </aside>
  );
}
