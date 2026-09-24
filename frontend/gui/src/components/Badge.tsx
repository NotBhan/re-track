import React from "react";
import { cn } from "../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "danger" | "accent" | "muted";
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = "default",
  size = "sm",
  children,
  ...props
}) => {
  const variantStyles = {
    default: "bg-[#121212] text-[#a1a1a1] border border-[#262626]",
    accent: "bg-[#1a1a1a] text-[#ededed] border border-[#333333]",
    success: "bg-[#051a0e] text-[#10b981] border border-[#10b981]/25",
    warning: "bg-[#1c1304] text-[#f59e0b] border border-[#f59e0b]/25",
    danger: "bg-[#180808] text-[#f87171] border border-[#f87171]/25",
    muted: "bg-transparent text-[#707070] border border-[#262626]",
  };

  const sizeStyles = {
    sm: "text-[11px] px-2 py-0.5 rounded-md font-medium tracking-tight",
    md: "text-xs px-2.5 py-1 rounded-md font-medium",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 select-none font-sans",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
