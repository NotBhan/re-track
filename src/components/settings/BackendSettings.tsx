import { useState } from "react";
import { Eye, EyeOff, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";
import { health } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function BackendSettings() {
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const status = useHealthStore((s) => s.status);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await health();
      setTestResult("success");
    } catch {
      setTestResult("error");
    } finally {
      setTesting(false);
    }
  };

  const inputCls =
    "w-full bg-[#0e0e0e] h-10 px-3 rounded-lg border border-[#262626] focus:border-white focus:outline-none text-white font-mono text-xs transition-colors placeholder:text-neutral-600";
  const rowCls =
    "flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-[#1c1c1c] pb-5";
  const labelCls = "text-xs font-mono font-medium text-white block";
  const subCls = "text-[11px] text-neutral-400 mt-0.5 block";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight mb-1">
          Backend Configuration
        </h2>
        <p className="text-xs text-neutral-400">
          Manage connection details for the primary RE:Track orchestration server.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 space-y-5 shadow-2xl">
        {/* Host URL */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Host URL</label>
            <span className={subCls}>
              The address of your local backend instance.
            </span>
          </div>
          <div className="md:w-2/3">
            <input
              type="text"
              defaultValue={status?.ollama_host ? `http://${status.ollama_host}` : "http://127.0.0.1"}
              className={inputCls}
            />
          </div>
        </div>

        {/* Port */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Port</label>
            <span className={subCls}>FastAPI server listen port (default 8765).</span>
          </div>
          <div className="md:w-2/3">
            <input
              type="number"
              defaultValue={8765}
              className={`${inputCls} max-w-[150px]`}
            />
          </div>
        </div>

        {/* API Key */}
        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
          <div className="md:w-1/3">
            <label className={labelCls}>API Key</label>
            <span className={subCls}>
              Required if authentication is enabled on the server.
            </span>
          </div>
          <div className="md:w-2/3 relative">
            <input
              type={showKey ? "text" : "password"}
              defaultValue="sk-retrack-local-dev-12345"
              className={`${inputCls} pr-10`}
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-2.5 text-neutral-400 hover:text-white transition-colors"
            >
              {showKey ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center gap-3">
        <div className="flex items-center gap-2">
          {testResult === "success" && (
            <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span>Backend reachable & healthy</span>
            </div>
          )}
          {testResult === "error" && (
            <div className="flex items-center gap-1.5 text-xs font-mono text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span>Backend unreachable</span>
            </div>
          )}
        </div>

        <Button
          onClick={handleTestConnection}
          disabled={testing}
          size="sm"
          className="gap-2 h-9 text-xs font-mono font-semibold bg-white text-black hover:bg-neutral-200"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${testing ? "animate-spin" : ""}`} />
          <span>{testing ? "Testing..." : "Test Connection"}</span>
        </Button>
      </div>
    </div>
  );
}
