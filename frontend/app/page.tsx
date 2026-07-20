import { cookies } from "next/headers";
import { redirect } from "next/navigation";

/**
 * 根页面：服务端快速重定向。
 * 读取 gradpath_token cookie，有 token 去 dashboard，没有去 login。
 * 零 JS 依赖，瞬间跳转，不卡 spinner。
 */
export default function HomePage() {
  const cookieStore = cookies();
  const token = cookieStore.get("gradpath_token")?.value;

  if (token) {
    redirect("/dashboard");
  } else {
    redirect("/login");
  }
}
