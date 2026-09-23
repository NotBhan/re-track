import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Trash2, AlertTriangle, Loader2 } from "lucide-react";
import type { Repository } from "@/types/repository";

interface DeleteRepositoryDialogProps {
  repository: Repository | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (repoId: string) => Promise<void>;
}

export function DeleteRepositoryDialog({
  repository,
  open,
  onOpenChange,
  onConfirm,
}: DeleteRepositoryDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!repository) return null;

  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await onConfirm(repository.id);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete repository");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(val) => !isDeleting && onOpenChange(val)}>
      <DialogContent className="sm:max-w-md bg-[#0a0a0a] border border-[#222222] text-foreground">
        <DialogHeader>
          <div className="flex items-center gap-2.5 text-red-400 mb-1">
            <div className="w-8 h-8 rounded-lg bg-red-950/40 border border-red-900/50 flex items-center justify-center shrink-0">
              <Trash2 className="w-4 h-4 text-red-400" />
            </div>
            <DialogTitle className="text-base font-semibold text-white tracking-tight">
              Delete Repository
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-neutral-400 text-left">
            Are you sure you want to delete{" "}
            <span className="font-semibold text-white font-mono">{repository.name}</span> from your workspace?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          {/* Target path display */}
          <div className="p-2.5 rounded-md bg-[#111111] border border-[#1e1e1e] font-mono text-[11px] text-neutral-300 truncate">
            <span className="text-neutral-500 mr-1.5">Path:</span>
            {repository.local_path}
          </div>

          {/* Safety warning */}
          <div className="p-3 rounded-md bg-amber-950/20 border border-amber-900/30 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-[11px] text-amber-200/90 leading-relaxed">
              This will remove the repository registration and all derived AST call graphs, LanceDB vector indexes, and Cognee semantic memories.
              <div className="mt-1 font-semibold text-neutral-300">
                Your local source code files on disk will NOT be deleted or modified.
              </div>
            </div>
          </div>

          {error && (
            <div className="p-2.5 rounded-md bg-red-950/30 border border-red-900/40 text-xs text-red-400 font-mono">
              {error}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
            className="h-8 text-xs font-mono border-[#262626] bg-[#0d0d0d] hover:bg-[#181818] text-neutral-300"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={isDeleting}
            className="h-8 text-xs font-mono bg-red-600 hover:bg-red-700 text-white gap-1.5 cursor-pointer shadow-xs"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete Repository</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
