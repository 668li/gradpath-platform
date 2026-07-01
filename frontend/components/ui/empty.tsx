import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-paper-300 bg-paper-50/50 px-6 py-14 text-center animate-fade-in",
        className,
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-paper-200">
        <Inbox className="h-6 w-6 text-ink-300" strokeWidth={1.5} />
      </div>
      <p className="mt-4 font-display text-base font-medium text-ink-700">{title}</p>
      {description && (
        <p className="mt-1.5 text-sm text-ink-400 max-w-sm leading-relaxed">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function LoadingState({ text = "加载中…" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-ink-400">
      <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-paper-300 border-t-brand-500" />
      <span className="ml-2 text-sm">{text}</span>
    </div>
  );
}
