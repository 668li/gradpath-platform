"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { AppNav } from "@/components/nav";
import { AuthGuard } from "@/components/auth-guard";
import { useAuthStore } from "@/stores/auth";
import { useOnboardingStore } from "@/stores/onboarding";

// 这些路径位于 (app) 路由组下，但无需登录即可访问（公开法律文档）。
// 中间件已放行，此处布局层也跳过 auth 检查，避免登录前点击协议链接被踢回 /login。
const PUBLIC_PATHS_IN_APP = ["/legal"];

function isPathPublic(pathname: string): boolean {
  return PUBLIC_PATHS_IN_APP.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const user = useAuthStore((s) => s.user);
  const [fetched, setFetched] = useState(false);

  // Onboarding 状态
  const onboardingCompleted = useOnboardingStore((s) => s.completed);
  const refreshOnboarding = useOnboardingStore((s) => s.refresh);

  // 从localStorage恢复token
  useEffect(() => {
    useAuthStore.getState().restore();
  }, []);

  // 首次进入受保护区域时拉取用户信息（若 store 中没有）
  // 跳过公开路径（/legal），避免登录前查看协议被重定向
  useEffect(() => {
    if (isPathPublic(pathname)) return;
    if (!user && !fetched) {
      setFetched(true);
      const { token } = useAuthStore.getState();
      if (token) {
        fetchUser().then(u => {
          if (!u) {
            router.replace("/login");
          }
        });
      } else {
        router.replace("/login");
      }
    }
  }, [user, fetched, fetchUser, router, pathname]);

  // 用户加载完成后，拉取 onboarding 状态
  useEffect(() => {
    if (user && onboardingCompleted === null) {
      refreshOnboarding();
    }
  }, [user, onboardingCompleted, refreshOnboarding]);

  // 如果未完成 onboarding 且当前不在 onboarding 页面，自动跳转
  // 跳过公开路径，避免登录前查看协议时触发 onboarding 跳转
  useEffect(() => {
    if (isPathPublic(pathname)) return;
    if (
      onboardingCompleted === false &&
      pathname !== "/onboarding" &&
      !pathname.startsWith("/onboarding")
    ) {
      router.replace("/onboarding");
    }
  }, [onboardingCompleted, pathname, router]);

  return (
    <AuthGuard>
      <div className="min-h-screen bg-paper-100 flex flex-col">
        <AppNav />
        <main className="md:pl-64 flex-1">
          <div className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">
            {children}
          </div>
        </main>
        <footer className="md:pl-64 border-t border-paper-300 bg-paper-100">
          <div className="mx-auto max-w-6xl px-4 md:px-8 py-6 flex flex-col md:flex-row gap-3 md:items-center md:justify-between text-xs text-ink-500">
            <p>© {new Date().getFullYear()} GradPath · 职径 · 职业轨迹</p>
            <nav className="flex flex-wrap gap-4">
              <Link href="/legal/privacy" className="hover:text-brand-600 hover:underline">
                隐私政策
              </Link>
              <Link href="/legal/terms" className="hover:text-brand-600 hover:underline">
                用户协议
              </Link>
              <Link href="/legal/cookie" className="hover:text-brand-600 hover:underline">
                Cookie 政策
              </Link>
              <Link href="/legal" className="hover:text-brand-600 hover:underline">
                法律文件
              </Link>
            </nav>
          </div>
        </footer>
      </div>
    </AuthGuard>
  );
}
