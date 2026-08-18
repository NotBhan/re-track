import { useState } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/layout/AppShell";
import { PageTransition } from "@/components/layout/PageTransition";
import { CreateRepositoryIndexModal } from "@/components/repositories/CreateRepositoryIndexModal";
import { Toaster } from "@/components/ui/toast";
import { AnimatePresence } from "motion/react";
import ContextStudio from "@/pages/ContextStudio";
import Repositories from "@/pages/Repositories";
import KnowledgeExplorer from "@/pages/KnowledgeExplorer";
import ContextBuilder from "@/pages/ContextBuilder";
import ContextPackages from "@/pages/ContextPackages";
import Memory from "@/pages/Memory";
import Benchmarks from "@/pages/Benchmarks";
import Settings from "@/pages/Settings";
import "./App.css";

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route
          path="/"
          element={
            <PageTransition>
              <Repositories />
            </PageTransition>
          }
        />
        <Route
          path="/studio"
          element={
            <PageTransition>
              <ContextStudio />
            </PageTransition>
          }
        />
        <Route
          path="/knowledge/:repoId"
          element={
            <PageTransition>
              <KnowledgeExplorer />
            </PageTransition>
          }
        />
        <Route
          path="/context-builder"
          element={
            <PageTransition>
              <ContextBuilder />
            </PageTransition>
          }
        />
        <Route
          path="/packages"
          element={
            <PageTransition>
              <ContextPackages />
            </PageTransition>
          }
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
          path="/benchmarks"
          element={
            <PageTransition>
              <Benchmarks />
            </PageTransition>
          }
        />
        <Route
          path="/settings"
          element={
            <PageTransition>
              <Settings />
            </PageTransition>
          }
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
