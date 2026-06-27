"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth";
import { LoadingState } from "@/components/ui/empty";

/**
 * 客户端路由保护：未登录重定向到 /login。
 * 在 hydration 完成前显示 loading，避免闪烁。
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const hydrated = useAuthStore((s) => s.hydrated);
  const restore = useAuthStore((s) => s.restore);

  useEffect(() => {
    restore();
  }, [restore]);

  useEffect(() => {
    if (hydrated && !token) {
      router.replace("/login");
    }
  }, [hydrated, token, router]);

  if (!hydrated || !token) {
    return <LoadingState text="正在校验登录状态…" />;
  }

  return <>{children}</>;
}
