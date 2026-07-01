import { cn } from "@/lib/utils";

const langColors: Record<string, string> = {
  TS: "text-[#3178C6]",
  JS: "text-[#F7DF1E]",
  RS: "text-[#DEA584]",
  GO: "text-[#00ADD8]",
  PY: "text-[#3776AB]",
  YAML: "text-[#CB171E]",
  TF: "text-[#7B42BC]",
};

interface LanguageBadgeProps {
  language: string;
}

export function LanguageBadge({ language }: LanguageBadgeProps) {
  return (
    <span
      className={cn(
        "bg-surface-variant px-2 py-1 rounded text-[10px] font-bold",
        langColors[language] || "text-on-surface-variant"
      )}
    >
      {language}
    </span>
  );
}
