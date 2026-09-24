import React from "react";
import { FolderGit2, ChevronDown, Plus, Cpu, ZoomIn, ZoomOut } from "lucide-react";
import { useRepositoryStore } from "../../stores/repositoryStore";
import { useSystemStore } from "../../stores/systemStore";
import { useUiScaleStore } from "../../stores/uiScaleStore";
import { cn } from "../../lib/utils";

interface HeaderProps {
  onAddRepo: () => void;
  onNavigateSystem: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onAddRepo, onNavigateSystem }) => {
  const { repositories, selectedId, selectRepository } = useRepositoryStore();
  const { providerReachable, activeProvider, activeModel, backendOnline } = useSystemStore();
  const { scale, zoomIn, zoomOut, resetScale } = useUiScaleStore();

  return (
    <header className="h-12 bg-[#000000] border-b border-[#262626] px-4 flex items-center justify-between shrink-0 select-none z-20">
      {/* Left: Brand + Active Repository Selector */}
      <div className="flex items-center gap-4">
        {/* Monochromatic Geist Brand Mark */}
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 rounded bg-[#ffffff] flex items-center justify-center">
            <span className="text-[10px] font-black text-[#000000] tracking-tighter">▲</span>
          </div>
          <span className="font-semibold text-xs tracking-tight text-[#ededed]">RE:Track</span>
        </div>

        <div className="h-3.5 w-px bg-[#262626]" />

        {/* Repository Switcher */}
        <div className="relative flex items-center">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#0a0a0a] border border-[#262626] hover:border-[#404040] transition-colors">
            <FolderGit2 className="w-3.5 h-3.5 text-[#707070]" />
            <select
              value={selectedId || ""}
              onChange={(e) => selectRepository(e.target.value || null)}
              className="bg-transparent text-xs font-medium text-[#ededed] outline-none cursor-pointer pr-4 appearance-none"
            >
              {repositories.length === 0 ? (
                <option value="" disabled className="bg-[#0a0a0a] text-[#707070]">
                  No repositories added
                </option>
              ) : (
                repositories.map((repo) => (
                  <option key={repo.id} value={repo.id} className="bg-[#0a0a0a] text-[#ededed]">
                    {repo.name} ({repo.file_count || 0} files)
                  </option>
                ))
              )}
            </select>
            <ChevronDown className="w-3 h-3 text-[#707070] -ml-4 pointer-events-none" />
          </div>

          <button
            onClick={onAddRepo}
            title="Add or import repository"
            className="ml-1.5 p-1 rounded-md text-[#707070] hover:text-[#ededed] hover:bg-[#121212] transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Right: UI Scale Controller + Runtime Indicator */}
      <div className="flex items-center gap-2.5">
        {/* UI Zoom Controls */}
        <div
          className="flex items-center bg-[#0a0a0a] border border-[#262626] rounded-md px-1 py-0.5"
          title="UI Scale (Ctrl + / - / 0)"
        >
          <button
            onClick={zoomOut}
            disabled={scale <= 80}
            title="Zoom Out (Ctrl -)"
            className="p-1 rounded text-[#707070] hover:text-[#ededed] hover:bg-[#121212] disabled:opacity-30 disabled:pointer-events-none transition-colors"
          >
            <ZoomOut className="w-3 h-3" />
          </button>

          <button
            onClick={resetScale}
            title="Reset Scale to 100% (Ctrl 0)"
            className="px-1.5 text-[11px] font-mono text-[#a1a1a1] hover:text-[#ededed] transition-colors"
          >
            {scale}%
          </button>

          <button
            onClick={zoomIn}
            disabled={scale >= 150}
            title="Zoom In (Ctrl +)"
            className="p-1 rounded text-[#707070] hover:text-[#ededed] hover:bg-[#121212] disabled:opacity-30 disabled:pointer-events-none transition-colors"
          >
            <ZoomIn className="w-3 h-3" />
          </button>
        </div>

        {/* Runtime Provider Indicator */}
        <button
          onClick={onNavigateSystem}
          className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#0a0a0a] border border-[#262626] hover:border-[#404040] transition-colors text-xs"
        >
          <Cpu className="w-3 h-3 text-[#707070]" />
          <span className="capitalize text-[#ededed] font-medium text-[11px]">
            {activeProvider || "Inference"}
          </span>
          {activeModel && (
            <span className="text-[11px] text-[#707070] max-w-[120px] truncate font-mono">
              {activeModel}
            </span>
          )}
          <span
            className={cn(
              "inline-block rounded-full h-1.5 w-1.5",
              backendOnline && providerReachable
                ? "bg-[#10b981]"
                : backendOnline
                ? "bg-[#f59e0b]"
                : "bg-[#ef4444]"
            )}
          />
        </button>
      </div>
    </header>
  );
};
