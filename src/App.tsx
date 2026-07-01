/**
 * App — root component with routing.
 */

import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./components/AppShell";
import Dashboard from "./pages/Dashboard";
import IndexRepository from "./pages/IndexRepository";
import ContextBuilder from "./pages/ContextBuilder";
import MemoryViewer from "./pages/MemoryViewer";
import Settings from "./pages/Settings";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/index" element={<IndexRepository />} />
          <Route path="/context" element={<ContextBuilder />} />
          <Route path="/memory" element={<MemoryViewer />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;
