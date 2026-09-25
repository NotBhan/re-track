import React, { useEffect } from "react";
import { X, Trash2, Bookmark, Zap, FileText } from "lucide-react";
import { useContextMenuStore } from "../../stores/contextStore";
import { Button } from "../../components/Button";
import { formatDate, formatNumber } from "../../lib/utils";
import { toast } from "../../app/providers/ToastProvider";

interface PackageDrawerProps {
  open: boolean;
  onClose: () => void;
  onSelectPackage: (markdown: string) => void;
}

export const PackageDrawer: React.FC<PackageDrawerProps> = ({
  open,
  onClose,
  onSelectPackage,
}) => {
  const { savedPackages, loadingPackages, fetchPackages, deleteSavedPackage } = useContextMenuStore();

  useEffect(() => {
    if (open) {
      fetchPackages();
    }
  }, [open, fetchPackages]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="relative w-full max-w-md bg-[#0a0a0a] border-l border-[#262626] h-full shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-200">
        <div className="p-4 border-b border-[#262626] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bookmark className="w-4 h-4 text-[#a1a1a1]" />
            <h3 className="text-sm font-semibold text-[#ededed]">Saved Context Packages</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-[#a1a1a1] hover:text-[#ededed] rounded-md hover:bg-[#121212]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {loadingPackages ? (
            <div className="flex items-center justify-center p-8 text-xs text-[#a1a1a1]">
              Loading packages...
            </div>
          ) : savedPackages.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center text-[#a1a1a1]">
              <FileText className="w-8 h-8 opacity-30 mb-2" />
              <p className="text-xs">No saved packages yet.</p>
              <p className="text-[11px] text-[#707070] mt-1">
                Synthesize context from your tasks and click "Save Package".
              </p>
            </div>
          ) : (
            savedPackages.map((pkg) => (
              <div
                key={pkg.id}
                className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#262626] hover:border-[#404040] transition-colors flex flex-col gap-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-xs font-semibold text-[#ededed]">{pkg.name}</h4>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      await deleteSavedPackage(pkg.id);
                      toast.success("Package deleted");
                    }}
                    className="text-[#707070] hover:text-[#f87171] p-1 rounded-md"
                    title="Delete package"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <p className="text-[11px] text-[#a1a1a1] line-clamp-2">{pkg.task}</p>

                <div className="flex items-center justify-between text-[10px] text-[#a1a1a1] pt-1 border-t border-[#262626]">
                  <span className="flex items-center gap-1 font-mono">
                    <Zap className="w-3 h-3 text-[#707070]" />
                    {formatNumber(pkg.token_estimate)} tokens
                  </span>
                  <span>{formatDate(pkg.created_at)}</span>
                </div>

                <Button
                  size="sm"
                  variant="secondary"
                  className="w-full mt-1"
                  onClick={() => {
                    onSelectPackage(pkg.markdown);
                    onClose();
                  }}
                >
                  View Context
                </Button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
