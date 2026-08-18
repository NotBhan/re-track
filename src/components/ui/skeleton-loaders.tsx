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
    <div className="rounded-xl bg-[#0a0a0a] border border-[#262626] p-5 space-y-4 shadow-xl">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="w-10 h-10 rounded-xl" />
          <div className="space-y-1.5">
            <Skeleton className="w-32 h-4" />
            <Skeleton className="w-24 h-3" />
          </div>
        </div>
        <Skeleton className="w-16 h-5 rounded-full" />
      </div>

      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-[#181818]">
        <Skeleton className="h-8 rounded-lg" />
        <Skeleton className="h-8 rounded-lg" />
        <Skeleton className="h-8 rounded-lg" />
      </div>

      <div className="flex items-center justify-between pt-1">
        <Skeleton className="w-20 h-4" />
        <Skeleton className="w-28 h-7 rounded-lg" />
      </div>
    </div>
  );
}

export function CallGraphSkeleton() {
  return (
    <div className="w-full h-full bg-[#050505] rounded-xl border border-[#222222] p-6 flex flex-col justify-between relative overflow-hidden">
      {/* Background grid shimmer lines */}
      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px]" />

      <div className="flex justify-between items-center z-10">
        <div className="space-y-1">
          <Skeleton className="w-36 h-4" />
          <Skeleton className="w-24 h-3" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="w-8 h-8 rounded-lg" />
          <Skeleton className="w-8 h-8 rounded-lg" />
        </div>
      </div>

      <div className="flex items-center justify-center gap-12 z-10 py-16">
        <div className="space-y-6">
          <Skeleton className="w-28 h-10 rounded-lg shadow-lg" />
          <Skeleton className="w-32 h-10 rounded-lg shadow-lg" />
        </div>
        <div className="space-y-8">
          <Skeleton className="w-36 h-12 rounded-xl shadow-lg" />
          <Skeleton className="w-28 h-10 rounded-lg shadow-lg" />
          <Skeleton className="w-32 h-10 rounded-lg shadow-lg" />
        </div>
        <div className="space-y-6">
          <Skeleton className="w-30 h-10 rounded-lg shadow-lg" />
          <Skeleton className="w-24 h-10 rounded-lg shadow-lg" />
        </div>
      </div>

      <div className="flex justify-between items-center z-10 border-t border-[#181818] pt-3">
        <Skeleton className="w-48 h-4" />
        <Skeleton className="w-20 h-4" />
      </div>
    </div>
  );
}

export function StatsMetricSkeleton() {
  return (
    <div className="p-4 rounded-xl bg-[#0a0a0a] border border-[#262626] space-y-2">
      <div className="flex justify-between items-center">
        <Skeleton className="w-20 h-3" />
        <Skeleton className="w-4 h-4 rounded" />
      </div>
      <Skeleton className="w-16 h-7" />
      <Skeleton className="w-28 h-3" />
    </div>
  );
}

export function PackageCardSkeleton() {
  return (
    <div className="rounded-xl bg-[#0a0a0a] border border-[#262626] p-4 space-y-3 shadow-lg">
      <div className="flex items-start justify-between">
        <div className="space-y-1.5">
          <Skeleton className="w-48 h-4" />
          <Skeleton className="w-32 h-3" />
        </div>
        <Skeleton className="w-20 h-5 rounded-full" />
      </div>
      <Skeleton className="w-full h-12 rounded-lg" />
      <div className="flex justify-between items-center pt-2 border-t border-[#181818]">
        <Skeleton className="w-24 h-4" />
        <div className="flex gap-2">
          <Skeleton className="w-16 h-7 rounded-md" />
          <Skeleton className="w-16 h-7 rounded-md" />
        </div>
      </div>
    </div>
  );
}
