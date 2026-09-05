import Link from "next/link";
import { GraduationCap } from "lucide-react";
import { EligibilityChecker } from "@/components/preview/eligibility-checker";

/**
 * 独立公开路由 /preview：免费可报性预览。
 *
 * 与根落地页共用同一个 EligibilityChecker，带简短说明头，
 * 方便种子用户分享「先来测一下」的直达链接。middleware 已显式放行。
 */
export default function PreviewPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-ink-50 to-brand-50/40">
      <header className="border-b border-ink-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <GraduationCap className="h-5 w-5" />
            </span>
            <span className="font-semibold text-ink-800">GradPath · 职径</span>
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            免费注册
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-ink-800">免费可报性预览</h1>
          <p className="mt-1 text-sm text-ink-500">
            不用注册，先测一测你的条件能不能报目标职位 / 院校——
            数据来自官方职位表与历年复试线，判定与登录后完全一致。
          </p>
        </div>
        <EligibilityChecker />
        <p className="mt-6 text-center text-xs text-ink-400">
          注册并补全专业后，不用先做测评——
          <Link href="/register" className="font-medium text-brand-600 hover:text-brand-700">
            你的专属报考路径（可报岗位/进面线/薪资/同分去向）立即生成 →
          </Link>
        </p>
        <p className="mt-2 text-center text-xs text-ink-400">
          想要保存判定并建立完整条件账本？
          <Link href="/register" className="font-medium text-brand-600 hover:text-brand-700">
            免费注册 →
          </Link>
        </p>
      </main>
    </div>
  );
}
