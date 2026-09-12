import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { GraduationCap, LogIn, UserPlus } from "lucide-react";

/**
 * 根页面：公开落地页。
 *
 * 2026-09-12 战略转向：定位 = 信息差供给 + 聚合 + 流程时间线伴随（权威口号待视觉稿定稿，
 * 下方为临时文案）。有 gradpath_token 直接进 dashboard；未登录渲染落地页。
 * 旧「免费可报性预览」漏斗（搜职位/院校→勾身份→出判定）已随职位数据删除下架，
 * 不虚假承诺未上线能力：时间线/公告盯梢标注"上线中"。
 */
export default function HomePage() {
  const cookieStore = cookies();
  const token = cookieStore.get("gradpath_token")?.value;

  if (token) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-ink-50 to-brand-50/40">
      {/* 顶部栏 */}
      <header className="border-b border-ink-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <GraduationCap className="h-5 w-5" />
            </span>
            <span className="font-semibold text-ink-800">GradPath · 职径</span>
          </Link>
          <div className="flex items-center gap-2 text-sm">
            <Link
              href="/login"
              className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-ink-600 hover:bg-ink-100"
            >
              <LogIn className="h-3.5 w-3.5" />
              登录
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-3 py-1.5 font-medium text-white hover:bg-brand-700"
            >
              <UserPlus className="h-3.5 w-3.5" />
              免费注册
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-10">
        {/* Hero */}
        <section className="text-center">
          <h1 className="text-3xl font-bold text-ink-800 sm:text-4xl">
            GradPath · 考公信息差管家
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-ink-500 sm:text-base">
            官方动作在官网、刷题在粉笔、查职位在雷达——我们替你盯散落各处的公告与规则变化，
            按你的身份过滤"与我相关"，每条情报连上官方来源。不代你报名，不编造数据。
          </p>
        </section>

        {/* 当前已开放的能力 */}
        <section className="mt-8 grid gap-4 text-sm sm:grid-cols-2">
          <div className="rounded-2xl border border-brand-100 bg-white/70 p-5">
            <p className="font-semibold text-ink-800">真实来源的考公情报</p>
            <p className="mt-1.5 text-ink-500">
              公告资讯、暗知识、报考规则解读逐条带来源与可信度标注；AI
              问答基于库内真实数据回答，不编造。
            </p>
          </div>
          <div className="rounded-2xl border border-brand-100 bg-white/70 p-5">
            <p className="font-semibold text-ink-800">考公定位评估</p>
            <p className="mt-1.5 text-ink-500">
              填写基本条件，获得竞争力评估、风险提示与备考建议；职位检索请使用公考雷达等专门工具。
            </p>
          </div>
        </section>

        {/* 转化引导 */}
        <section className="mt-10 rounded-2xl border border-brand-100 bg-white/70 p-6 text-center">
          <h2 className="text-lg font-semibold text-ink-800">
            流程时间线伴随 · 上线中
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-ink-500">
            从公告到录用的 12 环节时间线、节点提醒与身份过滤推送正在逐步开放；
            注册后可先行体验情报与定位功能。
          </p>
          <div className="mt-4 flex items-center justify-center gap-3">
            <Link
              href="/register"
              className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              免费注册，订阅信息差
            </Link>
            <Link
              href="/login"
              className="rounded-lg border border-paper-300 bg-white px-5 py-2.5 text-sm font-medium text-ink-600 hover:bg-ink-50"
            >
              已有账号登录
            </Link>
          </div>
        </section>

        <footer className="mt-10 pb-4 text-center text-xs text-ink-400">
          GradPath · 研招信息以官方发布为准，本工具只做数据整理与提示，不构成报考建议
          <div className="mt-1">
            <a
              href="https://beian.miit.gov.cn/"
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="hover:text-brand-600 hover:underline"
            >
              鲁ICP备2026053142号
            </a>
          </div>
        </footer>
      </main>
    </div>
  );
}
