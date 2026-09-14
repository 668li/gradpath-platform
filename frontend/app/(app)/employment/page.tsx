"use client";

import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import InterviewExperience from "@/app/(app)/interview/page";
import { failureCaseApi } from "@/lib/api/failure-case";
import type { FailureCaseResponse } from "@/types/failure-case";
import { AlertTriangle, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { careerIntelApi } from "@/lib/api/ai";
import { useToast } from "@/components/ui/toast";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import type {
} from "@/types";

// ===== Tab 配置（面试经验与失败案例已合并为面经库单一入口） =====
const tabs = [
  { id: "interview", label: "面经库", icon: MessageSquare, color: "text-cyan-700", desc: "面试经验与失败案例，一站式查阅与提交" },
];

const importanceColors: Record<string, string> = {
  critical: "border-red-200 bg-red-50/40",
  high: "border-orange-200 bg-orange-50/40",
  medium: "border-blue-200 bg-blue-50/40",
  low: "border-paper-200",
};

const importanceBadges: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-blue-100 text-blue-700",
  low: "bg-paper-100 text-ink-500",
};

const importanceLabels: Record<string, string> = {
  critical: "关键",
  high: "重要",
  medium: "一般",
  low: "参考",
};

// ===== Tab: 面经库（面试经验 + 失败案例，合并为单一入口） =====
function InterviewTab() {
  const [cases, setCases] = useState<FailureCaseResponse[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    failureCaseApi
      .list({ page: 1, size: 5 })
      .then((d) => {
        setCases(d.items);
        setTotal(d.total);
      })
      .catch(() => {});
  }, []);

  const pathLabel: Record<string, string> = {
    kaoyan: "考研",
    civil_service: "考公",
    employment: "就业",
    study_abroad: "留学",
  };

  return (
    <div className="space-y-8">
      <InterviewExperience />

      <section className="rounded-xl border border-paper-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 font-bold text-ink-800">
            <AlertTriangle className="h-5 w-5 text-rose-500" /> 失败案例（{total}）
          </h3>
          <Link href="/failure-cases/new" className="text-sm text-brand-600 hover:underline">
            分享我的失败案例
          </Link>
        </div>
        {cases.length === 0 ? (
          <p className="text-sm text-ink-400">暂无已审核的失败案例。真实教训和成功经验一样值钱。</p>
        ) : (
          <ul className="divide-y divide-paper-100">
            {cases.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/failure-cases/${c.id}`}
                  className="-mx-2 block rounded-lg px-2 py-3 hover:bg-paper-50"
                >
                  <p className="text-sm font-medium text-ink-800">{c.title}</p>
                  <p className="mt-0.5 line-clamp-2 text-xs text-ink-500">
                    {c.lessons[0] ?? c.what_would_i_do}
                  </p>
                  <p className="mt-1 text-[11px] text-ink-400">
                    {c.author_role} · {pathLabel[c.path_type] ?? c.path_type} · 有帮助 {c.helpful_count}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ===== 主页面 =====
export default function EmploymentPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <EmploymentPageContent />
    </Suspense>
  );
}

function EmploymentPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "interview";
  const current = tabs.find((t) => t.id === activeTab) || tabs[0];

  const handleTabChange = (id: string) => {
    router.push(`/employment?tab=${id}`);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">就业中心</h1>
        <p className="text-ink-500">面经库 · 失败案例</p>
      </div>

      <div className="flex gap-2 mb-8 border-b border-paper-200 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={cn(
                "flex items-center gap-2 px-6 py-3 font-medium transition-all border-b-2 whitespace-nowrap",
                activeTab === tab.id
                  ? `${tab.color} border-current`
                  : "text-ink-400 border-transparent hover:text-ink-600"
              )}
            >
              <Icon className="h-5 w-5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="mb-6">
        <p className="text-sm text-ink-500">{current.desc}</p>
      </div>

      <div>
        {activeTab === "interview" && <InterviewTab />}
      </div>
    </div>
  );
}
