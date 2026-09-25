import React from "react";
import { cn } from "../lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, icon, type = "text", ...props }, ref) => {
    return (
      <div className="relative flex items-center w-full">
        {icon && (
          <div className="absolute left-3 flex items-center pointer-events-none text-[#707070]">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          type={type}
          className={cn(
            "w-full h-9 bg-[#0a0a0a] text-[#ededed] placeholder:text-[#707070] text-sm rounded-sm px-3.5 border border-[#262626] transition-colors focus:outline-none focus:border-[#666666] focus:ring-1 focus:ring-[#ededed]/20 disabled:opacity-40 disabled:cursor-not-allowed",
            icon && "pl-9",
            className
          )}
          {...props}
        />
      </div>
    );
  }
);

Input.displayName = "Input";
