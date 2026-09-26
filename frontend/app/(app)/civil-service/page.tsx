import { redirect } from "next/navigation";

// 2026-09-26 考公线退役：本页随线隐藏（见 docs/数据供给总纲-爬取跟随决策-2026-09-26.md）。
export default function RetiredPage() {
  redirect("/dashboard");
}
