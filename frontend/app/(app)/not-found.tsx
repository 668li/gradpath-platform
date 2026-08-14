import Link from "next/link";
import { EmptyState } from "@/components/ui/empty";

export default function NotFound() {
  return (
    <EmptyState
      title="页面不存在（404）"
      description="你访问的地址无效或已被移除，返回工作台继续你的规划。"
      action={
        <Link
          href="/dashboard"
          className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
        >
          返回工作台
        </Link>
      }
    />
  );
}
