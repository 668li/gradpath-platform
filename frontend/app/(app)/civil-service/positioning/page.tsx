import { redirect } from "next/navigation";

// 2026-09-26 考公线退役：本页随线隐藏（见 docs/数据供给总纲-爬取跟随决策-2026-09-26.md）。
// force-dynamic：静态化会让 redirect 壳被 ISR 缓存钉死一年（R-07），必须每次请求动态 307。
export const dynamic = "force-dynamic";

export default function RetiredPage() {
  redirect("/dashboard");
}
