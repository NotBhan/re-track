import { useState } from "react";
import { Folder, Search, GitBranch } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface StructuralTreePaneProps {
  repositoryName?: string;
  subfolders?: Array<{ path: string; description: string }>;
  onSelectSubfolder?: (path: string) => void;
  selectedPath?: string;
}

export function StructuralTreePane({
  repositoryName = "re-track",
  subfolders = [
    { path: "backend/app/services", description: "Service layer & context synthesis (24 services)" },
    { path: "backend/app/api", description: "FastAPI endpoints & command handlers (7 files)" },
    { path: "backend/app/models", description: "Domain models & Pydantic contracts (15 models)" },
    { path: "src/components/context-builder", description: "Context studio UI modules (3 components)" },
    { path: "src/components/settings", description: "Engine & model configuration (5 components)" },
    { path: "src/stores", description: "Zustand reactive state managers (6 stores)" },
    { path: "src-tauri/src", description: "Rust native runtime & IPC bridge (2 files)" },
  ],
  onSelectSubfolder,
  selectedPath = "backend/app/services",
}: StructuralTreePaneProps) {
  const [search, setSearch] = useState("");

  const filteredFolders = subfolders.filter(
    (f) => f.path.toLowerCase().includes(search.toLowerCase()) || f.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="w-full lg:w-[300px] h-full flex flex-col bg-card rounded-md border border-border shadow-xs overflow-hidden shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
            Repository Map
          </span>
          <p className="text-xs text-muted-foreground mt-0.5">AST Structural Outline</p>
        </div>
        <Badge variant="outline" className="text-xs font-mono px-2 py-0.5 border-border bg-secondary text-muted-foreground">
          Depth 2.5
        </Badge>
      </div>

      {/* Repo badge & Search */}
      <div className="p-3.5 space-y-2.5 border-b border-border bg-black/40">
        <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-xs font-mono text-foreground border border-border">
          <GitBranch className="w-3.5 h-3.5 text-foreground shrink-0" />
          <span className="truncate font-medium">{repositoryName}</span>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search submodules..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 pl-8 text-xs font-mono bg-black border-border rounded-md focus-visible:ring-1 focus-visible:ring-white"
          />
        </div>
      </div>

      {/* Folder Tree */}
      <ScrollArea className="flex-1 p-2.5">
        <div className="space-y-1">
          {filteredFolders.map((sub) => {
            const isSelected = selectedPath === sub.path;
            return (
              <button
                key={sub.path}
                onClick={() => onSelectSubfolder?.(sub.path)}
                className={`w-full text-left p-3 rounded-md transition-colors text-xs font-mono border ${
                  isSelected
                    ? "bg-accent border-border text-white"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                }`}
              >
                <div className="flex items-center gap-2 font-medium truncate">
                  <Folder className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-white" : "text-muted-foreground"}`} />
                  <span className="truncate font-medium">{sub.path}</span>
                </div>
                <p className="text-xs mt-1 text-muted-foreground font-sans line-clamp-1">
                  {sub.description}
                </p>
              </button>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
