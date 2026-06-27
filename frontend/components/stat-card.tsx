import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  hint?: string;
  color?: "blue" | "green" | "amber" | "purple";
}

const colorMap = {
  blue: "bg-blue-50 text-blue-600",
  green: "bg-green-50 text-green-600",
  amber: "bg-amber-50 text-amber-600",
  purple: "bg-purple-50 text-purple-600",
};

export function StatCard({ label, value, icon, hint, color = "blue" }: StatCardProps) {
  return (
    <div className="card flex items-center gap-4">
      <div
        className={cn(
          "flex h-12 w-12 items-center justify-center rounded-xl",
          colorMap[color],
        )}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-slate-500">{label}</p>
        <p className="text-2xl font-bold text-slate-800 leading-tight">{value}</p>
        {hint && <p className="text-xs text-slate-400 truncate">{hint}</p>}
      </div>
    </div>
  );
}
