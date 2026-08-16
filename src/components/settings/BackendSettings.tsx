import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";
import { health } from "@/lib/api";

export function BackendSettings() {
  const [showKey, setShowKey] = useState(false);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const status = useHealthStore((s) => s.status);

  const handleTestConnection = async () => {
    try {
      await health();
      setTestResult("success");
    } catch {
      setTestResult("error");
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface mb-2">
          Backend Configuration
        </h2>
        <p className="text-[14px] leading-[20px] text-on-surface-variant">
          Manage connection details for the primary RE:Track (RefinedEngine Track) orchestration
          server.
        </p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 shadow-sm">
        <div className="space-y-6">
          {/* Host URL */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Host URL
              </label>
              <span className="text-[14px] leading-[20px] text-outline text-xs mt-1 block">
                The address of your backend instance.
              </span>
            </div>
            <div className="md:w-2/3">
              <input
                type="text"
                defaultValue={status?.ollama_host ?? "http://127.0.0.1"}
                className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-mono text-[13px] leading-[20px] transition-colors placeholder-outline"
              />
            </div>
          </div>

          {/* Port */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Port
              </label>
            </div>
            <div className="md:w-2/3">
              <input
                type="number"
                defaultValue={status?.ollama_port ?? 8000}
                className="w-full max-w-[150px] bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-mono text-[13px] leading-[20px] transition-colors"
              />
            </div>
          </div>

          {/* API Key */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                API Key
              </label>
              <span className="text-[14px] leading-[20px] text-outline text-xs mt-1 block">
                Required if authentication is enabled on the server.
              </span>
            </div>
            <div className="md:w-2/3 relative">
              <input
                type={showKey ? "text" : "password"}
                defaultValue="sk-retrack-local-dev-12345"
                className="w-full bg-surface-container h-10 pl-3 pr-10 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-mono text-[13px] leading-[20px] transition-colors"
              />
              <button
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-2.5 text-outline hover:text-on-surface transition-colors"
              >
                {showKey ? (
                  <EyeOff className="w-5 h-5" />
                ) : (
                  <Eye className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end items-center gap-3">
        {testResult === "success" && (
          <span className="text-[13px] text-green-600">Connection successful</span>
        )}
        {testResult === "error" && (
          <span className="text-[13px] text-red-600">Connection failed</span>
        )}
        <button
          onClick={handleTestConnection}
          className="px-4 py-2 bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 rounded-md text-[12px] leading-[16px] tracking-[0.02em] font-medium transition-colors"
        >
          Test Connection
        </button>
      </div>
    </div>
  );
}
