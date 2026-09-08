import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useParams } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/layout/AppShell";
import { PageTransition } from "@/components/layout/PageTransition";
import { CreateRepositoryIndexModal } from "@/components/repositories/CreateRepositoryIndexModal";
import { Toaster } from "@/components/ui/toast";
import { AnimatePresence } from "motion/react";
import ContextStudio from "@/pages/ContextStudio";
import Workspace from "@/pages/Workspace";
import Memory from "@/pages/Memory";
import SystemTelemetry from "@/pages/SystemTelemetry";
import "./App.css";

function PreservingRedirect({
  to,
  defaultParams,
}: {
  to: string;
  defaultParams?: Record<string, string>;
}) {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);

  if (defaultParams) {
    for (const [key, value] of Object.entries(defaultParams)) {
      if (!searchParams.has(key)) {
        searchParams.set(key, value);
      }
    }
  }

  const query = searchParams.toString();
  const target = query ? `${to}?${query}` : to;
  return <Navigate to={target} replace />;
}

function KnowledgeRedirect() {
  const { repoId } = useParams<{ repoId: string }>();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  if (repoId) {
    searchParams.set("repo", repoId);
  }
  if (!searchParams.has("tab")) {
    searchParams.set("tab", "ast");
  }
  return <Navigate to={`/workspace?${searchParams.toString()}`} replace />;
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PreservingRedirect to="/workspace" />} />
        <Route
          path="/workspace"
          element={
            <PageTransition>
              <Workspace />
            </PageTransition>
          }
        />
        <Route
          path="/repositories"
          element={<PreservingRedirect to="/workspace" />}
        />
        <Route
          path="/studio"
          element={
            <PageTransition>
              <ContextStudio />
            </PageTransition>
          }
        />
        <Route path="/knowledge/:repoId" element={<KnowledgeRedirect />} />
        <Route
          path="/context-builder"
          element={<PreservingRedirect to="/studio" />}
        />
        <Route
          path="/packages"
          element={<PreservingRedirect to="/studio" defaultParams={{ tab: "history" }} />}
        />
        <Route
          path="/memory"
          element={
            <PageTransition>
              <Memory />
            </PageTransition>
          }
        />
        <Route
          path="/system"
          element={
            <PageTransition>
              <SystemTelemetry />
            </PageTransition>
          }
        />
        <Route
          path="/benchmarks"
          element={<PreservingRedirect to="/system" defaultParams={{ tab: "benchmarks" }} />}
        />
        <Route
          path="/settings"
          element={<PreservingRedirect to="/system" defaultParams={{ tab: "runtime" }} />}
        />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  const [createModalOpen, setCreateModalOpen] = useState(false);

  return (
    <BrowserRouter>
      <TooltipProvider>
        <AppShell onNewIndex={() => setCreateModalOpen(true)}>
          <AnimatedRoutes />
        </AppShell>
        <CreateRepositoryIndexModal
          open={createModalOpen}
          onOpenChange={setCreateModalOpen}
        />
        <Toaster />
      </TooltipProvider>
    </BrowserRouter>
  );
}

export default App;
