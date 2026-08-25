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
    "w-full bg-[#050505] h-8 px-3 rounded-md border border-[#222222] focus:border-white focus:outline-none text-neutral-200 font-mono text-xs transition-colors placeholder:text-neutral-600";
  const rowCls =
    "flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-[#181818] pb-4";
  const labelCls = "text-xs font-medium text-neutral-200 block";
  const subCls = "text-xs text-neutral-500 mt-0.5 block";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white tracking-tight mb-0.5">
          Backend Configuration
        </h2>
        <p className="text-xs text-neutral-500">
          Manage connection details for the primary RE:Track orchestration server.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-4">
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
              className={`${inputCls} max-w-[140px]`}
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
              placeholder="Optional backend API key"
              className={`${inputCls} pr-9`}
            />

            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-2.5 top-2 text-neutral-400 hover:text-white transition-colors"
            >
              {showKey ? (
                <EyeOff className="w-3.5 h-3.5" />
              ) : (
                <Eye className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center gap-3">
        <div className="flex items-center gap-2">
          {testResult === "success" && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Backend reachable &amp; healthy</span>
            </div>
          )}
          {testResult === "error" && (
            <div className="flex items-center gap-1.5 text-xs text-red-400 font-mono">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Backend unreachable</span>
            </div>
          )}
        </div>

        <Button
          onClick={handleTestConnection}
          disabled={testing}
          size="sm"
          className="w-[140px] justify-center gap-1.5 h-7.5 px-3 text-xs bg-white text-black font-medium hover:bg-neutral-200 cursor-pointer shadow-xs disabled:opacity-60"
        >
          <RefreshCw className={`w-3 h-3 ${testing ? "animate-spin" : ""}`} />
          <span>{testing ? "Testing..." : "Test Connection"}</span>
        </Button>
      </div>
    </div>
  );
}
