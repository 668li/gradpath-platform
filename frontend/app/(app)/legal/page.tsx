import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "法律文件 | GradPath",
  description: "GradPath 隐私政策、用户协议与 Cookie 政策",
};

export default function LegalPage() {
  const sections = [
    {
      href: "/legal/privacy",
      title: "隐私政策",
      desc: "我们收集哪些数据、如何使用、如何保护你的隐私",
    },
    {
      href: "/legal/terms",
      title: "用户协议",
      desc: "使用 GradPath 服务的条款、权利与责任",
    },
    {
      href: "/legal/cookie",
      title: "Cookie 政策",
      desc: "我们如何使用 Cookie 与本地存储",
    },
  ];

  return (
    <main className="min-h-screen bg-paper-50">
      <div className="mx-auto max-w-3xl px-4 py-12 md:py-20">
        <h1 className="font-display text-3xl md:text-4xl font-semibold text-ink-900 tracking-tight">
          法律文件
        </h1>
        <p className="mt-3 text-ink-500 leading-relaxed">
          本页汇总 GradPath（以下简称"我们"）面向用户公开的法律文档。注册或使用服务即视为你已阅读并同意以下文档。
        </p>

        <div className="mt-10 grid gap-4">
          {sections.map((s) => (
            <Link
              key={s.href}
              href={s.href}
              className="block rounded-xl border border-paper-300 bg-white p-6 hover:border-brand-400 hover:shadow-sm transition-all"
            >
              <p className="font-display text-lg font-semibold text-ink-900">{s.title}</p>
              <p className="mt-1.5 text-sm text-ink-500 leading-relaxed">{s.desc}</p>
              <p className="mt-3 text-sm font-medium text-brand-600">阅读全文 →</p>
            </Link>
          ))}
        </div>

        <div className="mt-12 rounded-xl border border-paper-300 bg-paper-100/60 p-6 text-sm text-ink-600 leading-relaxed">
          <p className="font-medium text-ink-800">联系方式</p>
          <p className="mt-2">
            如对本文档有任何疑问、行使用户权利或投诉，请发送邮件至：<span className="font-mono text-brand-700">legal@gradpath.example.com</span>
          </p>
          <p className="mt-2">我们将在 15 个工作日内回复。</p>
        </div>
      </div>
    </main>
  );
}
