import { redirect } from "next/navigation";

/**
 * 国考职位检索页已随 2026-09-12 战略转向下架：职位数据全删、查询完全外链
 * （公考雷达/官网）。老链接 302 回考公中心，不留 404。
 */
export default function PositionsPage() {
  redirect("/civil-service");
}
