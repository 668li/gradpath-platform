import { redirect } from "next/navigation";

export default function QAListRedirectPage() {
  redirect("/kaoyan/community?tab=qa");
}
