import React, { useState, useEffect } from "react";
import { Header } from "./Header";
import { Navigation } from "./Navigation";
import { RepositoryAddModal } from "../../features/code/RepositoryAddModal";
import { useRepositoryStore } from "../../stores/repositoryStore";
import { useSystemStore } from "../../stores/systemStore";
import { useUiScaleStore } from "../../stores/uiScaleStore";
import { useNavigate } from "react-router-dom";

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const { fetchRepositories } = useRepositoryStore();
  const { pollHealth } = useSystemStore();
  const { zoomIn, zoomOut, resetScale } = useUiScaleStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchRepositories();
    pollHealth();

    // Poll health periodically every 5 seconds
    const interval = setInterval(() => {
      pollHealth();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchRepositories, pollHealth]);

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
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#000000] text-[#ededed] font-sans selection:bg-[#ffffff] selection:text-[#000000]">
      {/* Top Header */}
      <Header
        onAddRepo={() => setAddModalOpen(true)}
        onNavigateSystem={() => navigate("/system")}
      />

      {/* Main Layout: Sidebar + Page Canvas */}
      <div className="flex-1 flex overflow-hidden">
        <Navigation />
        <main className="flex-1 flex flex-col overflow-hidden bg-[#000000]">
          {children}
        </main>
      </div>

      {/* Global Add Repository Modal */}
      <RepositoryAddModal open={addModalOpen} onOpenChange={setAddModalOpen} />
    </div>
  );
};
