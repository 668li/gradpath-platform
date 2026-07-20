"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  GraduationCap,
  Users,
  UserCircle,
  LogOut,
  Menu,
  X,
  Bell,
  Search,
  LayoutDashboard,
  Bot,
  Target,
  TrendingUp,
  ChevronDown,
  BeakerIcon,
  GitBranch,
  Route,
  BookOpen,
  Building2,
  Briefcase,
  MessageSquare,
  Brain,
  Network,
  Compass,
  Map,
  Swords,
  Calendar,
  Sparkles,
  Lightbulb,
  Trophy,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";

interface NavChild {
  href: string;
  label: string;
  icon: typeof GraduationCap;
}

interface NavSection {
  href: string;
  label: string;
  icon: typeof GraduationCap;
  section?: string;
  children?: NavChild[];
}

function getNavSections(): NavSection[] {
  return [
    {
      href: "/dashboard",
      label: "我的看板",
      icon: LayoutDashboard,
      section: "核心",
    },
    {
      href: "/decision-center",
      label: "决策中心",
      icon: Target,
      children: [
        { href: "/decision-center", label: "决策中心", icon: Target },
        { href: "/decision-lab", label: "决策实验室", icon: BeakerIcon },
        { href: "/decisions", label: "去向决策", icon: GitBranch },
        { href: "/career-simulator", label: "职业路径模拟器", icon: Route },
      ],
    },
    {
      href: "/intel",
      label: "情报中心",
      icon: Search,
      children: [
        { href: "/intel", label: "情报中心", icon: Search },
        { href: "/kaoyan", label: "考研工具箱", icon: BookOpen },
        { href: "/civil-service", label: "考公中心", icon: Building2 },
        { href: "/employment", label: "就业中心", icon: Briefcase },
        { href: "/interview", label: "面试经验", icon: MessageSquare },
      ],
    },
    {
      href: "/growth/archive",
      label: "成长档案",
      icon: TrendingUp,
      section: "成长",
      children: [
        { href: "/growth/archive", label: "成长档案", icon: TrendingUp },
        { href: "/skills", label: "技能树", icon: Network },
        { href: "/life-wheel", label: "人生平衡轮", icon: Compass },
        { href: "/retrospectives", label: "阶段复盘", icon: Calendar },
        { href: "/insights", label: "成长洞察", icon: Lightbulb },
      ],
    },
    {
      href: "/community",
      label: "社区",
      icon: Users,
    },
    {
      href: "/ai-butler",
      label: "AI 对话",
      icon: Bot,
      children: [
        { href: "/ai-butler", label: "AI 对话", icon: Bot },
        { href: "/mentors", label: "AI 导师团", icon: Brain },
        { href: "/life-design", label: "人生设计引擎", icon: Sparkles },
      ],
    },
    {
      href: "/profile",
      label: "个人中心",
      icon: UserCircle,
      section: "其他",
      children: [
        { href: "/profile", label: "个人中心", icon: UserCircle },
        { href: "/career", label: "职业规划", icon: Map },
        { href: "/study-plans", label: "学习计划", icon: Swords },
        { href: "/achievements", label: "成就墙", icon: Trophy },
      ],
    },
  ];
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const sections = useMemo(() => getNavSections(), []);

  const [unread, setUnread] = useState(0);
  useEffect(() => {
    if (!user) return;
    let mounted = true;
    import("@/lib/api").then(({ notificationsApi }) =>
      notificationsApi
        .unreadCount()
        .then((d) => mounted && setUnread(d.unread_count))
        .catch(() => {}),
    );
    return () => {
      mounted = false;
    };
  }, [user]);

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
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

      {/* Nav items */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {sections.map((section, idx) => {
          const showSectionHeader =
            !!section.section &&
            section.section !== sections[idx - 1]?.section;

          return (
            <NavSectionItem
              key={section.href}
              section={section}
              pathname={pathname}
              onNavigate={onNavigate}
              showSectionHeader={showSectionHeader}
            />
          );
        })}
      </nav>

      {/* User area */}
      <div className="border-t border-ink-700/50 px-3 py-3 space-y-1">
        <Link
          href="/notifications"
          onClick={onNavigate}
          className="relative flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-ink-300 hover:bg-ink-700/40 hover:text-paper-100 transition-colors"
        >
          <Bell className="h-[18px] w-[18px] text-ink-400" strokeWidth={1.8} />
          通知
          {unread > 0 && (
            <span className="absolute right-3 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-brand-500 px-1 text-[11px] font-semibold text-white">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </Link>
        <Link
          href="/search"
          onClick={onNavigate}
          className="flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-ink-300 hover:bg-ink-700/40 hover:text-paper-100 transition-colors"
        >
          <Search className="h-[18px] w-[18px] text-ink-400" strokeWidth={1.8} />
          搜索
        </Link>
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

function NavSectionItem({
  section,
  pathname,
  onNavigate,
  showSectionHeader,
}: {
  section: NavSection;
  pathname: string;
  onNavigate?: () => void;
  showSectionHeader: boolean;
}) {
  const hasChildren = !!section.children && section.children.length > 0;

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  const isSelfOrChildActive = hasChildren
    ? section.children!.some((c) => isActive(c.href)) || isActive(section.href)
    : isActive(section.href);

  const [expanded, setExpanded] = useState(isSelfOrChildActive);

  useEffect(() => {
    if (isSelfOrChildActive) {
      setExpanded(true);
    }
  }, [isSelfOrChildActive]);

  return (
    <div>
      {showSectionHeader && (
        <p className="px-3 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-wider text-ink-500">
          {section.section}
        </p>
      )}

      {/* Parent item */}
      {hasChildren ? (
        <button
          onClick={() => setExpanded((v) => !v)}
          className={cn(
            "group relative flex min-h-[44px] w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
            isSelfOrChildActive
              ? "bg-brand-500/15 text-brand-300"
              : "text-ink-300 hover:bg-ink-700/40 hover:text-paper-100",
          )}
        >
          {isSelfOrChildActive && (
            <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-brand-400" />
          )}
          <section.icon
            className={cn(
              "h-[18px] w-[18px] transition-colors",
              isSelfOrChildActive
                ? "text-brand-400"
                : "text-ink-400 group-hover:text-paper-200",
            )}
            strokeWidth={isSelfOrChildActive ? 2.2 : 1.8}
          />
          <span className="flex-1 text-left">{section.label}</span>
          <ChevronDown
            className={cn(
              "h-3.5 w-3.5 transition-transform duration-200",
              expanded ? "rotate-0" : "-rotate-90",
              isSelfOrChildActive ? "text-brand-400" : "text-ink-500",
            )}
            strokeWidth={2}
          />
        </button>
      ) : (
        <Link
          href={section.href}
          onClick={onNavigate}
          data-track-id={`nav:${section.href}`}
          className={cn(
            "group relative flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
            isActive(section.href)
              ? "bg-brand-500/15 text-brand-300"
              : "text-ink-300 hover:bg-ink-700/40 hover:text-paper-100",
          )}
        >
          {isActive(section.href) && (
            <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-brand-400" />
          )}
          <section.icon
            className={cn(
              "h-[18px] w-[18px] transition-colors",
              isActive(section.href)
                ? "text-brand-400"
                : "text-ink-400 group-hover:text-paper-200",
            )}
            strokeWidth={isActive(section.href) ? 2.2 : 1.8}
          />
          {section.label}
        </Link>
      )}

      {/* Children */}
      {hasChildren && expanded && (
        <div className="ml-1 space-y-0.5 overflow-hidden">
          {section.children!.map((child) => {
            const active = isActive(child.href);
            const ChildIcon = child.icon;
            return (
              <Link
                key={child.href}
                href={child.href}
                onClick={onNavigate}
                data-track-id={`nav:${child.href}`}
                className={cn(
                  "group relative flex min-h-[40px] items-center gap-3 rounded-lg pl-10 pr-3 py-2 text-[13px] font-medium transition-all duration-200",
                  active
                    ? "bg-brand-500/10 text-brand-300"
                    : "text-ink-400 hover:bg-ink-700/40 hover:text-paper-100",
                )}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-r-full bg-brand-400/60" />
                )}
                <ChildIcon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    active ? "text-brand-400" : "text-ink-500",
                  )}
                  strokeWidth={active ? 2 : 1.6}
                />
                {child.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AppNav() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

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
      <aside className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 bg-ink-800">
        <SidebarContent />
      </aside>

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
            <div className="px-3 pt-14 pb-2">
              <Link
                href="/assessment"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 px-4 py-3 text-white shadow-lg hover:from-brand-600 hover:to-brand-700 transition-all"
              >
                <Target className="h-5 w-5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold">快速开始</p>
                  <p className="text-xs text-white/80">完成评估测试，获取个性化建议</p>
                </div>
              </Link>
            </div>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}