import React from "react";
import { cn } from "../lib/utils";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
  variant?: "pill" | "underline";
  ariaLabel?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  items,
  activeId,
  onChange,
  className,
  variant = "pill",
  ariaLabel,
}) => {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        variant === "pill"
          ? "flex items-center gap-1 p-1 bg-[#0a0a0a] border border-[#262626] rounded-sm"
          : "flex items-center gap-6 border-b border-[#262626]",
        className
      )}
    >
      {items.map((tab) => {
        const isActive = tab.id === activeId;
        if (variant === "underline") {
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => onChange(tab.id)}
              className={cn(
                "flex items-center gap-2 pb-2.5 text-xs font-medium transition-colors border-b-2 -mb-px",
                isActive
                  ? "border-[#ededed] text-[#ededed]"
                  : "border-transparent text-[#707070] hover:text-[#a1a1a1]"
              )}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={cn(
                    "text-[10px] px-1.5 py-0.2 rounded-full font-mono",
                    isActive
                      ? "bg-[#181818] text-[#ededed] border border-[#333333]"
                      : "bg-[#121212] text-[#707070] border border-[#262626]"
                  )}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        }

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors",
              isActive
                ? "bg-[#121212] text-[#ededed] border border-[#262626]"
                : "text-[#707070] hover:text-[#ededed] hover:bg-[#121212]/50"
            )}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={cn(
                  "text-[10px] px-1.5 py-0.2 rounded font-mono",
                  isActive
                    ? "bg-[#1f1f1f] text-[#ededed]"
                    : "bg-[#121212] text-[#707070]"
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
