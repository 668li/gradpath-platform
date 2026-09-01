import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { GraduationCap, LogIn, UserPlus } from "lucide-react";
import { EligibilityChecker } from "@/components/preview/eligibility-checker";

/**
 * 根页面：公开落地页（W1-D1 冷启动转化漏斗）。
 *
 * 有 gradpath_token 直接进 dashboard；未登录渲染落地页：
 * hero + 免费可报性预览（免注册搜职位/院校 → 勾身份 → 立即出判定），
 * 底部登录/注册 CTA。不套 (app) 壳，独立公开样式（参照 share 公开页模板）。
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
            考研 / 考公 / 就业，先测你能不能报
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-ink-500 sm:text-base">
            搜一个真实职位或院校，填 5 个身份字段，立即看到可报性判定和卡在哪。
            数据来自官方职位表与历年复试线，每一条都可溯源——不用注册也能先尝一口。
          </p>
        </section>

        {/* 免费预览（免登录） */}
        <section className="mt-8">
          <EligibilityChecker />
        </section>

        {/* 转化引导 */}
        <section className="mt-10 rounded-2xl border border-brand-100 bg-white/70 p-6 text-center">
          <h2 className="text-lg font-semibold text-ink-800">
            想要完整版？保存这份判定，建立你的报考条件账本
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-ink-500">
            注册后把目标职位做成「条件账本」，逐条勾选硬门槛与备考项，
            完成率就是你和上岸的距离；决策引擎再对比三路给出个人化建议，最后把结果回传给你。
          </p>
          <div className="mt-4 flex items-center justify-center gap-3">
            <Link
              href="/register"
              className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              免费注册，开始记账
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
        </footer>
      </main>
    </div>
  );
}
