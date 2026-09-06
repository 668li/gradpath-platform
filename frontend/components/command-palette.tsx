"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { useRouter } from "next/navigation";
import * as LucideIcons from "lucide-react";
import { Search, CornerDownLeft, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { commands, type Command } from "@/lib/commands";

/**
 * 全局命令面板 (Cmd+K / Ctrl+K)
 *
 * - 在 document 上监听 Cmd+K / Ctrl+K 打开,Escape 关闭
 * - 顶部居中浮层 + 毛玻璃背景,参考 Raycast / Spotlight
 * - 键盘 ↑↓ 选择,Enter 跳转;点击命令也跳转
 * - 跳转后自动关闭
 * - 移动端:点击触发按钮打开,触摸友好
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const router = useRouter();
  const isAdmin = useAuthStore((s) => !!s.user?.is_admin);

  // ── 全局快捷键 ────────────────────────────────────────────
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape" && open) {
        e.preventDefault();
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  // 监听自定义事件,允许其他组件 (例如 nav 中的 ⌘K 按钮) 打开面板
  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener("gradpath:open-command-palette", onOpen);
    return () =>
      window.removeEventListener("gradpath:open-command-palette", onOpen);
  }, []);

  // ── 打开/关闭时的副作用 ──────────────────────────────────
  useEffect(() => {
    if (open) {
      // 等待 DOM 渲染后聚焦输入框
      const t = window.setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 0);
      return () => window.clearTimeout(t);
    }
    // 关闭时清理状态
    setQuery("");
    setActiveIndex(0);
  }, [open]);

  // 锁定背景滚动
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // ── 过滤命令 ──────────────────────────────────────────────
  const visibleCommands = useMemo(
    () => commands.filter((cmd) => !cmd.admin || isAdmin),
    [isAdmin],
  );
  const filtered = useMemo<Command[]>(() => {
    const q = query.trim().toLowerCase();
    if (!q) return visibleCommands;
    return visibleCommands.filter((cmd) => {
      const hay = [
        cmd.title,
        cmd.subtitle ?? "",
        cmd.href,
        ...(cmd.keywords ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return q.split(/\s+/).every((token) => hay.includes(token));
    });
  }, [query, visibleCommands]);

  // 当查询变化时重置 active index
  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  // ── 跳转 ──────────────────────────────────────────────────
  const go = useCallback(
    (cmd: Command) => {
      setOpen(false);
      router.push(cmd.href);
    },
    [router],
  );

  // ── 键盘导航 ──────────────────────────────────────────────
  const handleKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => (i + 1) % Math.max(filtered.length, 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) =>
        i <= 0 ? Math.max(filtered.length - 1, 0) : i - 1,
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = filtered[activeIndex];
      if (target) go(target);
    }
  };

  // 滚动激活项到可见区
  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector<HTMLElement>(
      `[data-cmd-index="${activeIndex}"]`,
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, open]);

  // 分组渲染:保留 commands 顺序,按 subtitle 分组
  // 注意: useMemo 必须在条件 return 之前调用,以保持 hooks 调用顺序稳定
  const groups = useMemo(() => {
    const map = new Map<string, { cmd: Command; index: number }[]>();
    filtered.forEach((cmd, idx) => {
      const group = cmd.subtitle ?? "其他";
      const arr = map.get(group) ?? [];
      arr.push({ cmd, index: idx });
      map.set(group, arr);
    });
    return Array.from(map.entries());
  }, [filtered]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center px-4 pt-[12vh] sm:pt-[15vh]"
      role="dialog"
      aria-modal="true"
      aria-label="命令面板"
    >
      {/* 背景遮罩 */}
      <button
        type="button"
        aria-label="关闭命令面板"
        onClick={() => setOpen(false)}
        className="absolute inset-0 cursor-default bg-ink-900/50 backdrop-blur-sm"
      />

      {/* 面板 */}
      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-ink-700/60 bg-ink-800 shadow-2xl">
        {/* 顶部搜索框 */}
        <div className="flex items-center gap-3 border-b border-ink-700/60 px-4">
          <Search
            className="h-5 w-5 shrink-0 text-ink-400"
            strokeWidth={1.8}
          />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索页面或命令…"
            className="flex-1 bg-transparent py-4 text-base text-paper-50 placeholder:text-ink-500 focus:outline-none"
            autoComplete="off"
            spellCheck={false}
          />
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="flex h-7 w-7 items-center justify-center rounded-md text-ink-400 hover:bg-ink-700/60 hover:text-paper-100 transition-colors"
            aria-label="关闭"
          >
            <X className="h-4 w-4" strokeWidth={2} />
          </button>
        </div>

        {/* 命令列表 */}
        {filtered.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-ink-400">
            未找到匹配的命令
          </div>
        ) : (
          <ul
            ref={listRef}
            className="max-h-[55vh] overflow-y-auto py-2"
          >
            {groups.map(([groupName, items]) => (
              <li key={groupName} className="mb-1">
                <p className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-ink-500">
                  {groupName}
                </p>
                <ul>
                  {items.map(({ cmd, index }) => (
                    <CommandRow
                      key={cmd.id}
                      cmd={cmd}
                      active={index === activeIndex}
                      onSelect={() => go(cmd)}
                      onHover={() => setActiveIndex(index)}
                      index={index}
                    />
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}

        {/* 底部提示条 */}
        <div className="flex items-center justify-between border-t border-ink-700/60 px-4 py-2 text-[11px] text-ink-500">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Kbd>↑</Kbd>
              <Kbd>↓</Kbd>
              <span className="ml-1">导航</span>
            </span>
            <span className="flex items-center gap-1">
              <Kbd>↵</Kbd>
              <span className="ml-1">跳转</span>
            </span>
            <span className="flex items-center gap-1">
              <Kbd>esc</Kbd>
              <span className="ml-1">关闭</span>
            </span>
          </div>
          <span className="text-ink-500">{filtered.length} 个结果</span>
        </div>
      </div>
    </div>
  );
}

function CommandRow({
  cmd,
  active,
  onSelect,
  onHover,
  index,
}: {
  cmd: Command;
  active: boolean;
  onSelect: () => void;
  onHover: () => void;
  index: number;
}) {
  const Icon = resolveIcon(cmd.icon);
  return (
    <li data-cmd-index={index} role="option" aria-selected={active}>
      <button
        type="button"
        onClick={onSelect}
        onMouseEnter={onHover}
        className={cn(
          "group flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
          active ? "bg-brand-500/15 text-paper-50" : "text-ink-200",
        )}
      >
        <span
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
            active
              ? "bg-brand-500/20 text-brand-300"
              : "bg-ink-700/40 text-ink-400",
          )}
        >
          <Icon className="h-4 w-4" strokeWidth={1.8} />
        </span>
        <span className="flex-1 min-w-0">
          <span className="block truncate text-sm font-medium text-paper-100">
            {cmd.title}
          </span>
          <span className="block truncate text-[11px] text-ink-500">
            {cmd.href}
          </span>
        </span>
        {active && (
          <CornerDownLeft
            className="h-4 w-4 shrink-0 text-ink-400"
            strokeWidth={1.6}
          />
        )}
      </button>
    </li>
  );
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-5 min-w-[20px] items-center justify-center rounded border border-ink-700 bg-ink-900/60 px-1 text-[10px] font-medium text-ink-300">
      {children}
    </kbd>
  );
}

/**
 * 根据 lucide icon 名解析出对应组件。
 * 找不到时回退到 Search 图标,保证渲染不报错。
 */
function resolveIcon(name?: string): LucideIcons.LucideIcon {
  if (!name) return Search;
  const icon = (LucideIcons as Record<string, unknown>)[name];
  if (typeof icon === "function") return icon as LucideIcons.LucideIcon;
  return Search;
}

/**
 * 程序化打开命令面板。供 nav 等外部组件调用。
 * 例: <button onClick={() => openCommandPalette()}>⌘K</button>
 */
export function openCommandPalette() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event("gradpath:open-command-palette"));
}
