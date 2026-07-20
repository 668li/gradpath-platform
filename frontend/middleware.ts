import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Edge Middleware 路由守卫
 *
 * 通过读取 cookie `gradpath_token` 判断登录态（客户端 lib/api/client.ts
 * 在 setToken / clearToken 时会同步维护该 cookie）。未登录访问受保护
 * 路由时重定向到 /login?redirect=<原路径>；已登录访问 /login 或 /register
 * 时重定向到 /dashboard。
 *
 * 客户端 `app/(app)/layout.tsx` 中的 useEffect 与 `components/auth-guard.tsx`
 * 仍保留作为兜底（middleware 失效或客户端导航时）。
 */
const TOKEN_COOKIE = "gradpath_token";

// 受保护路径前缀（匹配以这些路径开头，含子路径）
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/employment",
  "/war-room",
  "/career",
  "/kaoyan",
  "/civil-service",
  "/profile",
  "/chat",
  "/decisions",
  "/decision-lab",
  "/growth",
  "/growth-patterns",
  "/life-wheel",
  "/skills",
  "/retrospectives",
  "/mentors",
  "/achievements",
  "/onboarding",
  "/admin",
  "/ai-butler",
  "/assessment",
  "/career-simulator",
  "/community",
  "/explore",
  "/insights",
  "/interview",
  "/knowledge",
  "/learning-methods",
  "/learning-resources",
  "/life-design",
  "/notifications",
  "/outcome-report",
  "/pipeline",
  "/plans",
  "/search",
  "/study-plans",
  "/timeline",
];

// 公开路径前缀（无需登录即可访问）
const PUBLIC_PREFIXES = [
  "/login",
  "/register",
  "/share",
  "/api",
  "/_next",
];

// 精确匹配的公开路径
const PUBLIC_EXACT = new Set<string>([
  "/",
  "/favicon.ico",
  "/sitemap.xml",
  "/robots.txt",
]);

function isPublic(pathname: string): boolean {
  if (PUBLIC_EXACT.has(pathname)) return true;
  // OG 图片资源：/og-image 开头（如 /og-image.png）
  if (pathname.startsWith("/og-image")) return true;
  return PUBLIC_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
}

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const token = request.cookies.get(TOKEN_COOKIE)?.value;
  const isLoggedIn = !!token;

  // 已登录用户访问 /login 或 /register → 直接跳转 dashboard
  if (isLoggedIn && (pathname === "/login" || pathname === "/register")) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }

  // 公开路径直接放行
  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  // 受保护路径未登录 → 重定向到 /login?redirect=<原路径>
  if (!isLoggedIn && isProtected(pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    const redirectTarget = pathname + (search || "");
    url.searchParams.set("redirect", redirectTarget);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  // 排除 Next.js 静态资源与 favicon，避免不必要的中间件执行
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
