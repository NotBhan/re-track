import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "../lib/utils";

export interface SelectOption {
  value: string;
  label: string;
  hint?: string;
  disabled?: boolean;
}

export interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  size?: "sm" | "md";
  className?: string;
  menuClassName?: string;
  ariaLabel?: string;
  id?: string;
  title?: string;
}

export const Select: React.FC<SelectProps> = ({
  value,
  onChange,
  options,
  placeholder = "Select…",
  disabled = false,
  size = "md",
  className,
  menuClassName,
  ariaLabel,
  id,
  title,
}) => {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const generatedId = useId();
  const listboxId = `${id || generatedId}-listbox`;

  const enabledIndexes = useMemo(
    () => options.map((opt, index) => (opt.disabled ? -1 : index)).filter((index) => index >= 0),
    [options]
  );
  const selectedIndex = options.findIndex((opt) => opt.value === value);
  const selected = selectedIndex >= 0 ? options[selectedIndex] : null;

  const close = useCallback(() => {
    setOpen(false);
    setActiveIndex(-1);
  }, []);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        close();
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open, close]);

  useEffect(() => {
    if (!open) return;
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : enabledIndexes[0] ?? -1);
  }, [open, selectedIndex, enabledIndexes]);

  useEffect(() => {
    if (!open) return;
    listRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open || activeIndex < 0) return;
    const node = listRef.current?.querySelector<HTMLElement>(`[data-option-index="${activeIndex}"]`);
    node?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  const commit = (index: number) => {
    const option = options[index];
    if (!option || option.disabled) return;
    onChange(option.value);
    close();
    triggerRef.current?.focus();
  };

  const moveActive = (direction: 1 | -1) => {
    if (enabledIndexes.length === 0) return;
    const position = enabledIndexes.indexOf(activeIndex);
    const nextPosition =
      position === -1
        ? direction === 1
          ? 0
          : enabledIndexes.length - 1
        : (position + direction + enabledIndexes.length) % enabledIndexes.length;
    setActiveIndex(enabledIndexes[nextPosition]);
  };

  const handleTriggerKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) return;
    switch (event.key) {
      case "ArrowDown":
      case "ArrowUp":
      case "Enter":
      case " ":
        event.preventDefault();
        setOpen(true);
        break;
      case "Escape":
        close();
        break;
      default:
        break;
    }
  };

  const handleListKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        moveActive(1);
        break;
      case "ArrowUp":
        event.preventDefault();
        moveActive(-1);
        break;
      case "Home":
        event.preventDefault();
        setActiveIndex(enabledIndexes[0] ?? -1);
        break;
      case "End":
        event.preventDefault();
        setActiveIndex(enabledIndexes[enabledIndexes.length - 1] ?? -1);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        commit(activeIndex);
        break;
      case "Tab":
        close();
        break;
      case "Escape":
        event.preventDefault();
        close();
        triggerRef.current?.focus();
        break;
      default:
        break;
    }
  };

  const sizeStyles = {
    sm: "h-7 text-[11px] px-2 gap-1.5",
    md: "h-9 text-xs px-3 gap-2",
  };

  return (
    <div ref={containerRef} className={cn("relative inline-flex", className)} title={title}>
      <button
        ref={triggerRef}
        id={id}
        type="button"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        aria-disabled={disabled}
        disabled={disabled}
        onClick={() => !disabled && setOpen((prev) => !prev)}
        onKeyDown={handleTriggerKeyDown}
        className={cn(
          "flex w-full items-center justify-between rounded-sm border bg-[#0a0a0a] font-medium text-[#ededed] transition-colors",
          "border-[#262626] hover:border-[#404040]",
          "focus-visible:outline-none focus-visible:border-[#666666] focus-visible:ring-1 focus-visible:ring-[#ededed]/25",
          open && "border-[#404040]",
          disabled && "opacity-40 cursor-not-allowed hover:border-[#262626]",
          sizeStyles[size]
        )}
      >
        <span className={cn("truncate text-left", !selected && "text-[#707070]")}>
          {selected ? selected.label : placeholder}
        </span>
        <ChevronDown
          className={cn(
            "shrink-0 text-[#707070] transition-transform duration-150",
            size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div
          ref={listRef}
          id={listboxId}
          role="listbox"
          aria-label={ariaLabel}
          tabIndex={-1}
          onKeyDown={handleListKeyDown}
          className={cn(
            "absolute left-0 top-[calc(100%+4px)] z-50 min-w-full max-w-[22rem] max-h-64 overflow-y-auto",
            "rounded-lg border border-[#262626] bg-[#121212] p-1",
            "shadow-[0_2px_2px_rgba(0,0,0,0.4),0_8px_16px_-4px_rgba(0,0,0,0.6)]",
            menuClassName
          )}
        >
          {options.length === 0 && (
            <div className="px-2.5 py-2 text-[11px] text-[#707070]">No options available</div>
          )}
          {options.map((option, index) => {
            const isSelected = option.value === value;
            const isActive = index === activeIndex;
            return (
              <div
                key={option.value}
                data-option-index={index}
                role="option"
                aria-selected={isSelected}
                aria-disabled={option.disabled}
                onMouseEnter={() => !option.disabled && setActiveIndex(index)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => commit(index)}
                className={cn(
                  "flex items-center justify-between gap-3 rounded-[4px] px-2.5 py-1.5 text-xs transition-colors select-none",
                  option.disabled
                    ? "text-[#555555] cursor-not-allowed"
                    : isActive
                    ? "bg-[#1a1a1a] text-[#ededed] cursor-pointer"
                    : "text-[#a1a1a1] cursor-pointer",
                  isSelected && !option.disabled && "text-[#ededed] font-medium"
                )}
              >
                <span className="flex min-w-0 flex-col">
                  <span className="truncate">{option.label}</span>
                  {option.hint && (
                    <span className="truncate text-[10px] text-[#707070] font-normal">{option.hint}</span>
                  )}
                </span>
                {isSelected && <Check className="w-3.5 h-3.5 shrink-0 text-[#ededed]" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
