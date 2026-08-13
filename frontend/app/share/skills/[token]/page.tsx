import type { Metadata } from "next";
import { ShareContent } from "./content";

export const dynamic = "force-dynamic";

async function getShareData(token: string) {
  try {
    // 走同源 /api 代理（next.config.js rewrites → BACKEND_URL），
    // 避免在源码中写死后端地址。
    const resp = await fetch(`/api/share/skills/${token}`, { cache: "no-store" });
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
  return {
    title: `${data.user_name}的技能树 | GradPath`,
    description: `查看 ${data.user_name} 的技能成长轨迹`,
    openGraph: {
      title: `${data.user_name}的技能树 | GradPath`,
      description: `查看 ${data.user_name} 的技能成长轨迹`,
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
