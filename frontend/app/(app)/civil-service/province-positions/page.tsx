import { redirect } from "next/navigation";

/** 省考职位检索页随职位数据删除下架（09-12 战略转向）：302 回考公中心。 */
export default function ProvincePositionsPage() {
  redirect("/civil-service");
}
