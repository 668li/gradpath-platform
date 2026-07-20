import { redirect } from "next/navigation";

export default function PostsListRedirectPage() {
  redirect("/kaoyan/community?tab=experience");
}
