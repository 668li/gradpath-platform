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
  PieChart,
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
  BookOpen,
  UserCircle,
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
    { href: "/profile", label: "职业画像", icon: UserCircle },
    { href: "/assessment", label: "职业测评", icon: Compass },
    { href: "/life-wheel", label: "人生平衡轮", icon: PieChart },
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
    items.push({ href: "/knowledge", label: "知识库", icon: BookOpen });
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
      {/* Logo — display font, warm accent on dark */}
      <div className="flex items-center gap-3 px-5 py-6 border-b border-ink-700/50">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500 text-white shadow-brand-sm">
          <GraduationCap className="h-5 w-5" strokeWidth={2.2} />
        </div>
        <div>
          <p className="font-display text-lg font-semibold text-paper-50 leading-tight tracking-tight">
            GradPath
          </p>
          <p className="text-[11px] text-ink-400 leading-tight tracking-wide">
            职径 · 职业轨迹
          </p>
        </div>
      </div>

      {/* Nav items — warm text on dark, brand accent for active */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
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
                "group relative flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                active
                  ? "bg-brand-500/15 text-brand-300"
                  : "text-ink-300 hover:bg-ink-700/40 hover:text-paper-100",
              )}
            >
              {/* Active left accent bar */}
              {active && (
                <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-brand-400" />
              )}
              <Icon
                className={cn(
                  "h-[18px] w-[18px] transition-colors",
                  active
                    ? "text-brand-400"
                    : "text-ink-400 group-hover:text-paper-200",
                )}
                strokeWidth={active ? 2.2 : 1.8}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User area — subtle card on dark */}
      <div className="border-t border-ink-700/50 px-3 py-3 space-y-1">
        <div className="flex items-center gap-2.5 rounded-lg px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/20 text-sm font-semibold text-brand-300 ring-1 ring-brand-500/30">
            {user?.name?.[0] ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium text-paper-100">
              {user?.name ?? "用户"}
            </p>
            <p className="truncate text-[11px] text-ink-400">
              {user?.email ?? ""}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-ink-400 hover:bg-red-500/10 hover:text-red-400 transition-colors"
        >
          <LogOut className="h-[18px] w-[18px]" strokeWidth={1.8} />
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

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const closeBtn = panel?.querySelector<HTMLButtonElement>("[data-close]");
    closeBtn?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
        return;
      }
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
      prevActive?.focus?.();
    };
  }, [open]);

  return (
    <>
      {/* 桌面端固定侧边栏 — 深色"期刊书脊" */}
      <aside className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 bg-ink-800">
        <SidebarContent />
      </aside>

      {/* 移动端顶栏 */}
      <div className="md:hidden sticky top-0 z-30 flex items-center justify-between border-b border-paper-300 bg-paper-50 px-4 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-white shadow-brand-sm">
            <GraduationCap className="h-5 w-5" strokeWidth={2.2} />
          </div>
          <span className="font-display font-semibold text-ink-800 tracking-tight">
            GradPath
          </span>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-ink-500 hover:text-ink-800 hover:bg-paper-200 transition-colors"
          aria-label="打开菜单"
        >
          <Menu className="h-6 w-6" strokeWidth={1.8} />
        </button>
      </div>

      {/* 移动端抽屉 */}
      {open && (
        <div className="md:hidden fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-ink-900/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="导航菜单"
            className="absolute left-0 top-0 h-full w-72 bg-ink-800 shadow-2xl"
          >
            <button
              onClick={() => setOpen(false)}
              data-close
              className="absolute right-2 top-2 z-10 flex h-11 w-11 items-center justify-center rounded-lg text-ink-400 hover:text-paper-50 hover:bg-ink-700 transition-colors"
              aria-label="关闭菜单"
            >
              <X className="h-5 w-5" strokeWidth={1.8} />
            </button>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
