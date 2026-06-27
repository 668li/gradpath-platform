import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ui/toast";

export const metadata: Metadata = {
  title: "GradPath · 职径",
  description: "个人职业轨迹记录与复盘平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
