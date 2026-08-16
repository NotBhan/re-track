import { cn } from "@/lib/utils";

interface LanguageBadgeProps {
  language: string;
}

export function LanguageBadge({ language }: LanguageBadgeProps) {
  return (
    <span
      className={cn(
        "px-2.5 py-1 rounded-md text-[11px] font-mono font-medium bg-[#141414] border border-[#2a2a2a] text-neutral-200"
      )}
    >
      {language}
    </span>
  );
}
