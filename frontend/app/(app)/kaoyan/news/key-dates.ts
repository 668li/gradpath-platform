// app/(app)/kaoyan/news/key-dates.ts
/**
 * 关键日期倒计时工具 — 资讯中心/详情页共用。
 *
 * 后端 research_promote.extract_key_dates 产出 [{label, date, end_date?}]。
 * 这里只做展示计算：距关键日期的天数、是否已过期、是否紧急。
 */
import type { KaoyanKeyDate } from "@/types";

/** 距目标日期天数（今天为 0 天，已过为负数）。入参 yyyy-mm-dd。 */
export function daysUntil(dateStr: string): number {
  const target = new Date(`${dateStr}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86400000);
}

export interface CountdownInfo {
  date: string;
  days: number;
  /** 已过期 */
  expired: boolean;
  /** 10 天内临近（含今天） */
  urgent: boolean;
  /** 展示文案，如「距报名截止 12 天」/「已过 3 天」/「今天截止」 */
  text: string;
}

export function countdownOf(kd: KaoyanKeyDate): CountdownInfo {
  const days = daysUntil(kd.date);
  const expired = days < 0;
  const urgent = !expired && days <= 10;
  let text: string;
  if (expired) {
    text = days === -1 ? "昨天截止" : `已过 ${-days} 天`;
  } else if (days === 0) {
    text = "今天截止";
  } else if (days === 1) {
    text = "明天截止";
  } else {
    text = `距${kd.label} ${days} 天`;
  }
  return { date: kd.date, days, expired, urgent, text };
}

/** 取最紧急（最近且未过期）的关键日期用于卡片高亮；无则返回 null。 */
export function mostUrgentKeyDate(keyDates: KaoyanKeyDate[] | undefined): CountdownInfo | null {
  if (!keyDates?.length) return null;
  const active = keyDates
    .map(countdownOf)
    .filter((c) => !c.expired)
    .sort((a, b) => a.days - b.days);
  return active[0] ?? null;
}

/** 卡片/详情统一的时间格式化。 */
export function formatDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("zh-CN");
}
