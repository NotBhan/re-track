import { ReactNode, useState, useRef, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useHealthStore } from "@/stores/health-store";
import { useRepositoryStore } from "@/stores/repository-store";
import { cn } from "@/lib/utils";
import { useLayout } from "./LayoutContext";
import {
  Menu,
  Layers,
  FolderGit2,
  ChevronDown,
  Search,
  Check,
  Plus,
} from "lucide-react";

interface TopBarProps {
  title?: string;
  subtitle?: string;
  children?: ReactNode;
}

export function TopBar({ title, subtitle, children }: TopBarProps) {
  const {
    backendOnline,
    engineState,
    providerIdentity,
    activeModel,
    configuredModel,
  } = useHealthStore();

  const { repositories, selectedId, selected, select } = useRepositoryStore();
  const { toggleMobileMenu, openNewIndexModal } = useLayout();

  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const [searchParams, setSearchParams] = useSearchParams();


  // Click outside and Escape handler for dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const handleSelectRepo = (id: string | null) => {
    select(id);
    setIsOpen(false);
    const nextParams = new URLSearchParams(searchParams);
    if (id) {
      nextParams.set("repo", id);
    } else {
      nextParams.delete("repo");
    }
    setSearchParams(nextParams, { replace: true });
  };

  const safeRepositories = repositories || [];

  const filteredRepos = safeRepositories.filter(
    (r) =>
      r.name.toLowerCase().includes(filter.toLowerCase()) ||
      r.local_path.toLowerCase().includes(filter.toLowerCase())
  );

  const displayModel = activeModel
    ? activeModel.split(":")[0]
    : "No active model";

  const isHealthy = engineState === "healthy";
  const isDegraded = engineState === "degraded";

  const statusLabel = isHealthy
    ? "Ready"
    : isDegraded
    ? "Degraded"
    : backendOnline
    ? "Unavailable"
    : "Offline";

  const providerLabel =
    providerIdentity === "lmstudio"
      ? "LM Studio"
      : providerIdentity === "ollama"
      ? "Ollama"
      : providerIdentity === "openai_compatible"
      ? "OpenAI Compatible"
      : providerIdentity || "AI Engine";

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

        {/* Global Active Repository Selector (Left-Center) */}
        <div className="relative ml-1 sm:ml-3">
          <button
            ref={triggerRef}
            type="button"
            data-testid="global-repo-selector"
            onClick={() => setIsOpen(!isOpen)}
            className={cn(
              "inline-flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-colors cursor-pointer shrink-0",
              selected
                ? "border border-[#262626] bg-[#0c0c0c] hover:bg-[#151515] text-neutral-200"
                : "border border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/15 font-medium"
            )}
            title={
              selected
                ? `Active Repository: ${selected.name} (${selected.local_path})`
                : "No active repository selected"
            }
          >
            <FolderGit2
              className={cn(
                "w-3.5 h-3.5 shrink-0",
                selected ? "text-neutral-400" : "text-amber-400"
              )}
            />
            {selected ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                <span className="font-medium text-neutral-200 truncate max-w-[130px] sm:max-w-[170px]">
                  {selected.name}
                </span>
                <span className="text-[10px] text-neutral-500 font-mono hidden md:inline truncate max-w-[110px]">
                  {selected.local_path}
                </span>
              </>
            ) : (
              <span>Select Repository</span>
            )}
            <ChevronDown
              className={cn(
                "w-3 h-3 transition-transform duration-150 shrink-0",
                isOpen && "rotate-180",
                selected ? "text-neutral-400" : "text-amber-400/80"
              )}
            />
          </button>

          {/* Dropdown Menu */}
          {isOpen && (
            <div
              ref={dropdownRef}
              className="absolute left-0 top-full mt-1.5 w-72 sm:w-80 rounded-lg border border-[#222222] bg-[#0d0d0d] shadow-2xl z-50 p-2 text-xs flex flex-col gap-1 animate-in fade-in zoom-in-95 duration-100"
            >
              {/* Search Filter */}
              <div className="relative mb-1">
                <Search className="w-3.5 h-3.5 text-neutral-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Filter repositories..."
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="w-full h-8 pl-8 pr-3 bg-[#161616] border border-[#262626] rounded-md text-neutral-200 placeholder:text-neutral-500 text-xs focus:outline-none focus:border-neutral-400"
                  autoFocus
                />
              </div>

              {/* Repository List */}
              <div className="max-h-56 overflow-y-auto space-y-0.5 py-0.5">
                {filteredRepos.length > 0 ? (
                  filteredRepos.map((repo) => {
                    const isCurrent = repo.id === selectedId;
                    return (
                      <button
                        key={repo.id}
                        type="button"
                        onClick={() => handleSelectRepo(repo.id)}
                        className={cn(
                          "w-full flex items-center justify-between px-2.5 py-2 rounded-md transition-colors text-left group cursor-pointer",
                          isCurrent
                            ? "bg-[#1f1f1f] text-white"
                            : "text-neutral-300 hover:bg-[#161616] hover:text-white"
                        )}
                      >
                        <div className="flex items-center gap-2 min-w-0 pr-2">
                          <FolderGit2 className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
                          <div className="min-w-0">
                            <div className="font-medium truncate text-xs">
                              {repo.name}
                            </div>
                            <div className="text-[10px] text-neutral-500 font-mono truncate max-w-[180px]">
                              {repo.local_path}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-neutral-400 font-mono">
                            {repo.status || "ready"}
                          </span>
                          {isCurrent && (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          )}
                        </div>
                      </button>
                    );
                  })
                ) : (
                  <div className="py-4 text-center text-xs text-neutral-500 font-mono">
                    {safeRepositories.length === 0
                      ? "No repositories indexed yet"
                      : "No matching repositories"}
                  </div>
                )}
              </div>

              {selectedId && (
                <button
                  type="button"
                  onClick={() => handleSelectRepo(null)}
                  className="w-full text-left px-2.5 py-1.5 rounded-md text-[11px] text-neutral-400 hover:text-neutral-200 hover:bg-[#161616] transition-colors cursor-pointer"
                >
                  Clear selection (None)
                </button>
              )}

              <div className="border-t border-[#1e1e1e] my-1" />

              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  openNewIndexModal?.();
                }}
                className="w-full flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-md bg-[#181818] hover:bg-[#222222] text-white font-medium text-xs transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Index New Repository</span>
              </button>
            </div>
          )}
        </div>

        {/* Group B: Contextual Actions & Workspace Switcher */}
        {children && (
          <div className="flex items-center gap-2 sm:gap-3 ml-2 sm:ml-3 pl-2 sm:pl-3 border-l border-[#222222]">
            {children}
          </div>
        )}
      </div>

      {/* Group C: Engine Status & Telemetry */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        <div
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#222222] bg-[#0a0a0a] text-[11px] font-mono text-neutral-300 shadow-xs"
          title={`${providerLabel}: ${displayModel}${
            configuredModel && configuredModel !== activeModel
              ? ` (Configured: ${configuredModel})`
              : ""
          } (${statusLabel})`}
        >
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full shrink-0",
              isHealthy
                ? "bg-emerald-400"
                : isDegraded
                ? "bg-amber-400"
                : "bg-red-500"
            )}
          />
          <span className="truncate max-w-[90px] sm:max-w-[140px]">
            {displayModel}
          </span>
          <span className="text-neutral-600 hidden xs:inline">·</span>
          <span
            className={cn(
              "hidden xs:inline",
              isHealthy
                ? "text-neutral-400"
                : isDegraded
                ? "text-amber-400"
                : "text-red-400"
            )}
          >
            {statusLabel}
          </span>
        </div>
      </div>
    </header>
  );
}
