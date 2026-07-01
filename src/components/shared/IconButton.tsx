import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface IconButtonProps {
  icon: LucideIcon;
  label: string;
  onClick?: () => void;
  className?: string;
}

export function IconButton({ icon: Icon, label, onClick, className }: IconButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={cn(
        "text-on-surface-variant hover:bg-surface-variant rounded-full p-2 transition-all duration-150 active:scale-95",
        className
      )}
    >
      <Icon className="w-5 h-5" />
    </button>
  );
}
