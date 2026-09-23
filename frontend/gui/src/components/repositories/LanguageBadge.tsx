import { cn } from "@/lib/utils";

interface LanguageBadgeProps {
  language: string;
}

export function LanguageBadge({ language }: LanguageBadgeProps) {
  return (
    <span
      className={cn(
        "px-1.5 py-0.5 rounded text-[11px] font-mono text-neutral-300 bg-[#121212] border border-[#222222]"
      )}
    >
      {language}
    </span>
  );
}
