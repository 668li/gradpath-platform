// 续学卡 helper（P1）— 从当前微行动计划中找到"上次停在哪"。
// 属于 frontend/lib/api/ 下的小 helper，无副作用，便于单测与复用。
import type { MicroActionPlanResponse } from "@/types/micro-action";

export interface NextPendingTask {
  id: string;
  day_number: number;
  title: string;
}

/** 从当前 plan 中提取第一个待办任务（按 day_number 升序）。 */
export function findNextPendingTask(
  plan: MicroActionPlanResponse | null | undefined,
): NextPendingTask | null {
  if (!plan || plan.status !== "active" || !Array.isArray(plan.tasks)) return null;
  const pending = plan.tasks
    .filter((t) => t.status === "pending")
    .sort((a, b) => a.day_number - b.day_number);
  const first = pending[0];
  if (!first) return null;
  return { id: first.id, day_number: first.day_number, title: first.title };
}
