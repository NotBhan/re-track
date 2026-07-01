import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { AlertTriangle } from "lucide-react";

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
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-surface-container border border-outline-variant shadow-[0_20px_50px_-12px_rgba(0,0,0,0.8)]">
        <DialogHeader>
          <div className="w-12 h-12 rounded-full bg-error/10 border border-error/20 flex items-center justify-center text-error mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <DialogTitle className="text-[20px] leading-[28px] font-medium text-on-surface">
            {title}
          </DialogTitle>
          <DialogDescription className="text-[14px] leading-[20px] text-on-surface-variant">
            {description}
          </DialogDescription>
        </DialogHeader>

        {warning && (
          <p className="text-[13px] leading-[20px] text-on-surface-variant border-l-2 border-error/50 pl-3 py-1 bg-error/5 rounded-r">
            {warning}
          </p>
        )}

        <DialogFooter className="gap-2">
          <button
            onClick={() => onOpenChange(false)}
            className="px-4 py-2 rounded-md text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface hover:bg-surface-variant border border-transparent transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={
              variant === "destructive"
                ? "px-4 py-2 rounded-md text-[12px] leading-[16px] tracking-[0.02em] font-medium bg-error text-white hover:bg-error/90 transition-colors shadow-[0_0_10px_rgba(255,180,171,0.2)]"
                : "px-4 py-2 rounded-md text-[12px] leading-[16px] tracking-[0.02em] font-medium bg-primary text-on-primary hover:bg-primary-container transition-colors"
            }
          >
            {confirmLabel}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
