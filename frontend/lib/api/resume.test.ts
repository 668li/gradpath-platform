// 续学卡 helper 测试（P1）
import { describe, it, expect } from "vitest";
import { findNextPendingTask } from "@/lib/api/resume";
import type { MicroActionPlanResponse } from "@/types/micro-action";

function makePlan(overrides: Partial<MicroActionPlanResponse> = {}): MicroActionPlanResponse {
  return {
    id: "plan-1",
    target_path: "employment",
    target_role: null,
    status: "active",
    started_at: "2026-09-01T00:00:00Z",
    completed_at: null,
    progress: 0,
    self_discovery_report: null,
    tasks: [
      { id: "t1", day_number: 1, task_type: "research", title: "查 3 个目标 JD", description: "", estimated_minutes: 20, status: "completed", completed_at: null, user_response: null, insight: null },
      { id: "t2", day_number: 2, task_type: "research", title: "看 2 个岗位 vlog", description: "", estimated_minutes: 20, status: "pending", completed_at: null, user_response: null, insight: null },
      { id: "t3", day_number: 3, task_type: "interview", title: "约 1 位从业者", description: "", estimated_minutes: 30, status: "pending", completed_at: null, user_response: null, insight: null },
    ],
    ...overrides,
  };
}

describe("findNextPendingTask", () => {
  it("返回第一个未完成任务（按 day_number 升序）", () => {
    const task = findNextPendingTask(makePlan());
    expect(task).toEqual({ id: "t2", day_number: 2, title: "看 2 个岗位 vlog" });
  });

  it("乱序任务列表也能取到最小的 day_number", () => {
    const plan = makePlan();
    const day3 = { ...plan.tasks[1], id: "t3", day_number: 3, title: "约 1 位从业者" };
    const task = findNextPendingTask({ ...plan, tasks: [day3, plan.tasks[1]] });
    expect(task?.day_number).toBe(2);
  });

  it("全部完成时返回 null", () => {
    const plan = makePlan();
    expect(
      findNextPendingTask({
        ...plan,
        tasks: plan.tasks.map((t) => ({ ...t, status: "completed" })),
      }),
    ).toBeNull();
  });

  it("plan 非 active 时返回 null", () => {
    expect(findNextPendingTask(makePlan({ status: "abandoned" }))).toBeNull();
    expect(findNextPendingTask(makePlan({ status: "completed" }))).toBeNull();
  });

  it("plan 为 null/undefined 时返回 null", () => {
    expect(findNextPendingTask(null)).toBeNull();
    expect(findNextPendingTask(undefined)).toBeNull();
  });
});
