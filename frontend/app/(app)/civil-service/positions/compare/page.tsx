import { redirect } from "next/navigation";

/** 职位对比随职位检索一并下架（09-12 战略转向）：302 回考公中心。 */
export default function PositionsComparePage() {
  redirect("/civil-service");
}
