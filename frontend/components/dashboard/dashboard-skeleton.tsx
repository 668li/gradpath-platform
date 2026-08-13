"use client";

import { Skeleton } from "@/components/ui/skeleton";

/** Dashboard骨架屏 — 结构化占位，替代空白spinner */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex items-center justify-between">
        <div><Skeleton className="h-8 w-32 mb-2" /><Skeleton className="h-4 w-48" /></div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => (
          <div key={`skel-${i}`} className="card p-5">
            <Skeleton className="h-10 w-10 rounded-lg mb-3" />
            <Skeleton className="h-4 w-16 mb-1" />
            <Skeleton className="h-6 w-12" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    </div>
  );
}
