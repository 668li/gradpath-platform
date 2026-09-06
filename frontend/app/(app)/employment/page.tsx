"use client";

import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import InterviewExperience from "@/app/(app)/interview/page";
import { failureCaseApi } from "@/lib/api/failure-case";
import type { FailureCaseResponse } from "@/types/failure-case";
import { AlertTriangle, Lightbulb, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { careerIntelApi } from "@/lib/api/ai";
import { useToast } from "@/components/ui/toast";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { ListSkeleton } from "@/components/ui/skeleton";
import type {
  CareerDarkKnowledgeResponse,
  CareerDarkKnowledgeStage,
} from "@/types";

// ===== Tab 配置（P2 瘦身后只保留暗知识与面经库；面试经验已并入面经库） =====
const tabs = [
  { id: "dark-knowledge", label: "暗知识", icon: Lightbulb, color: "text-rose-700", desc: "求职过程中那些没人告诉你的关键经验与教训" },
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

// ===== Tab: 暗知识 =====
function DarkKnowledgeTab() {
  const toast = useToast();
  const [stages, setStages] = useState<CareerDarkKnowledgeStage[]>([]);
  const [knowledge, setKnowledge] = useState<CareerDarkKnowledgeResponse[]>([]);
  const [selectedStage, setSelectedStage] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [stageData, knowledgeData] = await Promise.all([
          careerIntelApi.getDarkKnowledgeStages(),
          careerIntelApi.getDarkKnowledge(),
        ]);
        setStages(stageData);
        setKnowledge(knowledgeData);
        if (stageData.length > 0) setSelectedStage(stageData[0].stage);
      } catch (err) {
        toast.push(err instanceof Error ? err.message : "加载暗知识失败", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  const handleStageChange = async (stage: string) => {
    setSelectedStage(stage);
    try {
      const data = await careerIntelApi.getDarkKnowledge(stage);
      setKnowledge(data);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    }
  };

  if (loading) return <ListSkeleton count={3} />;

  const filteredKnowledge = selectedStage
    ? knowledge.filter((k) => k.stage === selectedStage)
    : knowledge;

  return (
    <div className="space-y-6">
      {stages.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {stages.map((s) => (
            <button
              key={s.stage}
              onClick={() => handleStageChange(s.stage)}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                selectedStage === s.stage
                  ? "bg-rose-600 text-white"
                  : "bg-white border border-paper-200 text-ink-600 hover:bg-paper-50"
              )}
            >
              {s.stage_name} ({s.count})
            </button>
          ))}
        </div>
      )}

      {filteredKnowledge.length === 0 ? (
        <EmptyState title="该阶段暂无暗知识" description="试试其他阶段" />
      ) : (
        <div className="space-y-4">
          {filteredKnowledge.map((item) => (
            <div
              key={item.id}
              className={cn(
                "bg-white rounded-xl border p-5 hover:shadow-md transition-shadow",
                importanceColors[item.importance] || "border-paper-200"
              )}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-bold text-ink-800">{item.title}</h3>
                <span className={cn("text-xs px-2 py-1 rounded-full shrink-0", importanceBadges[item.importance] || "bg-paper-100 text-ink-500")}>
                  {importanceLabels[item.importance] || item.importance}
                </span>
              </div>

              <p className="text-sm text-ink-600 leading-relaxed mb-3">{item.content}</p>

              {item.common_misconception && (
                <div className="bg-amber-50 rounded-lg p-3 mb-3">
                  <p className="text-xs font-medium text-amber-700 mb-1">常见误解</p>
                  <p className="text-sm text-amber-800">{item.common_misconception}</p>
                </div>
              )}

              {item.actionable_advice && (
                <div className="bg-green-50 rounded-lg p-3">
                  <p className="text-xs font-medium text-green-700 mb-1">实操建议</p>
                  <p className="text-sm text-green-800">{item.actionable_advice}</p>
                </div>
              )}

              {item.tags.length > 0 && (
                <div className="flex gap-1 mt-3 flex-wrap">
                  {item.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-paper-100 text-ink-500 px-2 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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
  const activeTab = searchParams.get("tab") || "dark-knowledge";
  const current = tabs.find((t) => t.id === activeTab) || tabs[0];

  const handleTabChange = (id: string) => {
    router.push(`/employment?tab=${id}`);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-ink-800 mb-2">就业中心</h1>
        <p className="text-ink-500">暗知识 · 面经库 · 失败案例</p>
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
        {activeTab === "dark-knowledge" && <DarkKnowledgeTab />}
        {activeTab === "interview" && <InterviewTab />}
      </div>
    </div>
  );
}
