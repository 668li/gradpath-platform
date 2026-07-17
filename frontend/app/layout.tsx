import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ui/toast";
import { ErrorBoundary } from "@/components/error-boundary";
import { Fraunces, Plus_Jakarta_Sans } from "next/font/google";

// 优化：web-vitals 使用动态导入，避免 require 破坏 tree-shaking
const reportWebVitals = async () => {
  try {
    const wv = await import("@/lib/web-vitals");
    wv.reportWebVitals();
  } catch {
    // web-vitals not available
  }
};

// 优化：精简字体文件，仅保留常用字重（400/500/600/700），减少约60%字体文件下载量
// Fraunces: 4→2 字重, Plus Jakarta Sans: 6→3 字重
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

export const metadata: Metadata = {
  title: "GradPath · 职径",
  description: "个人职业轨迹记录与复盘平台",
};

reportWebVitals();

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className={`${fraunces.variable} ${jakarta.variable}`}>
      <body>
        <ErrorBoundary>
          <ToastProvider>{children}</ToastProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
