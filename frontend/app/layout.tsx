import type { Metadata } from "next";
import "./globals.css";
import localFont from "next/font/local";
import { RootLayoutClient } from "./layout-client";

// 字重覆盖 400/500/600/700，匹配全站 font-medium / font-semibold / font-bold 使用
// 自托管 woff2：服务器构建环境无法访问 Google Fonts，next/font/google 会在 BuildKit
// 字体缓存被 prune 后必然构建失败（2026-09-04 部署事故），本地字体彻底去掉构建期网络依赖。
const fraunces = localFont({
  src: [
    { path: "./fonts/fraunces-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/fraunces-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/fraunces-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  display: "swap",
  variable: "--font-display",
});

const jakarta = localFont({
  src: [
    { path: "./fonts/plus-jakarta-sans-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/plus-jakarta-sans-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/plus-jakarta-sans-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/plus-jakarta-sans-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  display: "swap",
  variable: "--font-sans",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://gradpath.example.com";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "GradPath · 职径",
  description: "个人职业轨迹记录与复盘平台",
  openGraph: {
    title: "GradPath · 职径",
    description: "个人职业轨迹记录与复盘平台",
    type: "website",
    url: siteUrl,
    siteName: "GradPath · 职径",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "GradPath · 职径",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "GradPath · 职径",
    description: "个人职业轨迹记录与复盘平台",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className={`${fraunces.variable} ${jakarta.variable}`}>
      <body>
        <RootLayoutClient>{children}</RootLayoutClient>
      </body>
    </html>
  );
}
