import { cn } from "@/lib/utils";

interface StatusDotProps {
  status: "online" | "idle" | "error";
  size?: "sm" | "md";
  className?: string;
}

const statusColors = {
  online: "bg-secondary shadow-[0_0_8px_rgba(78,222,163,0.6)]",
  idle: "bg-outline",
  error: "bg-error",
};

const sizeClasses = {
  sm: "w-1.5 h-1.5",
  md: "w-2 h-2",
};

export function StatusDot({ status, size = "md", className }: StatusDotProps) {
  return (
    <span className="relative flex items-center justify-center">
      {status === "online" && (
        <span
          className={cn(
            "absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75 animate-ping",
            sizeClasses[size]
          )}
        />
      )}
      <span
        className={cn(
          "relative inline-flex rounded-full",
          sizeClasses[size],
          statusColors[status],
          className
        )}
      />
    </span>
  );
}
