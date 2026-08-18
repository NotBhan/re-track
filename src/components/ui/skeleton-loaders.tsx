import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[#141414] border border-[#222222]/50",
        className
      )}
    />
  );
}

export function RepositoryCardSkeleton() {
  return (
    <div className="rounded-lg bg-[#0a0a0a] border border-[#1e1e1e] p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <Skeleton className="w-4 h-4 rounded shrink-0" />
          <Skeleton className="w-36 h-4 rounded" />
        </div>
        <Skeleton className="w-14 h-4.5 rounded" />
      </div>

      <div className="space-y-1.5">
        <Skeleton className="w-full h-3 rounded" />
        <Skeleton className="w-3/4 h-3 rounded" />
      </div>

      <div className="flex items-center gap-2 pt-1 font-mono">
        <Skeleton className="w-44 h-3 rounded" />
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-[#181818]">
        <Skeleton className="w-24 h-3 rounded" />
        <div className="flex items-center gap-1.5">
          <Skeleton className="w-16 h-7 rounded-md" />
          <Skeleton className="w-18 h-7 rounded-md" />
        </div>
      </div>
    </div>
  );
}

export function CallGraphSkeleton() {
  return (
    <div className="w-full h-full bg-[#050505] rounded-lg border border-[#1e1e1e] p-4 flex flex-col justify-between relative overflow-hidden">
      <div className="flex justify-between items-center z-10">
        <div className="space-y-1">
          <Skeleton className="w-36 h-4" />
          <Skeleton className="w-24 h-3" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="w-7 h-7 rounded-md" />
          <Skeleton className="w-7 h-7 rounded-md" />
        </div>
      </div>

      <div className="flex items-center justify-center gap-8 z-10 py-12">
        <div className="space-y-4">
          <Skeleton className="w-24 h-8 rounded-md" />
          <Skeleton className="w-28 h-8 rounded-md" />
        </div>
        <div className="space-y-6">
          <Skeleton className="w-32 h-10 rounded-md" />
          <Skeleton className="w-24 h-8 rounded-md" />
          <Skeleton className="w-28 h-8 rounded-md" />
        </div>
        <div className="space-y-4">
          <Skeleton className="w-26 h-8 rounded-md" />
          <Skeleton className="w-20 h-8 rounded-md" />
        </div>
      </div>

      <div className="flex justify-between items-center z-10 border-t border-[#181818] pt-2.5">
        <Skeleton className="w-40 h-3 rounded" />
        <Skeleton className="w-16 h-3 rounded" />
      </div>
    </div>
  );
}

export function StatsMetricSkeleton() {
  return (
    <div className="p-3.5 rounded-lg bg-[#0a0a0a] border border-[#1e1e1e] space-y-1.5">
      <div className="flex justify-between items-center">
        <Skeleton className="w-20 h-3 rounded" />
        <Skeleton className="w-3.5 h-3.5 rounded" />
      </div>
      <Skeleton className="w-16 h-6 rounded" />
      <Skeleton className="w-24 h-2.5 rounded" />
    </div>
  );
}

export function PackageCardSkeleton() {
  return (
    <div className="rounded-lg bg-[#0a0a0a] border border-[#1e1e1e] p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0 flex-1">
          <Skeleton className="w-48 h-4 rounded" />
          <Skeleton className="w-32 h-3 rounded" />
        </div>
        <Skeleton className="w-16 h-4.5 rounded" />
      </div>
      <Skeleton className="w-full h-8 rounded-md" />
      <div className="flex justify-between items-center pt-2 border-t border-[#181818]">
        <Skeleton className="w-28 h-3 rounded" />
        <div className="flex gap-1.5">
          <Skeleton className="w-14 h-6.5 rounded-md" />
          <Skeleton className="w-14 h-6.5 rounded-md" />
        </div>
      </div>
    </div>
  );
}
