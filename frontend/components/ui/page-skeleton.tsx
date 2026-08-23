import { ListSkeleton, CardSkeleton } from "@/components/ui/skeleton";

/**
 * 页面级加载骨架（loading.tsx 共享实现）。
 * 8 个路由曾各自复制同一份 CardSkeleton + ListSkeleton 结构，现收敛为本组件。
 */
export default function PageSkeleton() {
  return (
    <div className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-7xl px-4 py-6 md:px-6 md:py-8">
        <CardSkeleton />
        <div className="mt-6">
          <ListSkeleton count={5} />
        </div>
      </div>
    </div>
  );
}
