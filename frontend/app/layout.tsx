import type { Metadata } from "next";
import "./globals.css";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";
import { RootLayoutClient } from "./layout-client";

// 优化：精简字体文件，仅保留常用字重（400/500/600/700），减少约60%字体文件下载量
const fraunces = Fraunces({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  weight: ["400", "700"],
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
  weight: ["400", "500", "700"],
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
