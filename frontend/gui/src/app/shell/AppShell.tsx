import React, { useEffect } from "react";
import { Header } from "./Header";
import { Navigation } from "./Navigation";
import { RepositoryAddModal } from "../../features/code/RepositoryAddModal";
import { useRepositoryStore } from "../../stores/repositoryStore";
import { useSystemStore } from "../../stores/systemStore";
import { useUiScaleStore } from "../../stores/uiScaleStore";
import { useNavigate } from "react-router-dom";

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const {
    bootstrapRepositories,
    stopBootstrap,
    fetchRepositories,
    addRepositoryOpen,
    openAddRepository,
    closeAddRepository,
  } = useRepositoryStore();
  const { pollHealth, backendOnline } = useSystemStore();
  const { zoomIn, zoomOut, resetScale } = useUiScaleStore();
  const navigate = useNavigate();

  // Hydrate persisted repositories on startup. The backend takes time to become
  // ready after launch, so the bootstrap retries until the first fetch succeeds
  // instead of leaving the store empty until the next repository mutation.
  useEffect(() => {
    bootstrapRepositories();
    pollHealth();

    return () => stopBootstrap();
  }, [bootstrapRepositories, stopBootstrap, pollHealth]);

  // Poll health periodically every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      pollHealth();
    }, 5000);
    return () => clearInterval(interval);
  }, [pollHealth]);

  // Re-synchronize persisted repositories whenever the backend becomes reachable
  // (e.g. it restarted, or the bootstrap window closed before readiness).
  useEffect(() => {
    if (backendOnline) {
      fetchRepositories();
    }
  }, [backendOnline, fetchRepositories]);

  // Global UI Scale keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === "=" || e.key === "+") {
          e.preventDefault();
          zoomIn();
        } else if (e.key === "-") {
          e.preventDefault();
          zoomOut();
        } else if (e.key === "0") {
          e.preventDefault();
          resetScale();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [zoomIn, zoomOut, resetScale]);

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-[#000000] text-[#ededed] font-sans selection:bg-[#ffffff] selection:text-[#000000]">
      {/* Top Header */}
      <Header
        onAddRepo={openAddRepository}
        onNavigateSystem={() => navigate("/system")}
        onNavigateRepositories={() => navigate("/repositories")}
      />

      {/* Main Layout: Sidebar + Page Canvas */}
      <div className="flex-1 flex overflow-hidden">
        <Navigation />
        <main className="flex-1 flex flex-col overflow-hidden bg-[#000000]">
          {children}
        </main>
      </div>

      {/* Single global Add Repository Modal */}
      <RepositoryAddModal open={addRepositoryOpen} onOpenChange={(open) => !open && closeAddRepository()} />
    </div>
  );
};
