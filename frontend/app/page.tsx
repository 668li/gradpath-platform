"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";

/**
 * 根页面：根据登录状态重定向到 /dashboard 或 /login。
 */
export default function HomePage() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);
  const restore = useAuthStore((s) => s.restore);

  useEffect(() => {
    restore();
  }, [restore]);

  useEffect(() => {
    if (!hydrated) return;
    router.replace(token ? "/dashboard" : "/login");
  }, [hydrated, token, router]);

  return (
    <div className="flex min-h-screen items-center justify-center text-slate-400">
      <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
    </div>
  );
}
