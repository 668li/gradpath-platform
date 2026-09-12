import { redirect } from "next/navigation";

/**
 * 免费可报性预览（搜职位/院校 → 勾身份 → 出判定）已随 2026-09-12 战略转向下架：
 * 职位数据已全删、判定漏斗降级为辅助，不再作为公开门面。
 * 老分享链接一律 302 回落地页，不留 404（P2 收敛纪律同款）。
 */
export default function PreviewPage() {
  redirect("/");
}
