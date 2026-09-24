import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./app/shell/AppShell";
import { ToastProvider } from "./app/providers/ToastProvider";
import { RepositoryCatalog } from "./features/code/RepositoryCatalog";
import { ContextWorkbench } from "./features/context/ContextWorkbench";
import { MemoryHub } from "./features/memory/MemoryHub";
import { SystemHub } from "./features/system/SystemHub";
import { RepositoryAddModal } from "./features/code/RepositoryAddModal";
import "./App.css";

export function App() {
  const [addModalOpen, setAddModalOpen] = useState(false);

  return (
    <BrowserRouter>
      <ToastProvider>
        <AppShell>
          <Routes>
            <Route path="/" element={<Navigate to="/code" replace />} />
            <Route
              path="/code"
              element={<RepositoryCatalog onOpenAddModal={() => setAddModalOpen(true)} />}
            />
            {/* Backward-compatible redirects */}
            <Route path="/workspace" element={<Navigate to="/code" replace />} />
            <Route path="/repositories" element={<Navigate to="/code" replace />} />

            <Route path="/context" element={<ContextWorkbench />} />
            <Route path="/studio" element={<Navigate to="/context" replace />} />
            <Route path="/context-builder" element={<Navigate to="/context" replace />} />
            <Route path="/packages" element={<Navigate to="/context" replace />} />

            <Route path="/memory" element={<MemoryHub />} />

            <Route path="/system" element={<SystemHub />} />
            <Route path="/settings" element={<Navigate to="/system" replace />} />
            <Route path="/benchmarks" element={<Navigate to="/system" replace />} />

            <Route path="*" element={<Navigate to="/code" replace />} />
          </Routes>
        </AppShell>
        <RepositoryAddModal open={addModalOpen} onOpenChange={setAddModalOpen} />
      </ToastProvider>
    </BrowserRouter>
  );
}

export default App;
