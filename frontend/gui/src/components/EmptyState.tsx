import React from "react";
import { cn } from "../lib/utils";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center p-8 rounded-lg border border-[#262626] bg-[#0a0a0a]",
        className
      )}
    >
      {icon && (
        <div className="mb-3.5 p-3 rounded-lg bg-[#121212] text-[#a1a1a1] border border-[#262626]">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold text-[#ededed]">{title}</h3>
      {description && (
        <p className="text-xs text-[#a1a1a1] max-w-sm mt-1 mb-4 leading-relaxed">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
};
