"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, Compass, Clock, CheckCircle2, ArrowRight } from "lucide-react";
import { decisionsApi, useApi, decisionAnalysisApi } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import { DESTINATION_TYPE_LABEL } from "@/lib/constants";
import { EmptyState, LoadingState } from "@/components/ui/empty";
import { Badge, Button } from "@/components/ui/form-controls";
import { ListSkeleton } from "@/components/ui/skeleton";
import {
  PathConflictSection,
  ProcrastinationCostCard,
  RegretLessonsCard,
  TimeCapsuleCard,
} from "@/components/decision-copilot";
import type { DecisionResponse, PaginatedResponse, DecisionAnalysisResponse } from "@/types";

const TABS = [
  { id: "pending", label: "待决策" },
  { id: "history", label: "历史记录" },
];

const STATUS_BADGE: Record<string, "slate" | "blue" | "green" | "amber"> = {
  planned: "slate",
  confirmed: "blue",
  executed: "green",
  changed: "amber",
};

export default function DecisionCenterPage() {
  const [activeTab, setActiveTab] = useState("pending");

  const { data: listData, error: listError, isLoading: loading } = useApi<PaginatedResponse<DecisionResponse>>(
    "/api/decisions?page=1&page_size=50",
  );
  const { data: analysisData, isLoading: analysisLoading } = useApi<DecisionAnalysisResponse[]>(
    "/api/decision-analysis/list",
    { fallbackData: [] },
  );

  const decisions = listData?.items ?? [];
  const analyses = analysisData ?? [];
  const analyzedIds = new Set(analyses.map((a) => a.decision_id));

  const pendingDecisions = decisions.filter((d) => d.status === "planned");
  const historyDecisions = decisions.filter((d) => d.status !== "planned");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-800">决策中心</h1>
          <p className="text-ink-500 mt-1">管理你的去向决策，深度分析每个选项</p>
        </div>
        <Link href="/decisions">
          <Button>
            <Plus className="h-4 w-4" /> 新建决策
          </Button>
        </Link>
      </div>

      <div className="flex gap-2 border-b border-paper-300 pb-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "bg-white text-brand-600 border-b-2 border-brand-500"
                : "text-ink-400 hover:text-ink-600 hover:bg-paper-200",
            )}
          >
            {tab.label}
            {tab.id === "pending" && pendingDecisions.length > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-500 text-[11px] font-semibold text-white">
                {pendingDecisions.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 路径冲突调解卡片 — 检测到冲突时显示在决策列表上方 */}
      <PathConflictSection />

      {/* 创意功能：决策拖延成本 — 量化"还在犹豫"的真实代价 */}
      <ProcrastinationCostCard />

      {/* 创意功能：前车之鉴 — 过来人的后悔与教训 */}
      <RegretLessonsCard />

      {loading || analysisLoading ? (
        <ListSkeleton count={4} />
      ) : activeTab === "pending" ? (
        pendingDecisions.length === 0 ? (
          <div className="space-y-6">
            <EmptyState
              title="记录你的第一个去向决策"
              description="「去向决策」是你对毕业方向的一次正式选择——考研、就业、考公、出国等。记录下来，系统会帮你跟踪进度、安排回顾、检测路径冲突。"
              action={
                <Link href="/decisions">
                  <Button>
                    <Plus className="h-4 w-4" /> 创建决策
                  </Button>
                </Link>
              }
            />
            <div className="bg-white rounded-xl border border-paper-200 p-5">
              <h3 className="text-sm font-semibold text-ink-700 mb-3">示例：一条决策长什么样？</h3>
              <div className="flex items-start gap-3 rounded-lg bg-paper-50 border border-paper-200 p-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                  <Clock className="h-4 w-4" />
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ink-800 text-sm">考研 · 计算机科学与技术</span>
                    <Badge color="slate">待决策</Badge>
                  </div>
                  <p className="mt-1 text-xs text-ink-500">理由：本科项目经历让我对科研产生兴趣，目标院校华科/西交</p>
                  <p className="mt-1 text-xs text-ink-400">创建后系统会自动安排 30 天回顾提醒</p>
                </div>
              </div>
              <p className="mt-3 text-xs text-ink-400">
                你也可以在 <Link href="/decision-lab" className="text-brand-600 hover:underline">决策实验室</Link> 中用 5 步结构化分析来做深度对比。
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              {pendingDecisions.map((d) => (
                <div key={d.id} className="bg-white rounded-xl border border-paper-200 p-5 hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                      <Clock className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-ink-800">
                          {DESTINATION_TYPE_LABEL[d.destination_type]}
                        </h3>
                        <Badge color={STATUS_BADGE[d.status]}>待决策</Badge>
                      </div>
                      <p className="mt-1 text-sm text-ink-400">
                        创建于 {formatDate(d.created_at)}
                      </p>
                      {d.reasoning && (
                        <p className="mt-2 text-sm text-ink-500 line-clamp-2">{d.reasoning}</p>
                      )}
                    </div>
                  </div>
                  <div className="mt-4 flex items-center justify-between border-t border-paper-100 pt-3">
                    <span className="text-xs text-ink-400">
                      {analyzedIds.has(d.id) ? "已分析" : "待分析"}
                    </span>
                    <Link
                      href={`/decision-lab?decision_id=${d.id}`}
                      className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700"
                    >
                      继续分析
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>

            {/* 创意功能：决策时间胶囊 — 为最近一条待决策写给未来自己的信 */}
            {pendingDecisions.length > 0 && (
              <div>
                <p className="mb-2 text-xs text-ink-400">
                  给「{DESTINATION_TYPE_LABEL[pendingDecisions[0].destination_type]}」这个决策封存的信
                </p>
                <TimeCapsuleCard decisionId={pendingDecisions[0].id} />
              </div>
            )}
          </div>
        )
      ) : (
        historyDecisions.length === 0 ? (
          <EmptyState
            title="暂无历史决策"
            description="已确认或执行的决策将出现在这里"
          />
        ) : (
          <div className="space-y-3">
            {historyDecisions.map((d) => (
              <div key={d.id} className="bg-white rounded-xl border border-paper-200 p-4 hover:shadow-sm transition-shadow">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                      <Compass className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-ink-800">
                          {DESTINATION_TYPE_LABEL[d.destination_type]}
                        </h3>
                        <Badge color={STATUS_BADGE[d.status]}>
                          已{d.status === "confirmed" ? "确认" : d.status === "executed" ? "执行" : "变更"}
                        </Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-ink-400">
                        {formatDate(d.decision_date)}
                      </p>
                    </div>
                  </div>
                  {d.review_completed && (
                    <span className="flex items-center gap-1 text-xs text-green-600 shrink-0">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      已回溯
                    </span>
                  )}
                </div>
                {d.prediction && (
                  <p className="mt-2 text-sm text-ink-500 line-clamp-1">
                    <span className="text-ink-400">预测：</span>
                    {d.prediction}
                  </p>
                )}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}