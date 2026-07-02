import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Eye,
  EyeOff,
  Copy,
  Trash2,
  PlusCircle,
  GitBranch,
  Clock,
  Hash,
  Check,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { useContextPackageStore } from "@/stores/context-package-store";
import type { SavedContextPackage } from "@/lib/api";

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return "yesterday";
  return `${days}d ago`;
}

interface PackageCardProps {
  pkg: SavedContextPackage;
}

export function PackageCard({ pkg }: PackageCardProps) {
  const navigate = useNavigate();
  const removePackage = useContextPackageStore((s) => s.removePackage);
  const [expanded, setExpanded] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(pkg.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    await removePackage(pkg.id);
    setShowDeleteConfirm(false);
  };

  const handleAppend = () => {
    navigate(`/context-builder?repo=${pkg.repository_id}&append=${pkg.id}`);
  };

  return (
    <>
      <Card className="p-5 bg-surface-container border border-outline-variant hover:border-primary/30 transition-all duration-200 hover:shadow-[0_4px_20px_rgba(173,198,255,0.08)]">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-[16px] leading-[24px] font-semibold text-on-surface truncate">
                {pkg.name}
              </h3>
              <Badge variant="secondary" className="shrink-0 text-[10px] leading-[14px] tracking-[0.04em]">
                <Hash className="w-3 h-3" />
                {pkg.token_estimate.toLocaleString()} tokens
              </Badge>
            </div>

            <p className="text-[13px] leading-[20px] text-on-surface-variant mb-3 line-clamp-2">
              {pkg.task}
            </p>

            <div className="flex items-center gap-4 text-[11px] leading-[16px] text-on-surface-variant/70">
              <span className="flex items-center gap-1.5">
                <GitBranch className="w-3.5 h-3.5" />
                {pkg.repository_name}
                <span className="text-on-surface-variant/50">/</span>
                {pkg.repository_branch}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {formatRelativeTime(pkg.created_at)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setExpanded(!expanded)}
              title={expanded ? "Collapse" : "View"}
            >
              {expanded ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleCopy}
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-4 h-4 text-secondary" /> : <Copy className="w-4 h-4" />}
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleAppend}
              title="Append to Context Builder"
            >
              <PlusCircle className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setShowDeleteConfirm(true)}
              title="Delete package"
              className="text-on-surface-variant hover:text-error hover:bg-error/10"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-outline-variant/50">
            <div className="bg-surface-container-lowest rounded-lg border border-outline-variant/30 p-4 max-h-[400px] overflow-y-auto">
              <pre className="text-[12px] leading-[20px] text-on-surface-variant whitespace-pre-wrap font-mono">
                {pkg.markdown}
              </pre>
            </div>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Package"
        description={`Are you sure you want to delete "${pkg.name}"?`}
        warning="This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={handleDelete}
      />
    </>
  );
}
