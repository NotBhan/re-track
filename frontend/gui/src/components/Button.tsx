import React from "react";
import { cn } from "../lib/utils";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md" | "lg" | "icon";
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, children, disabled, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-colors select-none disabled:opacity-40 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ededed]/40 focus-visible:ring-offset-1 focus-visible:ring-offset-black";

    const variantStyles = {
      primary:
        "bg-[#ffffff] hover:bg-[#eaeaea] active:bg-[#d5d5d5] text-[#000000] font-medium shadow-none",
      secondary:
        "bg-[#121212] hover:bg-[#1a1a1a] active:bg-[#222222] text-[#ededed] border border-[#262626] hover:border-[#404040]",
      ghost:
        "bg-transparent hover:bg-[#121212] active:bg-[#1a1a1a] text-[#a1a1a1] hover:text-[#ededed]",
      danger:
        "bg-[#180808] hover:bg-[#260e0e] active:bg-[#331111] text-[#f87171] border border-[#451a1a] hover:border-[#7f1d1d]",
      outline:
        "bg-transparent border border-[#262626] hover:border-[#404040] hover:bg-[#0a0a0a] text-[#ededed]",
    };

    const sizeStyles = {
      sm: "text-xs h-8 px-3 rounded-md gap-1.5",
      md: "text-sm h-9 px-4 rounded-md gap-2",
      lg: "text-sm h-10 px-5 rounded-md gap-2.5 font-medium",
      icon: "h-9 w-9 p-0 rounded-md",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      >
        {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
