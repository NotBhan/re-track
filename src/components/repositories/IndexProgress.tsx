import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, Circle } from "lucide-react";

interface IndexProgressProps {
  repositoryName: string;
  status: "indexing" | "completed" | "error";
  error?: string | null;
}

const PIPELINE_STAGES = [
  "Preparing repository",
  "Scanning files",
  "Parsing source code",
  "Extracting architecture",
  "Generating embeddings",
  "Saving dataset",
  "Completed",
] as const;

export function IndexProgress({
  repositoryName,
  status,
  error,
}: IndexProgressProps) {
  const [activeStage, setActiveStage] = useState(-1);

  useEffect(() => {
    if (status === "completed") {
      setActiveStage(PIPELINE_STAGES.length - 1);
      return;
    }

    if (status !== "indexing") return;

    setActiveStage(0);

    const stageInterval = setInterval(() => {
      setActiveStage((prev) => {
        if (prev >= PIPELINE_STAGES.length - 2) {
          clearInterval(stageInterval);
          return prev;
        }
        return prev + 1;
      });
    }, 2500);

    return () => clearInterval(stageInterval);
  }, [status]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span className="text-sm font-medium text-on-surface">
          Indexing {repositoryName}
        </span>
      </div>

      <div className="rounded-lg bg-surface-container-lowest border border-outline-variant p-4 space-y-2.5">
        {PIPELINE_STAGES.map((stage, index) => {
          const isCompleted =
            status === "completed" ||
            (status === "indexing" && index < activeStage);
          const isActive = status === "indexing" && index === activeStage;
          const isPending = status === "indexing" && index > activeStage;

          return (
            <div key={stage} className="flex items-center gap-3">
              {isCompleted ? (
                <CheckCircle2 className="w-4 h-4 text-secondary shrink-0" />
              ) : isActive ? (
                <Loader2 className="w-4 h-4 animate-spin text-primary shrink-0" />
              ) : (
                <Circle
                  className={`w-4 h-4 shrink-0 ${
                    isPending ? "text-on-surface-variant/40" : "text-on-surface-variant"
                  }`}
                />
              )}
              <span
                className={`text-sm ${
                  isActive
                    ? "text-primary font-medium"
                    : isCompleted
                      ? "text-secondary"
                      : "text-on-surface-variant"
                }`}
              >
                {stage}
              </span>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="rounded-md bg-error/10 border border-error/30 px-4 py-3 text-sm text-error">
          {error}
        </div>
      )}
    </div>
  );
}
