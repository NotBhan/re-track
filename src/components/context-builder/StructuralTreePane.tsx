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
  repositoryName = "andes-context",
  subfolders = [
    { path: "backend/app/services", description: "Service layer & context logic (24 services)" },
    { path: "backend/app/api", description: "API schemas, routes & commands (7 files)" },
    { path: "backend/app/models", description: "Domain models & Pydantic contracts (15 models)" },
    { path: "src/components/context-builder", description: "Context studio UI modules (3 components)" },
    { path: "src/components/settings", description: "Model & engine configuration (5 components)" },
    { path: "src/stores", description: "Zustand client state managers (6 stores)" },
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
    <div className="w-full lg:w-[280px] h-full flex flex-col bg-card rounded-lg border border-border/80 shadow-xs overflow-hidden shrink-0">
      {/* Header */}
      <div className="p-3.5 border-b border-border/80 bg-card flex items-center justify-between">
        <div>
          <span className="text-xs font-bold text-foreground uppercase tracking-wider font-mono">
            Repository Map
          </span>
          <p className="text-[11px] text-muted-foreground">AST & Subfolder Outline</p>
        </div>
        <Badge variant="secondary" className="text-[11px] font-mono px-2 py-0.5">
          Depth 2.5
        </Badge>
      </div>

      {/* Repo badge & Search */}
      <div className="p-3 space-y-2 border-b border-border/80 bg-secondary/20">
        <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-secondary/80 text-xs font-mono text-foreground border border-border/40">
          <GitBranch className="w-3.5 h-3.5 text-primary shrink-0" />
          <span className="truncate font-semibold">{repositoryName}</span>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search submodules..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 pl-8 text-xs font-mono bg-background border-border/80 rounded-md"
          />
        </div>
      </div>

      {/* Folder Tree */}
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-1.5">
          {filteredFolders.map((sub) => {
            const isSelected = selectedPath === sub.path;
            return (
              <button
                key={sub.path}
                onClick={() => onSelectSubfolder?.(sub.path)}
                className={`w-full text-left p-2.5 rounded-md transition-all text-xs font-mono border ${
                  isSelected
                    ? "bg-primary/10 border-primary/40 text-foreground shadow-xs"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary/60 hover:border-border/40"
                }`}
              >
                <div className="flex items-center gap-2 font-medium truncate">
                  <Folder className={`w-4 h-4 shrink-0 ${isSelected ? "text-primary fill-primary/20" : "text-muted-foreground"}`} />
                  <span className="truncate font-semibold">{sub.path}</span>
                </div>
                <p className="text-[11px] mt-1 text-muted-foreground font-sans line-clamp-1 leading-normal">
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
