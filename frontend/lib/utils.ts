import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** 合并 Tailwind class，处理冲突 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 格式化日期 YYYY-MM-DD → YYYY年M月D日 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
}

/** 获取今天日期，格式 YYYY-MM-DD（用于 input[type=date] 默认值） */
export function todayISO(): string {
  const d = new Date();
  const tz = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tz).toISOString().slice(0, 10);
}

/** 数字转星标等级显示 */
export function levelStars(level: number, max = 5): string {
  return "★".repeat(level) + "☆".repeat(Math.max(0, max - level));
}
