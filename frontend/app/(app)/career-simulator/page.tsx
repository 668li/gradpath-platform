import { redirect } from "next/navigation";

// 2026-09-26 用户拍板：考公线整体退役 / 模拟器整站隐藏（底座数据退役，见 docs/数据供给总纲）。
// 文件保留以便恢复，入口已全部摘除。
export default function RetiredPage() {
  redirect("/dashboard");
}
