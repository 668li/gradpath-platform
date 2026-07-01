"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Telescope,
  Compass,
  History,
  Network,
  ClipboardList,
  LogOut,
  Menu,
  X,
  GraduationCap,
  Briefcase,
  Users,
  Database,
  TrendingUp,
  Award,
  Bot,
  Target,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";

interface NavItem {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
}

/** 根据是否为管理员生成导航项列表 */
function getNavItems(isAdmin: boolean = false): NavItem[] {
  const items: NavItem[] = [
    { href: "/dashboard", label: "个人看板", icon: LayoutDashboard },
    { href: "/chat", label: "AI 管家", icon: Bot },
    { href: "/plans", label: "职业规划", icon: Target },
    { href: "/explore", label: "去向探索", icon: Telescope },
    { href: "/community", label: "社区数据", icon: Users },
    { href: "/interview", label: "面试经验", icon: Briefcase },
    { href: "/decisions", label: "去向决策", icon: Compass },
    { href: "/timeline", label: "成长时间线", icon: History },
    { href: "/skills", label: "技能树", icon: Network },
    { href: "/retrospectives", label: "阶段复盘", icon: ClipboardList },
    { href: "/insights", label: "成长洞察", icon: TrendingUp },
    { href: "/achievements", label: "成就", icon: Award },
  ];
  if (isAdmin) {
    items.push({ href: "/pipeline", label: "数据管道", icon: Database });
  }
  return items;
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navItems = getNavItems(user?.is_admin);

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-slate-100">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
          <GraduationCap className="h-5 w-5" />
        </div>
        <div>
          <p className="text-base font-semibold text-slate-800 leading-tight">GradPath</p>
          <p className="text-xs text-slate-400 leading-tight">职径 · 职业轨迹</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-800",
              )}
            >
              <Icon className={cn("h-[18px] w-[18px]", active && "text-brand-600")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-100 px-3 py-3">
        <div className="flex items-center gap-2 rounded-lg px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-sm font-medium text-slate-600">
            {user?.name?.[0] ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium text-slate-700">
              {user?.name ?? "用户"}
            </p>
            <p className="truncate text-xs text-slate-400">
              {user?.email ?? ""}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="mt-1 flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut className="h-[18px] w-[18px]" />
          退出登录
        </button>
      </div>
    </div>
  );
}

export function AppNav() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // 抽屉打开时：锁定 body 滚动、Escape 关闭、焦点陷阱、关闭后恢复焦点
  useEffect(() => {
    if (!open) return;

    const panel = panelRef.current;
    const prevActive = document.activeElement as HTMLElement | null;

    // 锁定背景滚动，关闭时恢复
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // 打开时聚焦关闭按钮，便于键盘操作
    const closeBtn = panel?.querySelector<HTMLButtonElement>("[data-close]");
    closeBtn?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
        return;
      }
      // 焦点陷阱：Tab / Shift+Tab 在抽屉内循环，避免逃逸到背景
      if (e.key !== "Tab" || !panel) return;
      const focusable = panel.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      // 关闭后把焦点还给触发元素
      prevActive?.focus?.();
    };
  }, [open]);

  return (
    <>
      {/* 桌面端固定侧边栏 */}
      <aside className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 bg-white border-r border-slate-200">
        <SidebarContent />
      </aside>

      {/* 移动端顶栏 */}
      <div className="md:hidden sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
            <GraduationCap className="h-5 w-5" />
          </div>
          <span className="font-semibold text-slate-800">GradPath</span>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="flex h-11 w-11 items-center justify-center rounded-md text-slate-600 hover:text-slate-800 hover:bg-slate-100 transition-colors"
          aria-label="打开菜单"
        >
          <Menu className="h-6 w-6" />
        </button>
      </div>

      {/* 移动端抽屉 */}
      {open && (
        <div className="md:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="导航菜单"
            className="absolute left-0 top-0 h-full w-72 bg-white shadow-xl"
          >
            <button
              onClick={() => setOpen(false)}
              data-close
              className="absolute right-2 top-2 z-10 flex h-11 w-11 items-center justify-center rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="关闭菜单"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
