"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  LayoutDashboard,
  Shield,
  Flag,
  Users,
  Bug,
  Inbox,
  Network,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { LoadingState } from "@/components/ui/empty";

const ADMIN_TABS = [
  { href: "/admin", label: "后台首页", icon: LayoutDashboard, exact: true },
  { href: "/admin/moderation", label: "内容审核", icon: Shield },
  { href: "/admin/reports", label: "举报管理", icon: Flag },
  { href: "/admin/users", label: "用户管理", icon: Users },
  { href: "/admin/crawlers", label: "爬虫管理", icon: Bug },
  { href: "/admin/research-queue", label: "调研数据", icon: Inbox },
  { href: "/admin/skills", label: "技能管理", icon: Network },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);

  // 非管理员重定向（与各 admin 子页守卫一致，统一收敛到 layout）
  useEffect(() => {
    if (hydrated && user && !user.is_admin) {
      router.replace("/dashboard");
    }
  }, [hydrated, user, router]);

  if (!hydrated || !user) {
    return <LoadingState text="加载中…" />;
  }
  if (!user.is_admin) {
    return <LoadingState text="无权访问，正在跳转…" />;
  }

  return (
    <div className="min-h-screen bg-paper-50">
      {/* 横向子导航 */}
      <div className="sticky top-0 z-20 border-b border-paper-300 bg-paper-50/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center gap-1 overflow-x-auto px-4 py-3">
          {ADMIN_TABS.map((tab) => {
            const Icon = tab.icon;
            const active = tab.exact
              ? pathname === tab.href
              : pathname === tab.href || pathname.startsWith(tab.href + "/");
            return (
              <Link
                key={tab.href}
                href={tab.href}
                data-track-id={`admin-nav:${tab.href}`}
                className={cn(
                  "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-brand-600 text-white shadow-brand-sm"
                    : "text-ink-500 hover:bg-paper-200 hover:text-ink-800",
                )}
              >
                <Icon className="h-4 w-4" strokeWidth={1.8} />
                {tab.label}
              </Link>
            );
          })}
        </div>
      </div>
      <div className="mx-auto max-w-6xl px-4 py-6">{children}</div>
    </div>
  );
}
