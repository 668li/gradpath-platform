"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * 可折叠区域 — 用于 Dashboard 信息分层。
 * 首屏核心内容直接展示，详细模块折叠在下方，用户按需展开。
 */
export function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-paper-200 bg-white/60">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-paper-50"
        aria-expanded={open}
      >
        <div>
          <h2 className="text-sm font-semibold text-ink-700">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-ink-400">{subtitle}</p>}
        </div>
        <ChevronDown
          className={cn(
            "h-5 w-5 text-ink-400 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>
      {open && <div className="px-5 pb-5 space-y-6">{children}</div>}
    </div>
  );
}
