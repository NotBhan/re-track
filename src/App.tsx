import { BrowserRouter, Routes, Route } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/layout/AppShell";
import Dashboard from "@/pages/Dashboard";
import Repositories from "@/pages/Repositories";
import ContextBuilder from "@/pages/ContextBuilder";
import Memory from "@/pages/Memory";
import Benchmarks from "@/pages/Benchmarks";
import Settings from "@/pages/Settings";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <TooltipProvider>
        <AppShell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/repositories" element={<Repositories />} />
            <Route path="/context-builder" element={<ContextBuilder />} />
            <Route path="/memory" element={<Memory />} />
            <Route path="/benchmarks" element={<Benchmarks />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </AppShell>
      </TooltipProvider>
    </BrowserRouter>
  );
}

export default App;
