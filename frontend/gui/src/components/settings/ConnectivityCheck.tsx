import { useState } from "react";
import { AlertCircle, CheckCircle2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { health } from "@/lib/api";
import { Button } from "@/components/ui/button";

/**
 * Minimal backend reachability probe for the Settings page.
 *
 * Reads the same authoritative `/health` endpoint as the global runtime
 * indicator. It exposes no editable connection fields because the backend
 * origin is owned by the Tauri runtime, not by user configuration.
 */
export function ConnectivityCheck() {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<"success" | "error" | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    try {
      await health();
      setResult("success");
    } catch {
      setResult("error");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-xs font-medium text-neutral-200">Backend Connectivity</h3>
          <p className="text-xs text-neutral-500 mt-0.5">
            Probe the local RE:Track server. The backend origin is managed by the desktop runtime.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {result === "success" && (
            <span className="flex items-center gap-1.5 text-xs font-mono text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Backend reachable &amp; healthy</span>
            </span>
          )}
          {result === "error" && (
            <span className="flex items-center gap-1.5 text-xs font-mono text-red-400">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Backend unreachable</span>
            </span>
          )}

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleTest}
            disabled={testing}
            className="h-8 px-3 text-xs bg-[#141414] hover:bg-[#222222] text-neutral-200 border-[#2a2a2a] cursor-pointer"
          >
            <RefreshCw className={cn("w-3 h-3 mr-1.5", testing && "animate-spin")} />
            <span>{testing ? "Testing..." : "Test Connection"}</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
