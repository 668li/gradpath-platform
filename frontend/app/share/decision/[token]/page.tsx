import type { Metadata } from "next";
import { ShareContent } from "./content";

export const dynamic = "force-dynamic";

// 服务端组件不能走浏览器同源 /api 代理（相对 URL 在 Node 端无法解析）。
// 直接取 next.config.js rewrites 同一来源的绝对后端地址。
// Next.js 允许查询串覆盖 process.env（SSRF 面），故后端 host 走显式白名单：
// 只放行本机与 Docker 内部名，阻断经查询串指向任意主机（内网/云元数据）。
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8001";
const ALLOWED_BACKEND_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "backend"]);
const SHARE_TOKEN_RE = /^[A-Za-z0-9_-]{16,64}$/;

function safeBackendBase(): string | null {
  try {
    const u = new URL(BACKEND_URL);
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    if (!ALLOWED_BACKEND_HOSTS.has(u.hostname)) return null;
    return u.origin;
  } catch {
    return null;
  }
}

async function getShareData(token: string) {
  try {
    if (!SHARE_TOKEN_RE.test(token)) return null;
    const base = safeBackendBase();
    if (!base) return null;
    const resp = await fetch(`${base}/api/share/decision/${token}`, {
      cache: "no-store",
    });
    if (!resp.ok) return null;
    return resp.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { token: string };
}): Promise<Metadata> {
  const data = await getShareData(params.token);
  if (!data) {
    return { title: "分享链接无效 | GradPath" };
  }
  const input = data.input ?? {};
  const major = String(input.major ?? "我的专业");
  const year = String(input.graduation_year ?? 2026);
  const title = `${major} · ${year}届报考决策报告 | GradPath`;
  return {
    title,
    description: `${major} · ${year}届的三路报考对比（考研 / 考公 / 就业），每个数字可溯源，数据覆盖有限时如实标注。`,
    openGraph: {
      title,
      description: `${major} · ${year}届的三路报考对比，每个数字可溯源。`,
      type: "website",
    },
  };
}

export default async function Page({
  params,
}: {
  params: { token: string };
}) {
  return <ShareContent token={params.token} />;
}
