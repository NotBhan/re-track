import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: string;
  glow?: boolean;
  isBadge?: boolean;
  className?: string;
}

export function StatCard({
  icon,
  label,
  value,
  glow,
  isBadge,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "bg-surface-container border border-outline-variant rounded-xl p-5 flex flex-col justify-between h-32 transition-all hover:scale-[1.01] duration-200",
        glow && "glow-active",
        className
      )}
    >
      <div className="flex items-center gap-2 text-on-surface-variant text-[12px] leading-[16px] tracking-[0.02em] font-medium">
        {icon}
        {label}
      </div>
      {isBadge ? (
        <div className="text-[13px] leading-[20px] text-on-surface truncate px-2 py-1 bg-surface-container-lowest rounded border border-outline-variant inline-block mt-2 font-mono">
          {value}
        </div>
      ) : (
        <div className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface">
          {value}
        </div>
      )}
    </div>
  );
}
