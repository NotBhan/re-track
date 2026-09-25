import React, { useEffect, useState } from "react";
import { Download, Check, RefreshCw } from "lucide-react";
import { useSystemStore } from "../../stores/systemStore";
import { Button } from "../../components/Button";
import { toast } from "../../app/providers/ToastProvider";

export const DiagnosticsViewer: React.FC = () => {
  const {
    diagnosticsData,
    fetchDiagnostics,
    exportDiagnosticsBundle,
    exportPath,
    exportingDiagnostics,
  } = useSystemStore();

  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchDiagnostics();
  }, [fetchDiagnostics]);

  const handleExport = async () => {
    const path = await exportDiagnosticsBundle();
    if (path) {
      toast.success("Diagnostics bundle exported to disk");
    } else {
      toast.error("Failed to export diagnostics bundle");
    }
  };

  const handleCopyPath = () => {
    if (exportPath && navigator.clipboard) {
      navigator.clipboard.writeText(exportPath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success("Export path copied");
    }
  };

  return (
    <div className="flex flex-col gap-5 max-w-3xl">
      {/* Top action bar */}
      <div className="flex items-center justify-between p-4 rounded-lg bg-[#0a0a0a] border border-[#262626]">
        <div>
          <h4 className="text-xs font-semibold text-[#ededed]">Operational Diagnostics</h4>
          <p className="text-xs text-[#a1a1a1] mt-0.5">
            Sanitized logs, memory subsystem status, and hardware state for troubleshooting.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => fetchDiagnostics()}
            title="Refresh diagnostics"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>

          <Button size="sm" loading={exportingDiagnostics} onClick={handleExport}>
            <Download className="w-3.5 h-3.5 mr-1" />
            <span>Export Bundle</span>
          </Button>
        </div>
      </div>

      {/* Export Path Notice if present */}
      {exportPath && (
        <div className="p-3.5 rounded-lg bg-[#051a0e] border border-[#10b981]/25 text-[#10b981] text-xs flex items-center justify-between gap-3">
          <div className="truncate">
            <span className="font-semibold block mb-0.5">Bundle exported successfully:</span>
            <span className="font-mono text-[11px] text-[#ededed] truncate">{exportPath}</span>
          </div>
          <Button size="sm" variant="secondary" onClick={handleCopyPath} className="shrink-0">
            {copied ? <Check className="w-3 h-3 text-[#10b981] mr-1" /> : null}
            <span>{copied ? "Copied" : "Copy Path"}</span>
          </Button>
        </div>
      )}

      {/* Diagnostics JSON Tree / Log Viewer */}
      <div className="rounded-lg bg-[#0a0c10] border border-[#262626] p-4 max-h-[460px] overflow-y-auto">
        <pre className="text-xs font-mono text-[#a1a1a1] leading-relaxed overflow-x-auto whitespace-pre-wrap">
          {diagnosticsData
            ? JSON.stringify(diagnosticsData, null, 2)
            : "No diagnostics data collected. Click refresh to query backend."}
        </pre>
      </div>
    </div>
  );
};
