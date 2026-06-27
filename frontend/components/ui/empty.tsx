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
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/50 px-6 py-12 text-center",
        className,
      )}
    >
      <Inbox className="h-10 w-10 text-slate-300" />
      <p className="mt-3 text-base font-medium text-slate-600">{title}</p>
      {description && (
        <p className="mt-1 text-sm text-slate-400 max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function LoadingState({ text = "加载中…" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-slate-400">
      <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
      <span className="ml-2 text-sm">{text}</span>
    </div>
  );
}
