import { Link, Zap, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

// TODO: Replace with real activity data when backend activity endpoint is available
const mockActivities = [
  {
    id: "1",
    type: "index" as const,
    message: "Indexed repository",
    repoName: "andes-core",
    timestamp: "2 min ago",
    detail: "342 files processed",
  },
  {
    id: "2",
    type: "generate" as const,
    message: "Generated context package",
    repoName: null,
    timestamp: "15 min ago",
    detail: "Auth module refactoring",
  },
  {
    id: "3",
    type: "sync" as const,
    message: "Synced memory graph",
    repoName: null,
    timestamp: "1 hour ago",
    detail: "12 new relationships",
  },
  {
    id: "4",
    type: "index" as const,
    message: "Indexed repository",
    repoName: "cognee-sdk",
    timestamp: "3 hours ago",
    detail: "891 files processed",
  },
  {
    id: "5",
    type: "generate" as const,
    message: "Generated context package",
    repoName: null,
    timestamp: "5 hours ago",
    detail: "API endpoint migration",
  },
];

const iconMap = {
  index: { icon: Link, color: "text-primary", bg: "bg-primary/20", border: "border-primary/50" },
  generate: { icon: Zap, color: "text-secondary", bg: "bg-secondary/20", border: "border-secondary/50" },
  sync: { icon: RefreshCw, color: "text-on-surface-variant", bg: "bg-surface-variant", border: "border-outline-variant" },
};

export function ActivityTimeline() {
  return (
    <div className="bg-surface-container border border-outline-variant rounded-xl p-5 h-[calc(100vh-250px)] min-h-[400px] flex flex-col">
      <h3 className="text-[20px] leading-[28px] font-medium text-on-surface mb-6 flex items-center gap-2">
        <span className="w-5 h-5 text-on-surface-variant" />
        Recent Activity
      </h3>
      <div className="flex-1 overflow-y-auto pr-2 space-y-6 relative">
        {mockActivities.map((activity, index) => {
          const config = iconMap[activity.type];
          const Icon = config.icon;
          return (
            <div key={activity.id} className="relative flex gap-4">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center z-10 border",
                    config.bg,
                    config.border
                  )}
                >
                  <Icon className={cn("w-3 h-3", config.color)} />
                </div>
                {index < mockActivities.length - 1 && (
                  <div className="w-px flex-1 bg-outline-variant/30 mt-2" />
                )}
              </div>
              <div className="flex-1 pb-4">
                <p className="text-[14px] leading-[20px] text-on-surface">
                  {activity.message}{" "}
                  {activity.repoName && (
                    <span className="font-mono px-1 bg-surface-container-lowest rounded text-primary text-[13px] leading-[20px]">
                      {activity.repoName}
                    </span>
                  )}
                </p>
                <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mt-1">
                  {activity.timestamp} &bull; {activity.detail}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
