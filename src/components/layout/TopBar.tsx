import { useHealthStore } from "@/stores/health-store";
import { Badge } from "@/components/ui/badge";

interface TopBarProps {
  title?: string;
  children?: React.ReactNode;
}

export function TopBar({ title, children }: TopBarProps) {
  const { backendOnline } = useHealthStore();

  return (
    <header className="h-14 w-full sticky top-0 z-10 bg-black/90 backdrop-blur-md flex items-center justify-between px-6 border-b border-border">
      {/* Minimal Title */}
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-foreground tracking-tight">
          {title || "RE:Track"}
        </h2>
        {children}
      </div>

      {/* Subtle Right Indicators */}
      <div className="flex items-center gap-2.5">
        <Badge variant="outline" className="text-xs font-mono px-2.5 py-0.5 border-border bg-secondary/50 text-muted-foreground">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 inline-block shadow-[0_0_6px_#10b981]" />
          phi-4-mini
        </Badge>

        <Badge variant={backendOnline ? "secondary" : "destructive"} className="text-xs font-mono px-2.5 py-0.5">
          {backendOnline ? "Online" : "Offline"}
        </Badge>
      </div>
    </header>
  );
}
