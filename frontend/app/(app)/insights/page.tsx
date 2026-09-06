import { redirect } from "next/navigation";

/**
 * P2 合并：成长洞察已并入 /achievements（成长回顾）。
 * 常规流量由 next.config redirects 在 /insights 处 302，此页仅作直达兜底。
 */
export default function InsightsPage() {
  redirect("/achievements");
}
