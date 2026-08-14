import Link from "next/link";
import { Compass, Home } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper-100 px-4">
      <div className="card max-w-md w-full text-center space-y-4">
        <div className="flex justify-center">
          <Compass className="h-12 w-12 text-brand-500" />
        </div>
        <p className="font-display text-5xl font-bold text-ink-800">404</p>
        <h2 className="text-xl font-semibold text-ink-800">页面走丢了</h2>
        <p className="text-sm text-ink-500">
          你访问的地址不存在或已被移动，去看看别的规划内容吧。
        </p>
        <div className="flex flex-col gap-2 pt-2">
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <Home className="h-4 w-4" /> 返回首页
          </Link>
        </div>
      </div>
    </div>
  );
}
