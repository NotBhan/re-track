import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  warning?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  warning,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  const isDestructive = variant === "destructive";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#0a0a0a] border border-[#262626] text-white p-6 shadow-2xl rounded-2xl max-w-md">
        <DialogHeader className="pb-2">
          <div className="flex items-center gap-3 mb-2">
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center border shrink-0 ${
                isDestructive
                  ? "bg-red-500/10 border-red-500/30 text-red-400"
                  : "bg-black border-[#262626] text-white"
              }`}
            >
              <AlertCircle className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-white tracking-tight">
                {title}
              </DialogTitle>
            </div>
          </div>
          <DialogDescription className="text-xs font-mono text-neutral-400 leading-relaxed pt-1">
            {description}
          </DialogDescription>
        </DialogHeader>

        {warning && (
          <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-3 text-xs font-mono text-red-300 my-2">
            {warning}
          </div>
        )}

        <DialogFooter className="gap-2 pt-3 border-t border-[#1f1f1f]">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="h-8 px-4 text-xs font-mono border-[#333] bg-black text-neutral-300 hover:text-white hover:bg-[#141414] cursor-pointer"
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={onConfirm}
            className={`h-8 px-4 text-xs font-mono font-bold cursor-pointer ${
              isDestructive
                ? "bg-red-600 text-white hover:bg-red-500 shadow-sm"
                : "bg-white text-black hover:bg-neutral-200 shadow-sm"
            }`}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
