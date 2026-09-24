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
      <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <div>
          <h4 className="text-xs font-semibold text-slate-200">Operational Diagnostics</h4>
          <p className="text-xs text-slate-400 mt-0.5">
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
        <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between gap-3">
          <div className="truncate">
            <span className="font-semibold block mb-0.5">Bundle exported successfully:</span>
            <span className="font-mono text-[11px] text-emerald-200 truncate">{exportPath}</span>
          </div>
          <Button size="sm" variant="secondary" onClick={handleCopyPath} className="shrink-0">
            {copied ? <Check className="w-3 h-3 text-emerald-400 mr-1" /> : null}
            <span>{copied ? "Copied" : "Copy Path"}</span>
          </Button>
        </div>
      )}

      {/* Diagnostics JSON Tree / Log Viewer */}
      <div className="rounded-xl bg-[#0a0c10] border border-white/[0.06] p-4 max-h-[460px] overflow-y-auto">
        <pre className="text-xs font-mono text-slate-300 leading-relaxed overflow-x-auto whitespace-pre-wrap">
          {diagnosticsData
            ? JSON.stringify(diagnosticsData, null, 2)
            : "No diagnostics data collected. Click refresh to query backend."}
        </pre>
      </div>
    </div>
  );
};
